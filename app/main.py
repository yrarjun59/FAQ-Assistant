import os
import sys
import time
import requests
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

# Import our Modules
from prompts import FAQ_SYSTEM_PROMPT
from security import SecurityFirewall

# --- CONFIGURATION ---
DB_PATH = "./db"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
# MODEL_NAME = "llama3.1"
MODEL_NAME = "llama3.2:1b"


print("--- Initializing Secure System ---")

# 0. System Check
try:
    requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).raise_for_status()
    print("✅ Ollama connection successful.")
except Exception as e:
    print(f"❌ CRITICAL: Cannot connect to Ollama. Error: {e}")
    sys.exit(1)

try:
    # 1. Setup Components
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_store = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    
    # Initialize LLMs
    llm_main = OllamaLLM(model=MODEL_NAME, base_url=OLLAMA_URL)
    
    # Initialize Firewall (Passing the smart LLM for refusals)
    # firewall = SecurityFirewall(MODEL_NAME, OLLAMA_URL)
    firewall = SecurityFirewall(OLLAMA_URL)

    # 2. Build RAG Chain
    # Step A: Create the chain that combines documents (inserts context into prompt)
    combine_docs_chain = create_stuff_documents_chain(
        llm=llm_main, 
        prompt=FAQ_SYSTEM_PROMPT
    )

    # Step B: Create the full Retrieval Chain (Search -> Combine -> Answer)
    rag_chain = create_retrieval_chain(
        retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
        combine_docs_chain=combine_docs_chain
    )

    print("\n✅ System Ready. Talk to me! (Type 'exit' to quit)")

    # 3. Main Loop
    while True:
        try:
            user_query = input("\nYou: ")
            
            if user_query.lower().strip() == "exit":
                break

            # --- START TIMER ---
            start_time = time.time()

            # --- STEP A: SECURITY & ROUTING ---
            status, message = firewall.process(user_query)

            # --- STEP B: EXECUTION ---
            
            # Case 1: Blocked (HR/Injection/Unknown)
            if status == "BLOCKED":
                print(f"AI: {message}")
                # Calculate time for blocked responses too
                end_time = time.time()
                print(f"⏱️  Response Time: {end_time - start_time:.2f} seconds")
                continue

            # Case 2: Safe (RAG)
            if status == "SAFE":
                # Invoke RAG chain
                response = rag_chain.invoke({"input": user_query})
                answer = response.get('answer', 'I am unable to find an answer right now.')
                print(f"AI: {answer}")

                # --- STOP TIMER ---
                end_time = time.time()
                print(f"⏱️  Response Time: {end_time - start_time:.2f} seconds")

        except Exception as e:
            print(f"⚠️ Runtime Error: {e}")

except Exception as init_error:
    print(f"❌ Initialization Failed: {init_error}")