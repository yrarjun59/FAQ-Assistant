import os
import time
from typing import Optional, Set

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
PULL_TIMEOUT = int("600")

session = requests.Session()


# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
def _tags_url() -> str:
    return f"{OLLAMA_BASE_URL}/api/tags"


def _pull_url() -> str:
    return f"{OLLAMA_BASE_URL}/api/pull"


def _get_local_models() -> Set[str]:
    """Fetch all local model names."""
    resp = session.get(_tags_url(), timeout=5)
    resp.raise_for_status()
    return {m["name"] for m in resp.json().get("models", [])}


def _is_model_present(model_name: str, local_models: Optional[Set[str]] = None) -> bool:
    """Check model existence with optional cached list."""
    local_models = local_models or _get_local_models()

    if model_name in local_models:
        return True

    base, tag = model_name.split(":") if ":" in model_name else (model_name, "")
    return any(
        m.split(":")[0] == base and m.split(":")[-1] == tag
        for m in local_models
    )



def wait_for_ollama(
    *,
    poll_interval: float = 2.0,
    timeout: Optional[float] = None,
) -> None:
    """Wait until Ollama API is reachable."""
    deadline = time.monotonic() + timeout if timeout else None

    while True:
        try:
            resp = session.get(_tags_url(), timeout=3)
            if resp.ok:
                return
        except requests.RequestException:
            pass

        if deadline and time.monotonic() >= deadline:
            raise TimeoutError("Ollama not reachable within timeout")

        time.sleep(poll_interval)


def pull_model(model_name: str) -> str:
    """
    Ensure model exists locally.
    Pull if missing, stream progress, return model name.
    """
    print(f"🔍 Checking model: {model_name}")

    local_models = _get_local_models()
    if _is_model_present(model_name, local_models):
        print(f"✅ Model already available: {model_name}")
        return model_name

    print(f"⬇️ Pulling model: {model_name}")

    with session.post(
        _pull_url(),
        json={"name": model_name},
        stream=True,
        timeout=PULL_TIMEOUT,
    ) as resp:
        resp.raise_for_status()

    # Single verification (avoid repeated API calls)
    if not _is_model_present(model_name):
        raise RuntimeError(f"❌ Model '{model_name}' not found after pull")

    print(f"✅ Model ready: {model_name}")
    return model_name


def setup(
    *,
    wait_timeout: Optional[float] = None,
    model_name: str,
) -> str:
    """Initialize Ollama and ensure model is ready."""
    wait_for_ollama(timeout=wait_timeout)
    return pull_model(model_name)