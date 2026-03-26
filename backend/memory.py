# memory.py

from langchain_classic.memory import ConversationSummaryBufferMemory
from langchain_community.llms import Ollama

import tiktoken

# --- tokenizer ---
enc = tiktoken.get_encoding("cl100k_base")

def token_len(text: str) -> int:
    return len(enc.encode(text))


# --- custom LLM with tokenizer ---
class OllamaWithTokenizer(Ollama):
    def get_num_tokens(self, text: str) -> int:
        return token_len(text)

     # optional but good practice
    def get_num_tokens(self, text: str) -> int:
        return len(self.get_token_ids(text))


# --- memory factory ---
def create_memory(llm):
    """
    Memory with:
    - recent buffer
    - summarized history
    - custom tokenizer (no GPT-2 fallback warning)
    """

    memory = ConversationSummaryBufferMemory(
        llm=llm,
        max_token_limit=600,
        memory_key="chat_history",
        return_messages=True
    )

    return memory