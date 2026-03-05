# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time

from main import Stella

# ------------------- APP INIT -------------------
app = FastAPI(title="Stella: The Witty Space Assistant API")

assistant = Stella()

# ------------------- DATA MODELS -------------------
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    time_taken: float
    context_docs: list = []

# routes
@app.get("/")
def root():
    return {"message": "🚀 Stella API is live. POST to /ask with your query."}

@app.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    user_query = request.query.strip()\
    
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