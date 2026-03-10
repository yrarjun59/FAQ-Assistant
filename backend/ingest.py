import os
import csv
from pathlib import Path
import json
from typing import List

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings

cache_dir = Path("/app/fastembed_cache")
os.makedirs(cache_dir, exist_ok=True)

KNOWLEDGE_DIR = Path("knowledge/FAQS")
DB_PATH = Path("vector_db")
csv_dir = Path("CSV")

# EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

def load_documents(directory: str) -> List[Document]:

    if not directory.is_dir():
        print(f"❌ Error: Directory '{directory}' not found.")
        return []
    
    print(f"=== STEP 1: loading files from {directory} exits ????'")

    files = [f for f in os.listdir(directory) if f.endswith(".json")]
    if not files:
        print("❌ Error: No JSON files found.")
        return []

    documents = []
    
    for filename in files:
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # --- EXTRACT GLOBAL METADATA ---
                # These fields apply to all items in this file
                company = data.get('company', 'Unknown Company')
                category = data.get('category', 'General')
                last_updated = data.get('last_updated', 'N/A')

                # Extract the list of FAQs
                faqs = data.get('faqs', [])
                
                if not isinstance(faqs, list):
                    print(f"⚠️ Skipping {filename}: 'faqs' key is not a list.")
                    continue

                for item in faqs:
                    if not item or not item.get('question') or not item.get('answer'):
                        continue

                    question = item.get('question', '')
                    answer = item.get('answer', '')

                    # --- ENRICH CONTENT ---
                    # We inject metadata into the text so the AI knows the context

                    content = (
                        f"Company: {company}\n"
                        f"Category: {category}\n"
                        f"Question: {question}\n"
                        f"Answer: {answer}"
                    )

                    # --- CREATE DOCUMENT WITH METADATA ---
                    # We also save fields as metadata for filtering later
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": filename,
                            "company": company,
                            "category": category,
                            "last_updated": last_updated,
                            "question": question 
                        }
                    )
                    documents.append(doc)
        except Exception as e:
            print(f"⚠️ Error reading file {filename}: {e}")

    print(f"✅ Successfully created {len(documents)} document entries with metadata.")

    return documents

def initialize_embedding_model(model_name: str):
    """
    Initializes the HuggingFace embedding model on CPU.
    """
    print(f"\n=== STEP 2: INITIALIZING EMBEDDING MODEL ===")
    print(f"Loading model: {model_name}...")
    
    try:
        # OPTIMIZATION: Force CPU usage to save GPU VRAM for the LLM
        embeddings = FastEmbedEmbeddings(
            model_name=model_name,
            cache_dir=str(cache_dir),
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True} 
        )
        print("✅ Embedding model loaded (Running on CPU).")
    
        return embeddings
    except Exception as e:
        print(f"❌ Failed to initialize embedding model: {e}")
        raise

def create_vector_store(documents: List[Document], embeddings, persist_path: str) -> Chroma:

    """
    Creates a Chroma vector store from documents and embeddings, saving it to disk.
    """
    print(f"\n=== STEP 3: CREATING VECTOR STORE ===")

    try:
        print(f"💾 Processing {len(documents)} documents...")

        # Recreate vector store after deletion
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=str(persist_path),
            collection_name="faq_collection"
        )

        print(f"✅ Successfully saved {len(documents)} vectors to '{persist_path}'")
        return vector_store

    except Exception as e:
        print(f"❌ Failed to create vector store: {e}")
        raise

def save_documents_to_csv(documents: List[Document], save_dir: str, csv_name="meta_documents.csv"):
    """
    Save a list of Document objects to a CSV file for inspection.

    Each row contains metadata and a preview of the content.
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)  # ensure folder exists

    csv_path = save_dir / csv_name
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=["source", "company", "category", "last_updated", "question", "answer", "content_preview"]
            )
            writer.writeheader()
            for doc in documents:
                writer.writerow({
                    "source": doc.metadata.get("source", ""),
                    "company": doc.metadata.get("company", ""),
                    "category": doc.metadata.get("category", ""),
                    "last_updated": doc.metadata.get("last_updated", ""),
                    "question": doc.metadata.get("question", ""),
                    "answer": doc.page_content.split("Answer: ")[-1],  
                    "content_preview": doc.page_content[:500] 
                })
        print(f"💾 Documents preview saved to CSV: {csv_path}")
    except Exception as e:
        print(f"⚠️ Error saving CSV: {e}")

def main():
    """Orchestrates the ingestion pipeline."""
    try:
        documents = load_documents(KNOWLEDGE_DIR)
        save_documents_to_csv(documents, csv_dir)
        if documents is not None and len(documents) > 0:
            embeddings = initialize_embedding_model(EMBEDDING_MODEL)        
            vector_store = create_vector_store(documents, embeddings, DB_PATH)
        else:
            print("🛑 Stopping: No documents to process.")
            
    except Exception as e:
        print(f"\n💥 Fatal Error: {e}")


if __name__ == "__main__":
    main()