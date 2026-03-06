import os
import requests
import time

API_BASE = os.environ.get("STELLA_API_URL", "http://backend:8000")


def ask(query: str, timeout: int = 60) -> dict:
    """Send query to Stella FastAPI backend. Returns dict with answer, sources, time_taken, error."""
    try:
        t0 = time.time()
        resp = requests.post(
            f"{API_BASE}/chat",
            json={"query": query},
            timeout=timeout,
        )
        elapsed = round(time.time() - t0, 2)

        if not resp.ok:
            detail = resp.json().get("detail", f"Error {resp.status_code}")
            return {"answer": "", "sources": [], "time_taken": elapsed, "error": detail}

        data = resp.json()
        data["time_taken"] = elapsed  # use client-side time for accuracy
        return data

    except requests.exceptions.ConnectionError:
        return {"answer": "", "sources": [], "time_taken": 0,
                "error": "Cannot connect to Stella API. Is the backend running?"}
    except requests.exceptions.Timeout:
        return {"answer": "", "sources": [], "time_taken": timeout,
                "error": "Request timed out. The backend took too long to respond."}
    except Exception as e:
        return {"answer": "", "sources": [], "time_taken": 0, "error": str(e)}


def health_check() -> bool:
    try:
        resp = requests.get(f"{API_BASE}/", timeout=3)
        return resp.ok
    except Exception:
        return False