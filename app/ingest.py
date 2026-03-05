import os
import json
import shutil
from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# --- CONFIGURATION ---
KNOWLEDGE_DIR = "knowledge/faqs/"  
DB_PATH = "chroma_db"     
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_documents(directory: str) -> List[Document]:
    """
    Reads JSON files, extracts global context (company, category), 
    and maps them to individual FAQ items.
    """
    print(f"=== STEP 1: LOADING DOCUMENTS FROM '{directory}' ===")
    
    if not os.path.exists(directory):
        print(f"❌ Error: Directory '{directory}' not found.")
        return []

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
                    # Skip empty objects
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
                            "question": question # Useful for debugging
                        }
                    )
                    documents.append(doc)
                    
        except Exception as e:
            print(f"⚠️ Error reading file {filename}: {e}")

    print(f"✅ Successfully loaded {len(documents)} document entries with metadata.")
    return documents

def initialize_embedding_model(model_name: str) -> HuggingFaceEmbeddings:
    """
    Initializes the HuggingFace embedding model on CPU.
    """
    print(f"\n=== STEP 2: INITIALIZING EMBEDDING MODEL ===")
    print(f"Loading model: {model_name}...")
    
    try:
        # OPTIMIZATION: Force CPU usage to save GPU VRAM for the LLM
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True} 
        )
        print("✅ Embedding model loaded (Running on CPU).")
        
        # Visualization
        print("\n🔬 VISUALIZATION: Testing Vector Conversion...")
        sample_text = "This is a test sentence."
        vector = embeddings.embed_query(sample_text)
        
        print(f"   Input: '{sample_text}'")
        print(f"   Vector Dimensions: {len(vector)}")
        print(f"   Vector Preview (First 5 values): {vector[:5]}")
        
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
    if os.path.exists(persist_path):
        print(f"🧹 Cleaning up old database at '{persist_path}'...")
        shutil.rmtree(persist_path)

    if not documents:
        print("⚠️ No documents provided to store. Skipping vector store creation.")
        return None

    try:
        print(f"💾 Processing {len(documents)} documents...")
        
        # This takes your list of Documents, converts text to vectors, and saves to disk.
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_path
        )
        
        print(f"✅ Successfully saved {len(documents)} vectors to '{persist_path}'")
        return vector_store
    except Exception as e:
        print(f"❌ Failed to create vector store: {e}")
        raise

def verify_search(vector_store: Chroma, query: str) -> None:
    """
    Performs a test search on the created vector store to verify it works.
    """
    print(f"\n=== STEP 4: VERIFYING SEARCH ===")
    print(f"🔍 Searching for: '{query}'...")
    
    try:
        results = vector_store.similarity_search(query, k=5)
        
        if results:
            print("\n🔥 TOP MATCH FOUND:")
            print(results[0].page_content)
        else:
            print("⚠️ No results found for the query.")
    except Exception as e:
        print(f"❌ Search failed: {e}")

def inspect_vector_store(vector_store: Chroma, num_items: int = 5):
    """
    Retrieves and prints raw data from the vector store to verify structure.
    """
    print(f"\n=== STEP 4: INSPECTING STORED DATA ===")
    
    try:
        # 1. Get the raw data from the internal collection 'include' lets us specify exactly what we want to see
        raw_data = vector_store._collection.get(
            limit=num_items, 
            include=["metadatas", "documents", "embeddings"]
        )
        
        # Extract lists
        ids = raw_data.get('ids', [])
        documents = raw_data.get('documents', [])
        metadatas = raw_data.get('metadatas', [])
        embeddings = raw_data.get('embeddings', [])

        print(f"🔬 Displaying first {len(ids)} entries from database...\n")
        
        # 2. Loop and Print
        for i in range(len(ids)):
            print(f"--- Entry #{i+1} ---")
            print(f"ID: {ids[i]}")
            
            # A. The Stored Text
            print(f"Stored Text:\n{documents[i][:250]}...") # Print first 250 chars
            
            # B. The Stored Metadata
            print(f"Metadata: {metadatas[i]}")
            
            # C. The Vector (First 5 numbers)
            # if embeddings:
                # NEW (Safe)
            if embeddings is not None and len(embeddings) > 0:
                print(f"Vector (First 5 dims): {embeddings[i][:10]}...")
            
            print("")

    except Exception as e:
        print(f"❌ Inspection failed: {e}")

