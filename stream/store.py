import json
import os
import time
import streamlit as st

STORAGE_FILE = "chat_history.json"


def init_store():
    if "messages" not in st.session_state:
        st.session_state.messages = _load()
    if "streaming" not in st.session_state:
        st.session_state.streaming = False
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None


def add_user(text: str):
    st.session_state.messages.append({
        "role": "user", "text": text, "ts": time.time()
    })
    _save()


def add_assistant(text: str, sources: list, time_taken: float, error: str | None = None):
    st.session_state.messages.append({
        "role": "assistant", "text": text,
        "sources": sources, "time_taken": time_taken,
        "error": error, "ts": time.time()
    })
    _save()


def clear_history():
    st.session_state.messages = []
    _save()


def _load() -> list:
    try:
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save():
    try:
        with open(STORAGE_FILE, "w") as f:
            json.dump(st.session_state.messages, f, indent=2)
    except Exception:
        pass