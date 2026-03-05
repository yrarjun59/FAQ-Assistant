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
from security import classify_input

# config
DB_PATH = "./chroma_db"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
ACTIVE_MODEL = "llama3.2:1b"

USE_RAG = True

# initialize 
def initialize_rag():
    llm = OllamaLLM(model=ACTIVE_MODEL, base_url=OLLAMA_URL)

    if USE_RAG:
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vector_store = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})

        combine_chain = create_stuff_documents_chain(llm, WHIMSICAL_PROMPT)

        rag_chain = create_retrieval_chain(retriever, combine_chain)
     
        return rag_chain
    else:
        return WHIMSICAL_PROMPT | llm

def main():
    print("--- ⭐ Stella: The Witty Space Assistant ---")
    print("🔧 Initializing systems...")

    rag_chain = initialize_rag() 

    print("✅ Chat is live! (Type 'exit' to return to Earth)\n")


    while True:
        user_query = input("👨‍🚀 You: ").strip()
        if user_query.lower() == "exit":
            print("👋 Returning to orbit. Goodbye!")
            break

        start_time = time.time()

        if USE_RAG:
            response = rag_chain.invoke({
            "input": user_query,
            "context": ""
        })
            # print(response)

        else:
            response = rag_chain.invoke(user_query)
            print(response)

        
        print(f"🤖 Stella: {response['answer']}")

        # print(f"Time: {time.time() - start_time:.2f}s\n")

        sources = [
            d.metadata.get("source") 
            for d in response.get("context", []) 
            if d.metadata.get("source")
        ]

        print(f"Time: {time.time() - start_time:.2f}s\n")
        if sources:
            print(f"📚 Source: {', '.join(sources)}")


if __name__ == "__main__":
    main()