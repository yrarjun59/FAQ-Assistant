import streamlit as st
import requests
import os
import time
from pathlib import Path

import history

# ── Config ────────────────────────────────────────────────────────────────────
_BASE = os.getenv("STELLA_API_URL", "http://backend:8000")
CHAT_URL   = f"{_BASE}/chat"
HEALTH_URL = f"{_BASE}/health"   

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Stella", page_icon="✨")

css_path = Path(__file__).parent / "style.css"
if css_path.exists():                             
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = history.load()

if "pending" not in st.session_state:
    st.session_state.pending = None

if "backend_ready" not in st.session_state:      
    st.session_state.backend_ready = False   

# ── Header ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([8, 1])
with col1:
    st.title("✨ Stella")
with col2:
    if st.session_state.messages:
        if st.button("Clear", help="Clear chat history"):
            st.session_state.messages = []
            history.clear()
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────
FILE_URL = "http://127.0.0.1:8000"

def show_meta(sources: list, elapsed) -> None:
    if sources:
        items = "".join(
            f'<div class="src-item">📚'
            f'<a href="{FILE_URL}/file/{s}" target="_blank" '  
            f'style="color:#94a3b8;text-decoration:none;list-style: none;">{s}</a>'
            f'</div>'
            for s in sources
        )
        st.markdown(
            f'<div class="sources-block"><div class="src-title">Sources</div>{items}</div>',
            unsafe_allow_html=True,
        )
    if elapsed is not None:
        st.markdown(
            f'<span class="time-badge">⏱ {elapsed}s</span>',
            unsafe_allow_html=True,
        )


def typewrite(text: str) -> str:
    placeholder = st.empty()
    displayed = ""
    delay = min(0.025, 2.5 / max(len(text), 1))
    for char in text:
        displayed += char
        placeholder.markdown(displayed + "▌")
        time.sleep(delay)
    placeholder.markdown(displayed)
    return displayed


def wait_for_backend() -> bool:
    if st.session_state.backend_ready:
        return True

    max_wait_seconds = 300   # 5 min — enough for cold Ollama model pull
    poll_interval    = 5
    max_attempts     = max_wait_seconds // poll_interval

    with st.status("⏳ Backend is starting up, please wait…", expanded=False) as s:
        for attempt in range(max_attempts):
            try:
                r = requests.get(HEALTH_URL, timeout=4)
                if r.status_code == 200:
                    s.update(label="✅ Backend is ready!", state="complete")
                    st.session_state.backend_ready = True
                    return True
                # 503 = still loading (Stella not initialized yet), keep waiting
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout):
                pass   # container not up yet

            elapsed_s = attempt * poll_interval
            s.update(
                label=f"⏳ Backend loading… ({elapsed_s}s elapsed)",
                state="running",
            )
            time.sleep(poll_interval)

        s.update(label="❌ Backend unavailable after 5 min.", state="error")
        return False


def call_api(prompt: str) -> tuple[str, list, float | None]:
    """Call /chat. Returns (answer, sources, elapsed_seconds)."""
    if not wait_for_backend():
        return "⚠ Backend did not become ready in time.", [], None

    try:
        r = requests.post(CHAT_URL, json={"query": prompt}, timeout=(5, 120))  
        r.raise_for_status()
        data    = r.json()
        answer  = data.get("answer", "No response.")
        sources = data.get("sources", [])
        elapsed = round(data.get("time_taken", 0.0), 2)
        return answer, sources, elapsed

    except requests.exceptions.ConnectTimeout:
        st.session_state.backend_ready = False   
        return "⚠ Connection timed out.", [], None
    except requests.exceptions.ReadTimeout:
        return "⚠ Request timed out — the model is taking too long.", [], None
    except requests.exceptions.ConnectionError:
        st.session_state.backend_ready = False   # FIX 9
        return "⚠ Cannot connect to backend.", [], None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        return f"⚠ Server error {status}: {detail or str(e)}", [], None
    except Exception as e:
        return f"⚠ Unexpected error: {e}", [], None


# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            show_meta(msg.get("sources", []), msg.get("time_taken"))

# ── Chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input(
    "Ask anything…",
    disabled=st.session_state.pending is not None,
)

if prompt and st.session_state.pending is None:
    st.session_state.pending = prompt
    st.rerun()

# ── Process pending message ───────────────────────────────────────────────────
if st.session_state.pending:
    q = st.session_state.pending

    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        status_widget = st.status("Searching documents…", expanded=False)
        answer, sources, elapsed = call_api(q)

        is_error = answer.startswith("⚠")
        status_widget.update(
            label="Done" if not is_error else "Error",
            state="complete" if not is_error else "error",
        )
        displayed = typewrite(answer)
        show_meta(sources, elapsed)

    st.session_state.messages = st.session_state.messages + [
        {"role": "user",      "content": q},
        {"role": "assistant", "content": displayed, "sources": sources, "time_taken": elapsed},
    ]
    history.save(st.session_state.messages)
    st.session_state.pending = None
    st.rerun()