import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "phi3:mini")
PULL_TIMEOUT = int(os.getenv("OLLAMA_PULL_TIMEOUT", "600"))


def _tags_url() -> str:
    return f"{OLLAMA_BASE_URL}/api/tags"


def _is_model_present(model_name: str) -> bool:
    """Return True if the exact model tag already exists locally."""
    resp = requests.get(_tags_url(), timeout=5)
    resp.raise_for_status()
    local_names = {m["name"] for m in resp.json().get("models", [])}
    # Exact match first; fall back to name without digest suffix
    return model_name in local_names or any(
        m.split(":")[0] == model_name.split(":")[0]
        and m.split(":")[-1] == model_name.split(":")[-1]
        for m in local_names
    )


def wait_for_ollama(
    *,
    poll_interval: float = 3.0,
    timeout: Optional[float] = None,
) -> None:
    """Block until Ollama's /api/tags responds 200, then return."""
    deadline = time.monotonic() + timeout if timeout else None

    while True:
        try:
            resp = requests.get(_tags_url(), timeout=3)
            if resp.ok:
                return
        except requests.RequestException as exc:
            print(f"Ollama not yet reachable with {exc}")

        if deadline and time.monotonic() >= deadline:
            raise TimeoutError(
                f"Ollama did not become reachable within {timeout}s"
            )
        time.sleep(poll_interval)


def pull_model(model_name: str = LLM_MODEL) -> None:
    """Pull *model_name* if it is not already present, streaming progress."""
    print("Checking model '%s' …", model_name)

    if _is_model_present(model_name):
        print("Model '%s' already present — skipping pull.", model_name)
        return
    with requests.post(
        f"{OLLAMA_BASE_URL}/api/pull",
        json={"name": model_name},
        stream=True,
        timeout=PULL_TIMEOUT,
    ) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_lines():
            if chunk:return

    # Verify the pull actually succeeded
    if not _is_model_present(model_name):
        raise RuntimeError(
            f"Pull of '{model_name}' completed but model not found in /api/tags."
        )

def setup(
    *,
    wait_timeout: Optional[float] = None,
    model_name: str = LLM_MODEL,
) -> None:
    """Call once at application startup."""
    wait_for_ollama(timeout=wait_timeout)
    pull_model(model_name)