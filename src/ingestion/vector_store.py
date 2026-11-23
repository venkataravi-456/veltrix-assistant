import math
import re
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from langchain_core.documents import Document

from src.retrieval.precedence import is_document_eligible, rank_documents, find_upcoming_changes
from src.retrieval.context_budget import fit_chunks_within_budget

logger = logging.getLogger("vector_store")

def tokenize(text: str) -> List[str]:
    return re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())

class DocumentStore:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.manifest_docs: List[Dict[str, Any]] = []
        self.is_ready: bool = False
        self.client = chromadb.Client()
        # Uses sentence-transformers/all-MiniLM-L6-v2 running on pure CPU
        try:
            self.embed_fn = embedding_functions.DefaultEmbeddingFunction()
            logger.info("Initialized sentence-transformers/all-MiniLM-L6-v2 embedding model (CPU).")
        except Exception as e:
            logger.warning(f"Default embedding function fallback: {e}")
            self.embed_fn = None
        self.collection = None

    def load(self, chunks: List[Dict[str, Any]], manifest_docs: List[Dict[str, Any]]):
        self.chunks = chunks
        self.manifest_docs = manifest_docs
        self.langchain_docs = [
            Document(page_content=c["text"], metadata={k: v for k, v in c.items() if k != "text"})
            for c in chunks
        ]
        
        # Reset and build ChromaDB collection with all-MiniLM-L6-v2 embeddings
        try:
            try:
                self.client.delete_collection("veltrix_policies")
            except Exception:
                pass
                
            self.collection = self.client.create_collection(
                name="veltrix_policies",
                embedding_function=self.embed_fn,
                metadata={"hnsw:space": "cosine"}
            )
            
            ids = [f"chunk_{i}" for i in range(len(chunks))]
            documents = [c["text"] for c in chunks]
            metadatas = [
                {
                    "doc_id": c["doc_id"],
                    "locator": c["locator"],
                    "access_level": c["access_level"],
                    "doc_type": c["doc_type"],
                    "effective_date": c["effective_date"],
                    "chunk_index": i
                }
                for i, c in enumerate(chunks)
            ]
            
            # Add to Chroma in batches
            batch_size = 50
            for i in range(0, len(chunks), batch_size):
                self.collection.add(
                    ids=ids[i:i+batch_size],
                    documents=documents[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size]
                )
            logger.info(f"Loaded {len(chunks)} chunks into ChromaDB with all-MiniLM-L6-v2 embeddings.")
        except Exception as e:
            logger.warning(f"ChromaDB indexing error, using semantic keyword fallback: {e}")
            self.collection = None
            
        self.is_ready = True

    def retrieve(
        self,
        query: str,
        role: str,
        region: str,
        reference_date: str,
        top_k: int = 15
    ) -> Dict[str, Any]:
        """
        Retrieves relevant document chunks strictly following:
        1. Access control filter (Section 7.2 & 12.1 must-pass check 2)
        2. Region match & effective_date <= reference_date
        3. Semantic similarity using sentence-transformers/all-MiniLM-L6-v2
        4. Precedence ranking (Section 5)
        5. Token budget <= 3,000 tokens (Section 4.3 & 12.1 must-pass check 4)
        """
        # Step 1: Pre-filter eligible chunks (Mandatory Access Control)
        eligible_chunks = [
            c for c in self.chunks
            if is_document_eligible(c, role, region, reference_date)
        ]
        
        if not eligible_chunks:
            return {
                "chunks": [],
                "citations": [],
                "upcoming_changes": [],
                "total_tokens": 0
            }
            
        eligible_indices = {i for i, c in enumerate(self.chunks) if is_document_eligible(c, role, region, reference_date)}
        candidate_chunks = []
        
        # Step 2: Dense Semantic Search with all-MiniLM-L6-v2 via ChromaDB
        if self.collection is not None:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(top_k * 3, len(self.chunks))
                )
                if results and "metadatas" in results and results["metadatas"]:
                    for meta in results["metadatas"][0]:
                        idx = meta["chunk_index"]
                        if idx in eligible_indices:
                            candidate_chunks.append(self.chunks[idx])
                            if len(candidate_chunks) >= top_k:
                                break
            except Exception as e:
                logger.warning(f"Dense query error: {e}")
                
        # Fallback / Hybrid scoring if dense results empty
        if not candidate_chunks:
            q_tokens = set(tokenize(query))
            scored_chunks = []
            for c in eligible_chunks:
                c_tokens = tokenize(c["text"] + " " + c["title"] + " " + c["locator"])
                overlap = sum(1 for t in q_tokens if t in c_tokens)
                score = overlap / (math.log(len(c_tokens) + 1) + 1.0)
                if overlap > 0:
                    scored_chunks.append((score, c))
            if scored_chunks:
                scored_chunks.sort(key=lambda x: x[0], reverse=True)
                candidate_chunks = [c for _, c in scored_chunks[:top_k]]
            else:
                candidate_chunks = eligible_chunks[:top_k]
                
        # Step 3: Re-rank candidates using Section 5 Precedence (Authority, Scope, Recency)
        ranked_candidates = rank_documents(candidate_chunks, region)
        
        # Step 4: Fit within the strict 3,000 token budget
        final_chunks, token_count = fit_chunks_within_budget(ranked_candidates, max_tokens=3000)
        
        # Collect distinct citations (doc_id + locator)
        seen_cits = set()
        citations = []
        for c in final_chunks:
            key = (c["doc_id"], c["locator"])
            if key not in seen_cits:
                seen_cits.add(key)
                citations.append({"doc_id": c["doc_id"], "locator": c["locator"]})
                
        # Step 5: Check upcoming changes
        top_doc = final_chunks[0] if final_chunks else None
        upcoming = find_upcoming_changes(self.manifest_docs, role, region, reference_date, top_doc)
        
        return {
            "chunks": final_chunks,
            "citations": citations,
            "upcoming_changes": upcoming,
            "total_tokens": token_count
        }

doc_store = DocumentStore()
