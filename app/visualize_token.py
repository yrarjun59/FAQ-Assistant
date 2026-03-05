from transformers import AutoTokenizer


def visualize_tokenization(text: str):
    print("\n=== BONUS: TOKENIZATION VISUALIZATION ===")
    # Load the tokenizer specific to our embedding model
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    
    # 1. Tokenize
    tokens = tokenizer.tokenize(text)
    ids = tokenizer.encode(text)
    
    print(f"Original Text: {text}")
    print(f"Tokens (Chunks): {tokens}")
    print(f"IDs (Numbers):   {ids}")
    print(f"Total Tokens:    {len(tokens)}")

