import os
import csv
from pathlib import Path
import json
from typing import List

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings

# for chunking.... 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from uuid import uuid4
import tiktoken


COLLECTION_NAME     = "faq_collection"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_CACHE_DIR = "/app/fastembed_cache"
DB_PATH = Path("vector_db")
CSV_DIR = Path("CSV")


def check_chunking(content:str,metadata:dict,max_tokens:int=512)-> List[Document]:
    enc = tiktoken.get_encoding("cl100k_base")
    token_count = len(enc.encode(content))
    base_id = str(uuid4())

    if token_count <= max_tokens:
        return [
            Document(
                page_content=content,
                metadata={**metadata, "chunk_index": 1, "total_chunks": 1, "parent_id": base_id},
                id=f"{base_id}_1"
            )
        ]
    
     # header = Company + Category + Question lines (always repeat in every chunk)
    lines = content.split("\n")
    header_lines = [l for l in lines if l.startswith(("Company:", "Category:", "Question:"))]
    header = "\n".join(header_lines)  # this gets prepended to every chunk

    answer_part = content.split("Answer: ", 1)[-1]

    # budget: how many tokens left for answer after header
    header_tokens = len(enc.encode(header + "\nAnswer: "))
    answer_budget = 450 - header_tokens   # leave room for header


    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=answer_budget,
        chunk_overlap=40,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    answer_chunks = splitter.split_text(answer_part)
    base_id       = str(uuid4())
    total         = len(answer_chunks)

    return [
        Document(
            page_content=f"{header}\nAnswer: {chunk}",
            metadata={**metadata, "chunk_index": i + 1, "total_chunks": total, "parent_id": base_id},
            id=f"{base_id}_{i + 1}"
        )
        for i, chunk in enumerate(answer_chunks)
    ]

class Ingestor:
    """
    Encapsulates the ingestion pipeline: loading documents, creating embeddings,
    building the vector store, and saving document metadata to CSV.
    """

    def __init__(self,
                 knowledge_dir: str = "knowledge/FAQS",
                 db_path: str = DB_PATH,
                 csv_dir: str = "CSV",
                 embedding_model: str = EMBEDDING_MODEL,
                 cache_dir: str = EMBEDDING_CACHE_DIR):
        
        self.knowledge_dir = Path(knowledge_dir)
        self.db_path = Path(db_path)
        self.csv_dir = Path(csv_dir)
        self.embedding_model = embedding_model
        self.cache_dir = Path(cache_dir)
        

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.marker_file = self.db_path / ".db_ready"

    # -------------------- Document Loading --------------------
    def load_documents(self) -> List[Document]:
        """Load JSON documents and convert them into Document objects for chroma"""
        
        if not self.knowledge_dir.is_dir():
             raise FileNotFoundError(f"Directory '{self.knowledge_dir}' not found.")
        
        print(f"=== STEP 1: loading files from {self.knowledge_dir} exits ????'")

        files = [f for f in os.listdir(self.knowledge_dir) if f.endswith(".json")]

        print(f'total number of files : {len(files)}')
        if not files:
            raise FileNotFoundError(f"No JSON files found in '{self.knowledge_dir}'.")

        documents: List[Document] = []

        for file_name in files:
            file_path = os.path.join(self.knowledge_dir, file_name)
            try:
             with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
     
                company = data.get("company", "Unknown Company")
                category = data.get("category", "General")
                last_updated = data.get("last_updated", "N/A")

                faqs = data.get("faqs", [])

                for _ ,item in enumerate(faqs):

                    if not item or not item.get('question') or not item.get('answer'):
                        continue

                    question = item.get('question', '')
                    answer = item.get('answer', '')

    
                    content = (
                        f"Company: {company}\n"
                        f"Category: {category}\n"
                        f"Question: {question}\n"
                        f"Answer: {answer}"
                    )

                    # We inject metadata into the text so the AI knows the context
                    metadata={
                            "source": file_name,
                            "company": company,
                            "category": category,
                            "last_updated": last_updated,
                            "question": question
                        }
                    
                    docs = check_chunking(content,metadata)
                    documents.extend(docs)

            except Exception as e:
                print(f"⚠️ Error reading {file_name}: {e}")
                raise RuntimeError(f"Failed to read {file_name}: {e}") from e
            
        print(f"✅ Successfully loaded {len(documents)} documents from {len(files)} files.")
        return documents    

    # -------------------- CSV Saving --------------------
    def save_to_csv(self, documents: List[Document], csv_name: str = "meta_documents.csv"):
        """Save document metadata to CSV."""

        csv_dir = CSV_DIR
        csv_dir.mkdir(parents=True, exist_ok=True)
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
                        "content_preview": doc.page_content[:200],
                    })
            print(f"💾 CSV saved at {csv_path}")
        except Exception as e:
            print(f"⚠️ Error saving CSV: {e}")

    # -------------------- Embeddings --------------------
    def initialize_embeddings(self):
        """Initialize embedding model."""
        try:
            embeddings =  FastEmbedEmbeddings(
                collection_name=COLLECTION_NAME,
                model=self.embedding_model,
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
    def create_vector_store(self, chunked_documents: List[Document], embeddings) -> Chroma:
        """Create Chroma vector store from documents."""
        try:
            print("\n🔍 Sample chunks BEFORE embedding:\n")

            vector_store = Chroma(
                embedding_function=embeddings,
                persist_directory=str(self.db_path),
                collection_name=COLLECTION_NAME,
            )
            vector_store.add_documents(documents=chunked_documents)

            print(f"✅ Vector store created at {self.db_path}")
            return vector_store
        except Exception as e:
            print(f"❌ Failed to create vector store: {e}")
            raise
    
    # -------------------- Full Ingestion --------------------
    def run_ingestion(self) -> bool:
        """Run the complete ingestion pipeline."""
        try:
            embeddings = self.initialize_embeddings()  
            if self.marker_file.exists():
                temp_store = Chroma(
                    persist_directory=str(self.db_path),
                    embedding_function=embeddings,
                    collection_name=COLLECTION_NAME,
                )
                count = temp_store._collection.count()
                if count > 0:
                    print(f"✅ DB already ingested ({count} docs). Skipping.")
                    return True
                else:
                    print("⚠️ Marker exists but DB is empty — re-ingesting...")
                    self.marker_file.unlink()

            # final doucuments contains both chunking and not chunking.....
            fdocuments = self.load_documents()

            enc = tiktoken.get_encoding("cl100k_base")

            over, under = 0, 0
            for doc in fdocuments:
                tokens = len(enc.encode(doc.page_content))
                if tokens > 512:
                    over += 1
                    print(f"OVER  {tokens:4d} tokens | {doc.metadata.get('question','')[:60]}")
                else:
                    under += 1

            print(f"\nunder 512: {under} | over 512: {over}")

            # print([i for i in fdocuments])
    
            if fdocuments:
                self.save_to_csv(fdocuments)
                self.create_vector_store(fdocuments, embeddings)  
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