import os
import time
from pathlib import Path

from ingest import Ingestor
ingestor = Ingestor()

# from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_ollama import OllamaLLM , OllamaEmbeddings
from langchain_chroma import Chroma



from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain


from langchain_core.globals import  set_debug, set_verbose
from prompts import WHIMSICAL_PROMPT , RAG_PROMPT

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
ACTIVE_MODEL = os.getenv("LLM_MODEL","llama3.2:1b")

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_CACHE_DIR = "/app/fastembed_cache"
DB_PATH = Path("vector_db")

set_debug(False) # set true of see inner working of rag
set_verbose(False) # set true of see inner rag processs


class Stella:
    """Encapsulates RAG initialization and query processing."""
    # def __init__(self):
    def __init__(self, ingestor: Ingestor | None = None):
        self.ingestor = ingestor or Ingestor()
        self.rag_chain = None
        self.vector_store = None

        self._init_rag()


    def _init_rag(self):
        """Initialize RAG components exactly once at construction time."""
        print("🔧 Initializing RAG chain...")
        start = time.time()
 
        llm = OllamaLLM(model=ACTIVE_MODEL, base_url=OLLAMA_URL)
        embeddings = FastEmbedEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_dir=str(EMBEDDING_CACHE_DIR),
            model_kwargs={"device":"cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
 
        self.vector_store = Chroma(
            persist_directory=str(DB_PATH),
            embedding_function = embeddings,
            collection_name="faq_collection"
        )

        count = self.vector_store._collection.count()
        print(f"🗄️ Documents in vector store: {count}")
        
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
        combine_chain = create_stuff_documents_chain(llm, WHIMSICAL_PROMPT)
        self.rag_chain = create_retrieval_chain(retriever, combine_chain)
 
        print(f"✅ RAG ready in {time.time() - start:.2f}s")
 

    def ask(self, query: str) -> dict:
        """Process a query using the RAG chain."""
        if not query.strip():
            return {"error": "Query cannot be empty."}
 
        try:
            start_time = time.time()
            response = self.rag_chain.invoke({"input": query})
            context_docs = response.get("context", [])
            answer = response['answer']

            context_docs = response.get("context", response.get("source_documents", []))
            context_serialized = [{"content": d.page_content, "metadata": d.metadata} for d in context_docs]
            sources = [d.metadata.get("source") for d in context_docs if d.metadata.get("source")]

            return {
                "answer": answer,
                "sources": sources,
                "context_docs": context_serialized,
                "time_taken": round(time.time() - start_time, 2)
            }
 
        except Exception as e:
            return {"error": str(e)}
    
    def run_cli(self):
        """Interactive CLI for testing."""
        if not self.ingestor.run_ingestion():
            raise RuntimeError("❌ Ingestion failed. Cannot start Stella.")
 
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

                    
if __name__ == "__main__":
    assistant = Stella()
    assistant.run_cli()