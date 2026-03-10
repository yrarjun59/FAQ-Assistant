import os
import time
from urllib import response
from pathlib import Path

# from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_ollama import OllamaLLM , OllamaEmbeddings
from langchain_chroma import Chroma

from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.memory import ConversationBufferWindowMemory

# from transformers.utils.logging import set_verbosity_error
from langchain_core.globals import  set_debug, set_verbose


from prompts import WHIMSICAL_PROMPT , RAG_PROMPT


DB_PATH = Path("vector_db")

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
ACTIVE_MODEL = "llama3.2:1b"

set_debug(False) 
set_verbose(False)


class Stella:
    """Encapsulates RAG initialization and query processing."""
    def __init__(self):
        self.rag_chain = None
        self.vector_store = None
        self._ensure_rag_ready()

    def _ensure_rag_ready(self):
        """Initialize RAG components only when needed."""

        if self.rag_chain is None:
            start = time.time()
            print("🔧 Initializing RAG chain...")
            llm = OllamaLLM(model=ACTIVE_MODEL, base_url=OLLAMA_URL)
            embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

            # hfembeddings = FastEmbedEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            # pull once, lives in ollama_data volume
            # oembeddings = OllamaEmbeddings(base_url="http://ollama:11434",model="nomic-embed-text")   

            self.vector_store = Chroma(persist_directory=DB_PATH,embedding_function=embeddings)
            retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
            combine_chain = create_stuff_documents_chain(llm, WHIMSICAL_PROMPT)
            self.rag_chain = create_retrieval_chain(retriever, combine_chain)
            elapsed = time.time() - start
            print(f"✅ RAG ready in {elapsed:.2f}s")
 

    
    def ask(self, query: str) -> dict:
        """Processes a query using the initialized RAG chain."""
        self._ensure_rag_ready()
        if not query.strip():
            return {"error": "Query cannot be empty."}
        
        try:
            start_time = time.time()
            response = self.rag_chain.invoke({"input": query, "context": ""})

            print("Retrieved docs:", len(response.get("context", [])))
            
            answer = response['answer']
            context_docs = response.get("context", [])
            context_serialized = [{"content": d.page_content, "metadata": d.metadata} for d in context_docs]
            sources = [d.metadata.get("source") for d in context_docs if d.metadata.get("source")]

            return {
                "answer": answer,
                "sources": sources,
                "context_docs": context_serialized,
                "time_taken": round(time.time() - start_time, 2)
            }

        except Exception as e:
            return {
            "error": str(e)
        }
  
    def run_cli(self):
        """Interactive CLI for testing both modes."""
        print("✅ Chat is live! (Type 'exit' to quit)\n")
        while True:
            user_query = input("👨‍🚀 You: ").strip()
            if user_query.lower() == "exit":
                print("👋 Goodbye!")
                break

            result = self.ask(user_query)

            if "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"🤖 Stella: {result['answer']}")
                print(f"Time: {result['time_taken']:.2f}s")
                print([f"📚 Source: {src}" for src in result.get("sources", [])])

    def test_retrieval(self, query: str):
        """Test RAG retrieval without LLM."""
        
        docs = self.retrieve_docs(query)
        print(f"\n🔎 Retrieved {len(docs)} docs\n")

        for i, d in enumerate(docs):
            print(f"--- Doc {i+1} ---")
            print(d.page_content[:200])
            print("Metadata:", d.metadata)
            print()
                    
if __name__ == "__main__":
    assistant = Stella()
    assistant.run_cli()
    # assistant.test_retrieval("fuckyou")
