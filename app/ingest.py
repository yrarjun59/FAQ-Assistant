import os
import json
# from langchain.schema import Document
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- CONFIGURATION ---
KNOWLEDGE_DIR = "./knowledge/FAQS"  # Folder containing JSON files
DB_PATH = "./db"

def load_documents(knowledge_dir=KNOWLEDGE_DIR):
    print("=== Step 1: Reading JSON Files ===")
    all_documents = []
    if not os.path.exists(knowledge_dir):
        print(f"Error: Folder '{knowledge_dir}' not found.")
        return []
    files = [f for f in os.listdir(knowledge_dir) if f.endswith(".json")]
    if not files:
        print("Error: No JSON files found in knowledge folder.")
        return []
    for filename in files:
        filepath = os.path.join(knowledge_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            entries = data.get("faqs", [])
            if not isinstance(entries, list):
                print(f"Warning: {filename} does not contain a list under 'faqs'")
                continue
            for item in entries:
                content = (
                    f"Question: {item.get('question','')}\n"
                    f"Answer: {item.get('answer','')}"
                )
                doc = Document(page_content=content, metadata={"source": filename})
                all_documents.append(doc)
    print(f"Loaded {len(all_documents)} entries from {len(files)} files.")
    return all_documents


def create_vector_database(documents, db_path=DB_PATH):
    
    print("=== Step 2: Creating Vector Database ===")
    print("(This may take a moment to download model and process...)")
    embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    if os.path.exists(db_path):
        import shutil
        shutil.rmtree(db_path)
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embedding_function,
        persist_directory=db_path
    )
    print(f"SUCCESS: Database created at '{db_path}'")
    return vector_store

test_query = "what is spacewing ?"

def verify_database(vector_store, test_query=test_query):
    print("\n=== Step 3: Verification Test ===")
    print("Testing search capability with a sample query...")
    results = vector_store.similarity_search(test_query, k=1)
    if results:
        print("✅ Verification Successful! Found this match:")
        print(f"---\n{results[0].page_content}\n---")
        print("Data is accurately vectorized and retrievable.")
    else:
        print("❌ Verification Failed. No results found.")


def run_ingestion():
    docs = load_documents()
    if not docs:
        return
    store = create_vector_database(docs)
    verify_database(store)


if __name__ == "__main__":
    run_ingestion()