import os
import time
import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
LLM_MODEL       = os.getenv("LLM_MODEL", "llama3.2:1b")


def wait_for_ollama():
    """Block until Ollama is reachable."""
    print("Waiting for Ollama to be ready...")
    while True:
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if r.ok:
                print("Ollama is ready.")
                return
        except Exception:
            pass
        time.sleep(3)


def pull_model():
    """Pull LLM_MODEL if not already downloaded."""
    print(f"Checking model {LLM_MODEL}...")
    try:
        r      = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        models = [m["name"] for m in r.json().get("models", [])]

        if any(LLM_MODEL in m for m in models):
            print(f"Model {LLM_MODEL} already exists — skipping pull.")
            return

        print(f"Pulling {LLM_MODEL}… this may take a few minutes.")
        requests.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": LLM_MODEL},
            timeout=600,
        )
        print("Model ready.")
    except Exception as e:
        print(f"Warning: could not pull model: {e}")


def setup():
    """Call once at app startup."""
    wait_for_ollama()
    pull_model()