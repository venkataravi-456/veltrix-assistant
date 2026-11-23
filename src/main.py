import uuid
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field

from src.config import settings
from src.database import get_employee, get_db_connection
from src.ingestion.parser import ingest_corpus
from src.ingestion.holidays import holiday_store
from src.ingestion.vector_store import doc_store
from src.orchestration.router import handle_chat_message
from src.orchestration.session_state import session_store
from src.ui import CHAT_UI_HTML

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("veltrix_assistant")

is_ready = False

def init_system():
    global is_ready
    if not doc_store.is_ready:
        logger.info("Initializing Veltrix Assistant service...")
        try:
            logger.info(f"Loading holidays from {settings.CORPUS_DIR}...")
            holiday_store.load_from_corpus(settings.CORPUS_DIR)
            
            logger.info(f"Ingesting corpus from {settings.CORPUS_DIR} using manifest {settings.MANIFEST_PATH}...")
            chunks = ingest_corpus(settings.CORPUS_DIR, settings.MANIFEST_PATH)
            with open(settings.MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                
            doc_store.load(chunks, manifest)
            logger.info("Ingestion completed successfully. Service is ready!")
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
    is_ready = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_system()
    yield
    logger.info("Shutting down service.")

app = FastAPI(title="Veltrix PeopleOps Assistant", lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "The body is missing or invalid."}
    )

# Request & Response Models
class ChatRequest(BaseModel):
    session_id: str = Field(default="session_1", description="Unique conversation session ID")
    message: str = Field(default="What is my leave balance?", description="User query or message")

class Citation(BaseModel):
    doc_id: str
    locator: str

class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any]
    status: str

class ChatResponse(BaseModel):
    request_id: str
    answer: str
    route: str
    citations: List[Citation]
    tool_calls: List[ToolCall]
    pending_confirmation: bool

@app.get("/", response_class=HTMLResponse)
def index():
    return CHAT_UI_HTML

@app.get("/health")
def health():
    if not is_ready:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "initializing"})
    return {"status": "ok"}

@app.get("/api/employees")
def list_employees():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT employee_id, full_name, email, role, region, level FROM employees ORDER BY employee_id")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

@app.post("/chat", response_model=ChatResponse)
async def chat(
    chat_req: ChatRequest,
    x_employee_id: Optional[str] = Header(None, alias="X-Employee-Id")
):
    # 1. Check X-Employee-Id header
    if not x_employee_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header 'X-Employee-Id' is required."
        )
        
    emp = get_employee(x_employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee ID not found in database."
        )

    # 2. Check Session Ownership (Section 7.1)
    session = session_store.get_or_create(chat_req.session_id, x_employee_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The session_id belongs to another employee."
        )

    # 3. Route and handle conversation
    result = handle_chat_message(chat_req.session_id, x_employee_id, chat_req.message)
    req_id = str(uuid.uuid4())

    return ChatResponse(
        request_id=req_id,
        answer=result["answer"],
        route=result["route"],
        citations=result["citations"],
        tool_calls=result["tool_calls"],
        pending_confirmation=result["pending_confirmation"]
    )
