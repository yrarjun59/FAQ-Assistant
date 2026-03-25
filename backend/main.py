import time
from typing import Optional

from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_ollama import OllamaLLM 
from langchain_chroma import Chroma
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

from prompts import WHIMSICAL_PROMPT, FALLBACK_PROMPT, GUIDE_PROMPT
from ingest import Ingestor , EMBEDDING_MODEL, EMBEDDING_CACHE_DIR, DB_PATH
from ollama_setup import OLLAMA_BASE_URL as OLLAMA_URL , LLM_MODEL as ACTIVE_MODEL

class Stella:
    """RAG assistant: ingests documents and answers queries."""

    def __init__(self, ingestor: Optional[Ingestor] = None) -> None:
        self.ingestor = ingestor or Ingestor()
        self.rag_chain = None
        self.vector_store = None
        self.fallback_chain = None   # set in _init_rag
        self.guide_chain = None      # set in _init_rag
        self._init_rag()  
        
    def _init_rag(self) -> None:
        print("Initializing RAG chain...")
        start = time.perf_counter()

        self._llm = OllamaLLM(model=ACTIVE_MODEL, base_url=OLLAMA_URL)
        self.fallback_chain = FALLBACK_PROMPT | self._llm
        self.guide_chain    = GUIDE_PROMPT    | self._llm

        # cache embeddings as instance var — reused everywhere
        self._embeddings = FastEmbedEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_dir=str(EMBEDDING_CACHE_DIR),
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.vector_store = Chroma(
            persist_directory=str(DB_PATH),
            embedding_function=self._embeddings,
            collection_name="faq_collection",
        )

        print(f"Documents in vector store: {self.vector_store._collection.count()}")

        # combine_chain = create_stuff_documents_chain(llm, WHIMSICAL_PROMPT)

        self._combine_chain = create_stuff_documents_chain(self._llm, WHIMSICAL_PROMPT)

        print(f"RAG ready in {time.perf_counter() - start:.2f}s")


    def ask(self, query: str) -> dict:
        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty.")

        start = time.perf_counter()

        # ── guide trigger ─────────────────────────────────────────
        guide_triggers = ["what can you do", "what do you know", "help me", "what topics",
                        "what can i ask", "guide me", "capabilities", "what are you"]
        
        if any(t in query.lower() for t in guide_triggers):
            answer = self.guide_chain.invoke({"input": query})
            return {
                "answer": answer,
                "sources": [],
                "context_docs": [],
                "time_taken": round(time.perf_counter() - start, 2),
            }

        # ── single Chroma call — reuse results for both filter + LLM ─
        raw = self.vector_store.similarity_search_with_score(query, k=3)
        best_score = max((1.0 - dist for _, dist in raw), default=0.0)

        if best_score < 0.5:
            answer = self.fallback_chain.invoke({"input": query})
            return {
                "answer": answer,
                "sources": [],
                "context_docs": [],
                "time_taken": round(time.perf_counter() - start, 2),
            }
    

        # ── pass already-fetched docs directly to LLM ────────────
        context_docs = [doc for doc, _ in raw]
        answer = self._combine_chain.invoke({
            "input":   query,
            "context": context_docs,
        })

        sources = [d.metadata["source"] for d in context_docs if d.metadata.get("source")]
        context_serialized = [
            {"content": d.page_content, "metadata": d.metadata}
            for d in context_docs
        ]

        return {
            "answer": answer,
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