from sentence_transformers import SentenceTransformer
from transformers.utils.logging import set_verbosity_error
import torch
import time

set_verbosity_error()


x = torch.rand(5, 3)
print(x)


print(f"Version: {torch.__version__}, GPU: {torch.cuda.is_available()}, NUM_GPU: {torch.cuda.device_count()}")

# print(f"Is CUDA available? {torch.cuda.is_available()}")
# print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

sentences = ["The key idea behind RAG is to synthesize the accuracy and search capabilities of information retrieval techniques typically used by search engines, "
"with the in-depth language understanding and generation capabilities of LLMs."]

start = time.time()
#1 - for fast
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# 2 for accuracy
# model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
embeddings = model.encode(sentences)

print(f"Time taken for this model {time.time()-start:.2f}s")

print(embeddings)

# print(model.deencode(embeddings))
