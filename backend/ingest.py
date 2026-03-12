import os
import csv
from pathlib import Path
import json
from typing import List

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings


class Ingestor:
    """
    Encapsulates the ingestion pipeline: loading documents, creating embeddings,
    building the vector store, and saving document metadata to CSV.
    """

    def __init__(self,
                 knowledge_dir: str = "knowledge/FAQS",
                 db_path: str = "vector_db",
                 csv_dir: str = "CSV",
                 embedding_model: str = "BAAI/bge-small-en-v1.5",
                 cache_dir: str = "/app/fastembed_cache"):
        
        self.knowledge_dir = Path(knowledge_dir)
        self.db_path = Path(db_path)
        self.csv_dir = Path(csv_dir)
        self.embedding_model = embedding_model
        self.cache_dir = Path(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

        # Marker file to indicate ingestion is done
        self.marker_file = self.db_path / ".db_ready"

    # -------------------- Document Loading --------------------
    def load_documents(self) -> List[Document]:
        """Load JSON documents and convert them into Document objects."""
        
        if not self.knowledge_dir.is_dir():
             raise FileNotFoundError(f"Directory '{self.knowledge_dir}' not found.")
        
        print(f"=== STEP 1: loading files from {self.knowledge_dir} exits ????'")

        files = [f for f in os.listdir(self.knowledge_dir) if f.endswith(".json")]
        print(f'len of files : {len(files)}')
        if not files:
            raise FileNotFoundError(f"No JSON files found in '{self.knowledge_dir}'.")

        documents: List[Document] = []

        for file_name in files:
            file_path = os.path.join(self.knowledge_dir, file_name)
            print(f'File Path : {file_path}')
            try:
             with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                company = data.get("company", "Unknown Company")
                category = data.get("category", "General")
                last_updated = data.get("last_updated", "N/A")
            
                faqs = data.get("faqs", [])
                        
                if not isinstance(faqs, list):
                    print(f"⚠️ Skipping {file_name}: 'faqs' key is not a list.")
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
                            "source": file_name,
                            "company": company,
                            "category": category,
                            "last_updated": last_updated,
                            "question": question 
                        }
                    )
                    documents.append(doc)
            except Exception as e:
                print(f"⚠️ Error reading {file_name}: {e}")
                raise RuntimeError(f"Failed to read {file_name}: {e}") from e
        print(f"✅ Successfully loaded {len(documents)} documents from {len(files)} files.")
        return documents

    # -------------------- CSV Saving --------------------
    def save_to_csv(self, documents: List[Document], csv_name: str = "meta_documents.csv"):
        """Save document metadata to CSV."""

        self.csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self.csv_dir / csv_name
        print(f'csv path: {csv_path}')
        
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["source","company","category","last_updated","question","answer","content_preview"])
                writer.writeheader()
                for doc in documents:
                    writer.writerow({
                        "source": doc.metadata.get("source", ""),
                        "company": doc.metadata.get("company", ""),
                        "category": doc.metadata.get("category", ""),
                        "last_updated": doc.metadata.get("last_updated", ""),
                        "question": doc.metadata.get("question", ""),
                        "answer": doc.page_content.split("Answer: ")[-1],
                        "content_preview": doc.page_content[:500],
                    })
            print(f"💾 CSV saved at {csv_path}")
        except Exception as e:
            print(f"⚠️ Error saving CSV: {e}")

    # -------------------- Embeddings --------------------
    def initialize_embeddings(self):
        """Initialize embedding model."""
        try:
            embeddings =  FastEmbedEmbeddings(
                model_name=self.embedding_model,
                cache_dir=str(self.cache_dir),
                model_kwargs={"device":"cpu"},
                encode_kwargs={"normalize_embeddings": True}
                )
            print("✅ Embedding model ready")
            return embeddings
        except Exception as e:
            print(f"❌ Failed to initialize embeddings: {e}")
            raise

    # -------------------- Vector Store --------------------
    def create_vector_store(self, documents: List[Document], embeddings) -> Chroma:
        """Create Chroma vector store from documents."""
        try:
            vector_store = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=str(self.db_path),
                collection_name="faq_collection"
            )
            print(f"✅ Vector store created at {self.db_path}")
            return vector_store
        except Exception as e:
            print(f"❌ Failed to create vector store: {e}")
            raise
    
    # -------------------- Full Ingestion --------------------
    def run_ingestion(self) -> bool:
        """Run the complete ingestion pipeline."""
        try:
            embeddings = self.initialize_embeddings()  # ← initialize ONCE here
            if self.marker_file.exists():
                temp_store = Chroma(
                    persist_directory=str(self.db_path),
                    embedding_function=embeddings,
                    collection_name="faq_collection"
                )
                count = temp_store._collection.count()
                if count > 0:
                    print(f"✅ DB already ingested ({count} docs). Skipping.")
                    return True
                else:
                    print("⚠️ Marker exists but DB is empty — re-ingesting...")
                    self.marker_file.unlink()

            documents = self.load_documents()

            if documents:
                self.save_to_csv(documents)
                self.create_vector_store(documents, embeddings)  # ← reuses same instance
                self.db_path.mkdir(parents=True, exist_ok=True)
                self.marker_file.touch()
                print(f"✅ Ingestion complete. Marker file: {self.marker_file}")
                return True
            else:
                print("🛑 No documents to process.")
                return False
        except Exception as e:
            print(f"\n💥 Fatal Error: {e}")
            return False


if __name__ == "__main__":
    ingestor = Ingestor()
    ingestor.run_ingestion()