
from ollama_setup import setup
setup()
from ingest import Ingestor
ingestor = Ingestor()
if not ingestor.run_ingestion():
        raise RuntimeError("❌ Ingestion failed. Cannot start Stella.")

from main import Stella
assistant = Stella()

import time
import os
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Stella API")

# --- ADD THIS BLOCK ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------

# ------------------- DATA MODELS -------------------
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    time_taken: float
    context_docs: list = []
    error: str | None = None

@app.get("/")
def health_check():
    return {"status": "online"}
    

@app.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    user_query = request.query.strip()
    
    print(f"Received query: {user_query}")

    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        start_time = time.time()
        result = assistant.ask(user_query)
        result['time_taken'] = time.time() - start_time
        
        return QueryResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
    
@app.get("/file/{filename}")
def file_location(filename: str):

    print(f"{filename} is filename")

    base_dir = "knowledge/FAQS"
    file_path = os.path.join(base_dir, f"{filename}")

    print("Looking for file at:", os.path.abspath(file_path))

    # check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # return file to browser
    with open(file_path,"r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content = data)
