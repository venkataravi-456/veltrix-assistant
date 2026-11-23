import os
import io
import re
import json
from typing import List, Dict, Any, Optional
from PIL import Image
import pypdf
import docx
import bs4
import pytesseract

def clean_text(text: str) -> str:
    # Replace weird whitespace characters
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()

def parse_pdf(file_path: str, doc_id: str) -> List[Dict[str, Any]]:
    chunks = []
    reader = pypdf.PdfReader(file_path)
    current_heading = "p. 1"
    
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_locator = f"p. {page_num}"
        text = page.extract_text() or ""
        
        # Check if page is scanned/image-only
        if len(text.strip()) < 20 and len(page.images) > 0:
            try:
                for img_file in page.images:
                    pil_img = Image.open(io.BytesIO(img_file.data))
                    ocr_text = pytesseract.image_to_string(pil_img)
                    if ocr_text.strip():
                        text += "\n" + ocr_text
            except Exception as e:
                # If tesseract binary isn't in PATH on local machine
                print(f"OCR note for {file_path} (page {page_num}): {e}")
                
        text = clean_text(text)
        if not text:
            continue
            
        # Try to find section headings in text (e.g. "1. Section Name", "## Heading", etc.)
        lines = text.split("\n")
        current_chunk_lines = []
        loc = page_locator
        
        for line in lines:
            line_str = line.strip()
            # Check if line looks like a section heading
            heading_match = re.match(r"^(\d+\.[\d\.]*\s+[A-Z][A-Za-z0-9\s,\-_/]+)$", line_str)
            if heading_match and len(line_str) < 80:
                if current_chunk_lines:
                    chunk_body = "\n".join(current_chunk_lines).strip()
                    if chunk_body:
                        chunks.append({
                            "locator": loc,
                            "text": chunk_body
                        })
                    current_chunk_lines = []
                loc = heading_match.group(1).strip()
                current_chunk_lines.append(line_str)
            else:
                current_chunk_lines.append(line_str)
                
        if current_chunk_lines:
            chunk_body = "\n".join(current_chunk_lines).strip()
            if chunk_body:
                chunks.append({
                    "locator": loc,
                    "text": chunk_body
                })
                
    return chunks

def parse_docx(file_path: str, doc_id: str) -> List[Dict[str, Any]]:
    chunks = []
    doc = docx.Document(file_path)
    current_heading = "Overview"
    current_lines = []
    
    for element in doc.element.body:
        # Paragraph
        if element.tag.endswith('p'):
            p = [p for p in doc.paragraphs if p._element == element]
            if p:
                text = p[0].text.strip()
                if not text:
                    continue
                # Heading detection
                style_name = p[0].style.name.lower() if p[0].style else ""
                is_heading = "heading" in style_name or re.match(r"^(\d+\.[\d\.]*\s+[A-Z].*)$", text)
                if is_heading:
                    if current_lines:
                        body = "\n".join(current_lines).strip()
                        if body:
                            chunks.append({"locator": current_heading, "text": body})
                        current_lines = []
                    current_heading = text
                else:
                    current_lines.append(text)
        # Table
        elif element.tag.endswith('tbl'):
            tbl = [t for t in doc.tables if t._element == element]
            if tbl:
                table_lines = []
                for row in tbl[0].rows:
                    cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                    table_lines.append(" | ".join(cells))
                if table_lines:
                    current_lines.append("\n" + "\n".join(table_lines) + "\n")
                    
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append({"locator": current_heading, "text": body})
            
    return chunks

def parse_html(file_path: str, doc_id: str) -> List[Dict[str, Any]]:
    chunks = []
    with open(file_path, "r", encoding="utf-8") as f:
        soup = bs4.BeautifulSoup(f, "html.parser")
        
    current_heading = soup.title.string.strip() if soup.title and soup.title.string else "Overview"
    current_text = []
    
    # Iterate through child elements
    body = soup.body or soup
    for elem in body.find_all(["h1", "h2", "h3", "h4", "p", "table", "ul", "ol"]):
        tag_name = elem.name.lower()
        if tag_name in ["h1", "h2", "h3", "h4"]:
            if current_text:
                text_block = "\n".join(current_text).strip()
                if text_block:
                    chunks.append({"locator": current_heading, "text": text_block})
                current_text = []
            current_heading = elem.get_text(strip=True)
        elif tag_name == "table":
            rows = []
            for tr in elem.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                current_text.append("\n".join(rows))
        else:
            txt = elem.get_text(strip=True)
            if txt:
                current_text.append(txt)
                
    if current_text:
        text_block = "\n".join(current_text).strip()
        if text_block:
            chunks.append({"locator": current_heading, "text": text_block})
            
    return chunks

def parse_markdown(file_path: str, doc_id: str) -> List[Dict[str, Any]]:
    chunks = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    current_heading = "Overview"
    current_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    chunks.append({"locator": current_heading, "text": body})
                current_lines = []
            # Extract heading text
            current_heading = re.sub(r"^#+\s*", "", stripped)
        else:
            current_lines.append(line.rstrip())
            
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append({"locator": current_heading, "text": body})
            
    return chunks

def ingest_corpus(corpus_dir: str, manifest_path: str) -> List[Dict[str, Any]]:
    """
    Ingests all documents from manifest.json and corpus_dir.
    Returns a unified list of chunk dictionaries with metadata attached.
    """
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    all_chunks = []
    for doc in manifest:
        file_name = doc["file"]
        file_path = os.path.join(corpus_dir, file_name)
        if not os.path.exists(file_path):
            continue
            
        ext = os.path.splitext(file_name)[1].lower()
        if ext == ".pdf":
            chunks = parse_pdf(file_path, doc["doc_id"])
        elif ext == ".docx":
            chunks = parse_docx(file_path, doc["doc_id"])
        elif ext == ".html":
            chunks = parse_html(file_path, doc["doc_id"])
        elif ext in [".md", ".markdown"]:
            chunks = parse_markdown(file_path, doc["doc_id"])
        else:
            chunks = []
            
        for c in chunks:
            all_chunks.append({
                "doc_id": doc["doc_id"],
                "file": doc["file"],
                "title": doc["title"],
                "doc_type": doc["doc_type"],
                "regions": doc["regions"],
                "effective_date": doc["effective_date"],
                "access_level": doc["access_level"],
                "locator": c["locator"],
                "text": c["text"]
            })
            
    return all_chunks
