import streamlit as st
import requests, os, time
from pathlib import Path

import history  

BASE_URL = os.getenv("STELLA_API_URL", "http://backend:8000") + "/chat"

HEALTH_URL = BASE_URL.replace("/chat", "/")

st.set_page_config(page_title="Stella", page_icon="✨")

# ── CSS — loaded from style.css 
css = (Path(__file__).parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = history.load()

# ── Header  
col1, col2 = st.columns([8, 1])
with col1:
    st.title("✨ Stella")
with col2:
    if st.session_state.messages:
        if st.button("clear", help="Clear chat history"):
            st.session_state.messages = []
            history.clear()
            st.rerun()

# ── Helper: render sources + time badge
def show_meta(sources: list, elapsed) -> None:
    if sources:
        items = "".join(
                    f'<div class="src-item">· <a href="http://localhost:8000/file/{s}" '
                    f'target="_blank" style="color:#94a3b8;text-decoration:underline;'
                    f'text-underline-offset:3px;text-decoration: none;">{s}</a></div>'
            for s in sources )
        st.markdown(
            f'<div class="sources-block"><div class="src-title">Sources</div>{items}</div>',
            unsafe_allow_html=True,
        )
    if elapsed is not None:
        st.markdown(f'<span class="time-badge">⏱ {elapsed}s</span>', unsafe_allow_html=True)

# ── Helper: typewriter effect  
def typewrite(text: str) -> str:
    placeholder = st.empty()
    displayed   = ""
    delay = max(0.02, min(0.02, 4.0 / max(len(text), 1)))
    for char in text:
        displayed += char
        placeholder.markdown(displayed + "▌")
        time.sleep(delay)
    placeholder.markdown(displayed)
    return displayed

def wait_for_backend():
    """Send a dummy POST to /chat to confirm it's ready."""
    with st.status("⏳ Backend is starting up, please wait...", expanded=False) as s:
        for attempt in range(30):
            try:
                r = requests.post(
                    BASE_URL,
                    json={"query": "ping"},   # dummy query
                    timeout=5,
                )
                # any response = /chat is up and reachable
                # 200, 400, 422, 500 all mean server is ready
                # only ConnectionError means not ready
                if r.status_code != 503:
                    s.update(label="✅ Backend is ready!", state="complete")
                    return True
            except requests.exceptions.ConnectionError:
                pass   # not ready yet
            except Exception:
                pass
            s.update(label=f"⏳ Backend loading… ({attempt * 10}s elapsed)", state="running")
            time.sleep(10)
        s.update(label="❌ Backend unavailable.", state="error")
        return False

# ── Helper: call backend API  
def call_api(prompt: str) -> tuple:
    if not wait_for_backend():
        return "⚠ Backend did not become ready in time.", [], None
    try:
        t0 = time.time()
        r  = requests.post(BASE_URL, json={"query": prompt}, timeout=(5, 60))
        r.raise_for_status()
        data    = r.json()
        answer  = data.get("answer", "No response")
        sources = data.get("sources", [])
        elapsed = round(data.get("time_taken", time.time() - t0), 2)
        return answer, sources, elapsed
    except requests.exceptions.ConnectTimeout:
        return "⚠ Connection timed out.", [], None
    except requests.exceptions.ReadTimeout:
        return "⚠ Request timed out after 60s.", [], None
    except requests.exceptions.ConnectionError:
        return "⚠ Cannot connect to backend.", [], None
    except Exception as e:
        return f"⚠ {e}", [], None

# ── Render chat history 
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            show_meta(msg.get("sources", []), msg.get("time_taken"))

# ── Chat input 
if "pending" not in st.session_state:
    st.session_state.pending = None

prompt = st.chat_input("Ask anything…", disabled=st.session_state.pending is not None)

if prompt and st.session_state.pending is None:
    st.session_state.pending = prompt
    st.rerun()

if st.session_state.pending:
    q = st.session_state.pending
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        status = st.status("Searching documents…", expanded=False)
        answer, sources, elapsed = call_api(q)
        status.update(label="Done" if not answer.startswith("⚠") else "Error",
                      state="complete" if not answer.startswith("⚠") else "error")
        displayed = typewrite(answer)
        show_meta(sources, elapsed)
    st.session_state.messages += [
        {"role": "user", "content": q},
        {"role": "assistant", "content": displayed, "sources": sources, "time_taken": elapsed},
    ]
    history.save(st.session_state.messages)
    st.session_state.pending = None
    st.rerun()