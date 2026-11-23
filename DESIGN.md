# Veltrix PeopleOps Assistant — System Design Document

This document details the architectural and engineering decisions implemented in the Veltrix PeopleOps Assistant, adhering to the requirements of the AI/ML Engineer assessment brief.

---

## 1. Document Ingestion: Tables and Scanned Documents

### Pipeline Structure
The ingestion pipeline is implemented in `src/ingestion/parser.py` and `src/ingestion/holidays.py`:
- **Format Handlers**: Specialized parsers handle `.pdf` (via `pypdf`), `.docx` (via `python-docx`), `.html` (via `BeautifulSoup4`), and `.md` (via line scanning).
- **Table Parsing**:
  - For `.docx`, table elements (`w:tbl`) are iterated, cells are extracted, normalized, and formatted as Markdown pipes (`| Col 1 | Col 2 |`).
  - For `.html`, `<table>`, `<tr>`, and `<td>`/`<th>` tags are rendered into structured rows.
  - For `.pdf`, tabular text layouts are preserved with section locators.
- **Scanned Document Ingestion (OCR)**:
  - For PDF pages containing scanned images without an underlying text layer (such as `memo_hybrid_work_update.pdf`), `pypdf` extracts image streams from `page.images`.
  - The image bytes are fed into `pytesseract` (backed by the Docker container's `tesseract-ocr` C++ engine) to extract text content dynamically without hardcoding any facts from the corpus.
- **Holiday Extraction**: Calendar documents (`doc_type: "calendar"`) are processed during ingestion to extract public holidays into the in-memory `HolidayStore` mapped by region (`IN`, `US`, `DE`).

---

## 2. Chunking and Retrieval Design

### Strategy
- **Heading-Aware Semantic Chunking**: Rather than arbitrary fixed character splitting, documents are chunked based on hierarchical section headings (e.g., `1. Public holidays`, `Section 3: Eligibility`) and page numbers (`p. 1`, `p. 2`). This ensures that complete policy clauses remain intact within individual chunks.
- **Why Chosen**: In legal and HR policies, context truncation across arbitrary token boundaries can sever critical conditions from their allowances. Heading-aware chunking preserves logical coherence and guarantees accurate citations (`doc_id` + `locator`).
- **Retrieval Mechanism**:
  1. **Strict Pre-filtering**: Before computing similarity, chunks that the user is not entitled to read are strictly excluded (satisfying Section 12.1 Must-Pass Check 2).
  2. **Dense Semantic Embedding (`all-MiniLM-L6-v2`) & LangChain**: Chunks are wrapped in LangChain `Document` abstractions and embedded using `sentence-transformers/all-MiniLM-L6-v2` via ChromaDB on CPU (384-dimensional dense vectors evaluated with cosine distance). LLM response synthesis uses LangChain `ChatPromptTemplate` and `StrOutputParser`.
  3. **Deterministic Re-ranking**: Candidate chunks are re-ordered by the Section 5 Precedence engine.
  4. **Token Budget Enforcement**: Selected chunks are capped at 3,000 tokens using `tiktoken` (`cl100k_base`) via `src/retrieval/context_budget.py`.

---

## 3. Implementation of Section 5 Rules

Implemented in `src/retrieval/precedence.py`:
1. **Eligibility Filter (`is_document_eligible`)**:
   - `Role Access`: Evaluated against `access_level` (`all`, `managers`, `hr`).
   - `Region Scope`: Evaluated against requester's region or `GLOBAL`.
   - `Temporal Eligibility`: Evaluated against `effective_date <= reference_date`.
2. **Deterministic Precedence Comparator (`compare_precedence`)**:
   - **Step 1 (Authority)**: `policy`, `addendum`, `memo`, `handbook`, `calendar` (Rank 1) strictly outrank `faq` and `wiki` (Rank 2).
   - **Step 2 (Scope)**: Specific regional addenda (`IN`, `US`, `DE`) outrank `GLOBAL` documents.
   - **Step 3 (Recency)**: More recent `effective_date` outranks older versions.
   - **Unresolved Conflicts**: If documents tie on all three tests, both are presented with citations, explicitly highlighting the conflict.
3. **Upcoming Changes (`find_upcoming_changes`)**:
   - Documents with `effective_date > reference_date` that would win on their effective date are flagged and appended to the response as upcoming policy updates.

---

## 4. Access Control and Enforcement Boundaries

Access control is enforced **in application code**, completely independent of the LLM:

| Layer | File & Function | Rule Enforced |
|---|---|---|
| **Identity Authentication** | `src/main.py:chat` | Validates `X-Employee-Id` against the SQLite database; raises `HTTP 401` if missing/invalid. |
| **Session Boundary** | `src/orchestration/session_state.py:get_or_create` | Verifies that `session_id` belongs to the employee who initiated it; raises `HTTP 403` on mismatch. |
| **Document Retrieval** | `src/retrieval/precedence.py:is_document_eligible` | Excludes restricted documents prior to LLM injection. Restricted documents are never sent to the LLM. |
| **Leave Data Read** | `src/tools/leave_tools.py:check_can_view_leave` | Restricts employee to self; manager to self + direct reports; HR to single employee. Returns standard refusal message. |
| **Leave Data Write** | `src/tools/leave_tools.py:commit_apply_leave` | Restricts applying/cancelling leave strictly to the authenticated requester. |

---

## 5. Personal Data Protection (PII)

Implemented in `src/orchestration/pii_sanitizer.py`:
- **Console & File Logging**: Employee names, email addresses, and phone numbers are excluded from logs. Only `employee_id` is logged.
- **Answers & Tool Outputs**:
  - Phone numbers matching regex patterns are completely redacted.
  - Email addresses are masked to the first character plus `***` and domain (e.g., `r***@veltrix.example`).
  - Employee names are only rendered when the requester has verified RBAC access.
- **LLM Prompts**: Only relevant document text and necessary numeric leave parameters are injected.

---

## 6. Failure Modes Found and Fixed

1. **Tiktoken Cache Failure in Sandboxed/Offline Environments**:
   - *Failure*: Calling `tiktoken.get_encoding("cl100k_base")` on initial run attempted a network download to Microsoft Azure Blob storage, failing in restricted environments.
   - *Fix*: Pre-cached the encoding in the Dockerfile and added a graceful token-estimator fallback in `src/retrieval/context_budget.py`.
2. **Holiday Metadata Extraction Leakage**:
   - *Failure*: In `holiday_calendar_india_2026.pdf`, the metadata header contained `"Effective date: 1 January 2026"`, causing Jan 1 to be mistakenly flagged as a public holiday.
   - *Fix*: Scoped date parsing strictly to lines between `"1. Public holidays"` and `"2. Restricted holidays"`.
3. **Session Hijacking Across Different Headers**:
   - *Failure*: An existing session ID could be reused by another employee ID.
   - *Fix*: Mapped session ownership on first message in `SessionStore` and enforced HTTP 403 checks in `main.py`.

---

## 7. Scaling to 10,000 Documents

### Bottlenecks at Scale:
1. **In-Memory Sequential Scanning**: Linear iteration over 10,000 documents during startup would exhaust memory and violate the 10-minute startup SLA.
2. **Pre-filtering Overhead**: Checking metadata across tens of thousands of chunks in Python becomes CPU-bound.

### Scalable Architecture Fix:
- **Persistent Local Vector Index (Qdrant / PGVector / ChromaDB with HNSW)**: Store pre-computed document embeddings in SQLite or local HNSW vector indices with metadata payloads (`role`, `region`, `effective_date`).
- **Database-Level Metadata Filtering**: Execute metadata filtering directly in SQL or vector index query filters (`WHERE access_level IN (...) AND region IN (...)`) before computing cosine similarity.
- **Asynchronous Incremental Ingestion**: Compute file content hashes (SHA-256) and ingest only new or modified documents on startup.