def test_similarity_search(vector_store: Chroma, query: str):
    """
    Performs a similarity search and displays match scores.
    """
    print(f"\n=== STEP 5: TESTING SIMILARITY (MATCH PERCENTAGE) ===")
    print(f"User Query: '{query}'\n")

    try:
        # 1. Perform the search
        # 'k=3' returns the top 3 matches
        results = vector_store.similarity_search_with_score(query, k=10)

        if not results:
            print("No results found.")
            return

        print("🔬 Top Matches Found:\n")

        # 2. Loop through results
        for i, (doc, score) in enumerate(results):
            # 'score' is the Distance (Lower is better for distance)
            # We convert it to a percentage-like score for easier reading
            # Assuming Cosine Distance: Score = 1 - distance
            
            distance = score
            similarity_percentage = (1 - distance) * 100  # Convert to %

            print(f"--- Match #{i+1} ---")
            print(f"📊 Similarity Score: {similarity_percentage:.2f}%")
            print(f"📏 Distance:         {distance:.4f}")
            
            # Print the relevant part of the content
            print(f"Content Preview:     {doc.page_content[:100]}...")
            print(f"Metadata:            {doc.metadata}")
            print("")

    except Exception as e:
        print(f"❌ Search failed: {e}")

def run_precision_audit(vector_store: Chroma):
    """
    Performs a comprehensive audit on the ENTIRE database.
    """
    print("\n" + "="*50)
    print("🔍 RUNNING FULL PRECISION AUDIT")
    print("="*50)

    # 1. Get EVERYTHING
    try:
        # We request embeddings, documents, and metadatas
        all_data = vector_store._collection.get(
            include=["metadatas", "documents", "embeddings"]
        )
    except Exception as e:
        print(f"❌ CRITICAL: Could not retrieve data: {e}")
        return

    ids = all_data.get('ids', [])
    documents = all_data.get('documents', [])
    metadatas = all_data.get('metadatas', [])
    embeddings = all_data.get('embeddings') # Returns None if missing, or List[List[float]]

    total_items = len(ids)
    print(f"📊 Total Items Found in DB: {total_items}")

    if total_items == 0:
        print("❌ FAIL: Database is empty!")
        return

    # --- CHECK 1: Source File Coverage ---
    found_sources = set()
    for meta in metadatas:
        source = meta.get('source', 'Unknown')
        found_sources.add(source)
    
    print(f"📂 Unique Source Files Loaded: {len(found_sources)}")
    for src in sorted(found_sources):
        print(f"   - {src}")

    # --- CHECK 2: Integrity Loop ---
    print("\n--- Running Integrity Checks on All Items ---")
    
    errors_found = 0
    valid_embeddings_count = 0
    
    # FIX: Check if embeddings list exists AND has items
    has_embeddings = embeddings is not None and len(embeddings) > 0

    for i in range(total_items):
        # A. Check Text
        doc_text = documents[i]
        if not doc_text or len(doc_text) < 10:
            print(f"❌ ERROR (ID: {ids[i]}): Document text is too short or empty.")
            errors_found += 1

        # B. Check Metadata
        meta = metadatas[i]
        if not meta.get('company') or not meta.get('question'):
            print(f"❌ ERROR (ID: {ids[i]}): Missing critical metadata.")
            errors_found += 1

        # C. Check Vector
        if has_embeddings:
            # We have the matrix, now check the specific row 'i'
            vector = embeddings[i]
            if len(vector) == 384:
                valid_embeddings_count += 1
            else:
                print(f"❌ ERROR (ID: {ids[i]}): Wrong vector size {len(vector)}.")
                errors_found += 1
        else:
            print(f"❌ ERROR: Embeddings were not retrieved from DB.")
            errors_found += 1
            break # No point continuing if no embeddings exist

    # --- FINAL REPORT ---
    print("\n" + "="*50)
    print("📊 AUDIT REPORT")
    print("="*50)
    print(f"Total Items Checked: {total_items}")
    print(f"Valid Vectors:       {valid_embeddings_count}/{total_items}")
    
    if errors_found == 0:
        print("\n✅ STATUS: ALL FILES PROCESSED SUCCESSFULLY.")
        print("✅ STATUS: NO DATA CORRUPTION DETECTED.")
    else:
        print(f"\n⚠️ STATUS: DETECTED {errors_found} ERRORS.")

    print("="*50)

def main():
    """Orchestrates the ingestion pipeline."""
    try:
        documents = load_documents(KNOWLEDGE_DIR)
        embeddings = initialize_embedding_model(EMBEDDING_MODEL)        
        if documents:
            vector_store = create_vector_store(documents, embeddings, DB_PATH)
            
            if vector_store:
                # inspect_vector_store(vector_store)
                
                verify_search(vector_store, "food")
                test_similarity_search(vector_store, "food")

                run_precision_audit(vector_store)
                # visualize_tokenization(" SpaceWing was founded on January 15, 2025, by a team of visionary aerospace engineers, entrepreneurs, and space enthusiasts.")
        # else:
        #     print("🛑 Stopping: No documents to process.")
            
    except Exception as e:
        print(f"\n💥 Fatal Error: {e}")

if __name__ == "__main__":
    main()