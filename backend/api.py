from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import time

from ollama_setup import setup
from main import Stella

setup() # make sure ollama model runs before api run

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

assistant = Stella()

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