import time
from typing import Optional

from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_ollama import OllamaLLM 
from langchain_chroma import Chroma
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain


from prompts import WHIMSICAL_PROMPT, FALLBACK_PROMPT, GUIDE_PROMPT
from ingest import Ingestor , EMBEDDING_MODEL, EMBEDDING_CACHE_DIR, DB_PATH
from ollama_setup import setup, OLLAMA_BASE_URL as OLLAMA_URL
# from memory import create_memory, OllamaWithTokenizer

# use custom LLM
from dotenv import load_dotenv

load_dotenv()

# load the llm
LLM_MODEL = "llama3.2:1b"
# llm = OllamaWithTokenizer(model=LLM_MODEL)


class Stella:
    """RAG assistant: ingests documents and answers queries."""

    def __init__(self, ingestor: Optional[Ingestor] = None) -> None:
        self.ingestor = ingestor or Ingestor()
        self.rag_chain = None
        self.vector_store = None
        self.fallback_chain = None   # set in _init_rag
        self.guide_chain = None      # set in _init_rag
        self.memory = None  
        self._init_rag()
        
    def _init_rag(self) -> None:
        print("Initializing RAG chain...")
        start = time.perf_counter()
        
        model_name = setup(model_name=LLM_MODEL)
        self._llm = OllamaLLM(model=model_name, base_url = OLLAMA_URL)

        #create a memory
        # self.memory = create_memory(self._llm)

        self.fallback_chain = FALLBACK_PROMPT | self._llm
        self.guide_chain    = GUIDE_PROMPT    | self._llm

        # cache embeddings as instance var — reused everywhere
        embeddings = FastEmbedEmbeddings (model_name=EMBEDDING_MODEL,cache_dir=str(EMBEDDING_CACHE_DIR)
                            )
        self.vector_store = Chroma(
            persist_directory=str(DB_PATH),
            embedding_function=embeddings,
            collection_name="faq_collection",
        )
 
        print(f"Documents in vector store: {self.vector_store._collection.count()}")

        retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3})

        combine_chain = create_stuff_documents_chain(self._llm, WHIMSICAL_PROMPT)

        self.rag_chain = create_retrieval_chain(retriever, combine_chain)

        # self._combine_chain = create_stuff_documents_chain(self._llm, WHIMSICAL_PROMPT)
        print(f"RAG ready in {time.perf_counter() - start:.2f}s")

        return self.rag_chain


    def ask(self, query: str) -> dict:
        """Processes a query using the initialized RAG chain."""

        if not self.rag_chain: self._init_rag()

        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty.")

        start_time = time.perf_counter()
        # load memory
        # memory_vars = self.memory.load_memory_variables({})

        try:
            # call rag chain with memory injected
            response = self.rag_chain.invoke({"input": query,})
            
            # "chat_history": memory_vars["chat_history"]
    
            # Single fetch with fallback — no duplicate
            context_docs = response.get("context", response.get("source_documents", []))
            
            # answer = response.get('answer')
            answer = response['answer']
            context_serialized = [{"content": d.page_content, "metadata": d.metadata} for d in context_docs]
            sources = [d.metadata["source"] for d in context_docs if d.metadata.get("source")]

            # save interaction
            # self.memory.save_context(
            #     {"input": query},
            #     {"output": answer}
            #     )

            return {
                "answer": answer,
                "sources": sources,
                "context_docs": context_serialized,
                "time_taken": round(time.perf_counter() - start_time, 2),
            }
        except Exception as e:
            return {"error": str(e)}

    def run_cli(self) -> None:
        print("Chat is live! Type 'exit' to quit.\n")
        while True:
            user_query = input("👨‍🚀 You: ").strip()
            try:
                result = self.ask(user_query)

                answer = result.get('answer')
                print(f"🤖 Stella: {answer}")
                print(f"Time: {result['time_taken']:.2f}s")
                print([f"📚 Source: {src}" for src in result.get("sources", [])])
            except Exception as exc:
                print(f"Error: {exc}")

            if user_query.lower() == "exit":
                print("Goodbye!")
                break


if __name__ == "__main__":
    assistant = Stella()
    assistant.run_cli()