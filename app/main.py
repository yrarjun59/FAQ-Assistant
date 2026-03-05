import os
import time
from urllib import response
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM

from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.memory import ConversationBufferWindowMemory

from prompts import WHIMSICAL_PROMPT

# config
DB_PATH = "./chroma_db"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
ACTIVE_MODEL = "llama3.2:1b"


class Stella:
    """Encapsulates RAG initialization and query processing."""
    def __init__(self):
        self.rag_chain = None
        self._initialize_rag()
    
    def _initialize_rag(self):
        """Initializes LLM, embeddings, vector store, and RAG chain."""

        if self.rag_chain is None:
            print("🔧 Initializing RAG chain...")
            llm = OllamaLLM(model=ACTIVE_MODEL, base_url=OLLAMA_URL)
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vector_store = Chroma(persist_directory=DB_PATH,embedding_function=embeddings)
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            combine_chain = create_stuff_documents_chain(llm, WHIMSICAL_PROMPT)
            self.rag_chain = create_retrieval_chain(retriever, combine_chain)
            print("✅ RAG chain ready!")

    def ask(self, query: str) -> dict:
        """Processes a query using the initialized RAG chain."""
        if not query.strip():
            return {"error": "Query cannot be empty."}
        try:
            start_time = time.time()

            response = self.rag_chain.invoke({"input": query, "context": ""})
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
            return {"error": str(e)}
        

    def run_cli(self):
        """Optional CLI interface for local testing."""
        print("--- ⭐ Stella: The Witty Space Assistant ---\n")
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