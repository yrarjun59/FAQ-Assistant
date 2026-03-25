import time
from typing import Optional

from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_ollama import OllamaLLM 
from langchain_chroma import Chroma
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

from prompts import WHIMSICAL_PROMPT
from ingest import Ingestor , EMBEDDING_MODEL, EMBEDDING_CACHE_DIR, DB_PATH
from ollama_setup import OLLAMA_BASE_URL as OLLAMA_URL , LLM_MODEL as ACTIVE_MODEL

class Stella:
    """RAG assistant: ingests documents and answers queries."""

    def __init__(self, ingestor: Optional[Ingestor] = None) -> None:
        self.ingestor = ingestor or Ingestor()
        self.rag_chain = None
        self.vector_store = None
        self._init_rag()

    def _init_rag(self) -> None:
        print("Initializing RAG chain...")
        start = time.perf_counter()

        llm = OllamaLLM(model=ACTIVE_MODEL, base_url=OLLAMA_URL)
        embeddings = FastEmbedEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_dir=str(EMBEDDING_CACHE_DIR),
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.vector_store = Chroma(
            persist_directory=str(DB_PATH),
            embedding_function=embeddings,
            collection_name="faq_collection",
        )

        print(f"Documents in vector store: {self.vector_store._collection.count()}")

        retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
        combine_chain = create_stuff_documents_chain(llm, WHIMSICAL_PROMPT)
        self.rag_chain = create_retrieval_chain(retriever, combine_chain)

        print(f"RAG ready in {time.perf_counter() - start:.2f}s")

    def ask(self, query: str) -> dict:
        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty.")

        start = time.perf_counter()
        response = self.rag_chain.invoke({"input": query})

        context_docs = response.get("context", response.get("source_documents", []))
        sources = [d.metadata["source"] for d in context_docs if d.metadata.get("source")]
        context_serialized = [
            {"content": d.page_content, "metadata": d.metadata}
            for d in context_docs
        ]

        return {
            "answer": response["answer"],
            "sources": sources,
            "context_docs": context_serialized,
            "time_taken": round(time.perf_counter() - start, 2),
        }

    def run_cli(self) -> None:
        print("Chat is live! Type 'exit' to quit.\n")
        while True:
            user_query = input("You: ").strip()
            if user_query.lower() == "exit":
                print("Goodbye!")
                break
            try:
                result = self.ask(user_query)
                print(f"Stella: {result['answer']}")
                print(f"Time: {result['time_taken']:.2f}s")
                for src in result.get("sources", []):
                    print(f"  Source: {src}")
            except Exception as exc:
                print(f"Error: {exc}")

                    
if __name__ == "__main__":
    assistant = Stella()
    assistant.run_cli()