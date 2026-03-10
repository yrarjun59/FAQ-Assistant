import os
import csv
from pathlib import Path
import json
import shutil
from typing import List

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
# from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import FastEmbedEmbeddings


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
                    # This allows the AI to answer "Who runs this company?"
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

# def initialize_embedding_model(model_name: str) -> HuggingFaceEmbeddings:
def initialize_embedding_model(model_name: str) -> FastEmbedEmbeddings:
    """
    Initializes the HuggingFace embedding model on CPU.
    """
    print(f"\n=== STEP 2: INITIALIZING EMBEDDING MODEL ===")
    print(f"Loading model: {model_name}...")
    
    try:
        # OPTIMIZATION: Force CPU usage to save GPU VRAM for the LLM
        # embeddings = HuggingFaceEmbeddings(
        embeddings = FastEmbedEmbeddings(
            model_name=model_name,
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
    
    # Clean up old database if it exists to ensure fresh data
    if persist_path.exists() and persist_path.is_dir():
        print(f"🧹 Cleaning up old database at '{persist_path}'...")
        shutil.rmtree(persist_path)

    elif not persist_path.exists():
        print(f"📂 Creating new database directory '{persist_path}'...")
        os.makedirs(persist_path, exist_ok=True)

    try:
        print(f"💾 Processing {len(documents)} documents...")
        
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=str(persist_path)
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

def verify_search(vector_store: Chroma, query: str) -> None:
    """
    Performs a test search on the created vector store to verify it works.
    """
    print(f"\n=== STEP 4: VERIFYING SEARCH ===")
    print(f"🔍 Searching for: '{query}'...")
    
    try:
        results = vector_store.similarity_search(query, k=3)
        
        if results:
            print("\n🔥 TOP MATCH FOUND:")
            print(results[0].page_content)
        else:
            print("⚠️ No results found for the query.")
    except Exception as e:
        print(f"❌ Search failed: {e}")

def inspect_vector_store(vector_store: Chroma, limit: int = 5):
    """Print sample entries from the vector store."""

    print("\n🔎 Inspecting Vector Store")

    try:
        data = vector_store._collection.get(
            limit=limit,
            include=["documents", "metadatas"]
        )

        ids = data.get("ids", [])
        docs = data.get("documents", [])
        metas = data.get("metadatas", [])

        for i in range(len(ids)):
            print(f"\n--- Item {i+1} ---")
            print("ID:", ids[i])
            print("Text:", docs[i][:150], "...")
            print("Metadata:", metas[i])

    except Exception as e:
        print("❌ Inspection failed:", e)

def test_similarity_search(vector_store: Chroma, query: str, k: int = 5):
    """Test semantic search results."""

    print(f"\n🔎 Testing Query: {query}")

    try:
        results = vector_store.similarity_search_with_score(query, k=k)

        for i, (doc, score) in enumerate(results):
            similarity = (1 - score) * 100

            print(f"\n--- Result {i+1} ---")
            print(f"Similarity: {similarity:.2f}%")
            print("Text:", doc.page_content[:120], "...")
            print("Metadata:", doc.metadata)

    except Exception as e:
        print("❌ Search failed:", e)


def main():
    """Orchestrates the ingestion pipeline."""
    try:
        documents = load_documents(KNOWLEDGE_DIR)
        save_documents_to_csv(documents, csv_dir)
        if documents is not None and len(documents) > 0:
            embeddings = initialize_embedding_model(EMBEDDING_MODEL)        
            vector_store = create_vector_store(documents, embeddings, DB_PATH)
            
            if vector_store is not None:
                inspect_vector_store(vector_store)
                data = vector_store._collection.get()

                print(len(data["documents"]))
                print(data["documents"][0])
                print(data["metadatas"][0])

                print(verify_search(vector_store, "fuck"))
                print(test_similarity_search(vector_store, "pussy"))
        else:
            print("🛑 Stopping: No documents to process.")
            
    except Exception as e:
        print(f"\n💥 Fatal Error: {e}")


if __name__ == "__main__":
    main()