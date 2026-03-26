import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# from ollama_setup import setup
from ingest import Ingestor
from main import Stella

# ── Startup ───────────────────────────────────────────────────────────────────
# setup()

ingestor = Ingestor()
if not ingestor.run_ingestion():
    raise RuntimeError("Ingestion failed. Cannot start Stella.")

assistant = Stella()

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Stella API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Data models ───────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    time_taken: float = 0.0
    context_docs: list = []
    error: str | None = None

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "online"}


@app.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    user_query = request.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        start_time = time.perf_counter()
        result = assistant.ask(user_query)
        result["time_taken"] = round(time.perf_counter() - start_time, 2)
        return QueryResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/file/{filename}")
def get_file(filename: str):
    base_dir = Path("knowledge/FAQS").resolve()
    file_path = (base_dir / filename).resolve()

    if not file_path.is_relative_to(base_dir):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

    if file_path.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="Only JSON files are served.")

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}") from exc

    return JSONResponse(content=data)