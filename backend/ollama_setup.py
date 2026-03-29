import os
import time
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:1b")

session = requests.Session()


def wait_for_ollama() -> None:
    while True:
        try:
            if session.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3).ok:
                print("✅ Ollama ready.")
                return
        except requests.RequestException:
            pass
        print("⏳ Waiting for Ollama...")
        time.sleep(2)


def is_model_present(model_name: str) -> bool:
    resp = session.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
    resp.raise_for_status()
    return any(m["name"] == model_name for m in resp.json().get("models", []))


def pull_model(model_name: str) -> None:

    # resp = session.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
    # resp.raise_for_status()
    # local = [m["name"] for m in resp.json().get("models", [])]
    
    # print(f"Looking for: '{model_name}'")
    # print(f"Local models: {local}")

    
    if is_model_present(model_name):
        print(f"✅ Model already present: {model_name}")
        return

    print(f"⬇️  Downloading {model_name} — please wait...")
    resp = session.post(
        f"{OLLAMA_BASE_URL}/api/pull",
        json={"name": model_name, "stream": False},
        timeout=600,
    )
    resp.raise_for_status()
    print(f"✅ Model ready: {model_name}")

    if not is_model_present(model_name):
        raise RuntimeError(f"Pull failed: {model_name} not found after download.")

    print(f"✅ Model ready: {model_name}")


def setup() -> None:
    wait_for_ollama()
    pull_model(LLM_MODEL)

if __name__ == "__main__":
    setup()