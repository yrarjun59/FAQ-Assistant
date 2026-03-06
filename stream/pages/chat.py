import time
import json
import streamlit as st
from api import ask
from store import init_store, add_user, add_assistant, clear_history
from styles import inject

st.set_page_config(
    page_title="Stella · Chat", page_icon="✦",
    layout="centered", initial_sidebar_state="collapsed",
)
inject("chat")
init_store()

if "stop_flag"  not in st.session_state: st.session_state.stop_flag  = False
if "is_loading" not in st.session_state: st.session_state.is_loading = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ✦ Stella")
    st.caption("RAG Document Assistant")
    st.divider()

    if st.button("⌂ Home", use_container_width=True):
        st.switch_page("app.py")

    n = len(st.session_state.messages)
    st.caption(f"**{n}** message{'s' if n != 1 else ''}")

    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if user_msgs:
        st.caption("**Questions asked**")
        for i, m in enumerate(user_msgs[-8:], 1):
            t = m["text"]
            st.caption(f"{i}. {t[:42]}{'…' if len(t)>42 else ''}")
        st.divider()
        if st.button("🗑 Clear history", use_container_width=True):
            clear_history()
            st.switch_page("app.py")
        st.download_button(
            "⬇ Export", use_container_width=True,
            data=json.dumps(st.session_state.messages, indent=2),
            file_name="stella_history.json", mime="application/json",
        )

# ── CSS extras ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stFormSubmitButton"]{display:none!important}

/* Scroll FAB */
.fab-scroll {
    position: fixed; bottom: 28px; right: 22px; z-index: 999;
}
.fab-scroll a {
    display: flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; border-radius: 50%;
    background: rgba(15,22,36,.95); border: 1px solid #1e2d4a;
    color: #94a3b8; font-size: 15px; text-decoration: none;
    box-shadow: 0 2px 14px rgba(0,0,0,.45);
    transition: background .15s, border-color .15s, color .15s;
}
.fab-scroll a:hover { background:#192033; border-color:#4f8ef7; color:#4f8ef7; }

/* Logo button styled as plain text */
.logo-btn button {
    background: transparent !important;
    border: none !important; box-shadow: none !important;
    padding: 0 !important; min-height: unset !important;
    height: auto !important; width: auto !important;
    font-size: 1rem !important; font-weight: 700 !important;
    background: linear-gradient(90deg,#4f8ef7,#8b5cf6) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    cursor: pointer !important;
}
.logo-btn button:hover { opacity: .72 !important; }
.logo-btn button:focus { outline: none !important; box-shadow: none !important; }
</style>

<!-- Scroll to bottom FAB — uses anchor to bottom of page -->
<div class="fab-scroll">
  <a id="scroll-fab" href="#chat-bottom" title="Scroll to latest">↓</a>
</div>
<script>
document.getElementById('scroll-fab').addEventListener('click', function(e){
    e.preventDefault();
    var el = document.getElementById('chat-bottom');
    if(el) el.scrollIntoView({behavior:'smooth'});
});
</script>
""", unsafe_allow_html=True)

# ── Topbar — logo click = st.switch_page (internal Streamlit nav) ─────────────
top_logo, top_label = st.columns([2, 10])
with top_logo:
    st.markdown('<div class="logo-btn">', unsafe_allow_html=True)
    if st.button("✦ Stella", key="logo_home"):
        st.switch_page("app.py")
    st.markdown('</div>', unsafe_allow_html=True)
with top_label:
    st.markdown(
        '<p style="font-size:.68rem;color:#445069;margin:6px 0 0">RAG Document Intelligence</p>',
        unsafe_allow_html=True,
    )
st.markdown('<hr style="margin:.25rem 0 .6rem;border-color:#1e2d4a">', unsafe_allow_html=True)

# ── Render stored messages ────────────────────────────────────────────────────
def render_bubble(msg: dict):
    if msg["role"] == "user":
        st.markdown(
            f'<div class="msg-wrap-user"><div class="bubble-user">{msg["text"]}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        if msg.get("error"):
            st.markdown(
                f'<div class="msg-wrap-asst"><div class="bubble-error">⚠ {msg["error"]}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            src_html = ""
            if msg.get("sources"):
                items = "".join(f"· {s}<br>" for s in msg["sources"])
                src_html = f'<div class="msg-sources"><b>Sources</b>{items}</div>'
            meta = f'<div class="msg-meta">⏱ {msg["time_taken"]}s</div>' if msg.get("time_taken") else ""
            text = msg["text"].replace("\n", "<br>")
            st.markdown(
                f'<div class="msg-wrap-asst"><div class="bubble-asst">{text}{src_html}{meta}</div></div>',
                unsafe_allow_html=True,
            )

for msg in st.session_state.messages:
    render_bubble(msg)

# ── Handle pending query ──────────────────────────────────────────────────────
pending = st.session_state.get("pending_query")
if pending:
    st.session_state.pending_query = None
    st.session_state.stop_flag  = False
    st.session_state.is_loading = True

    add_user(pending)
    st.markdown(
        f'<div class="msg-wrap-user"><div class="bubble-user">{pending}</div></div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Thinking…"):
        t0     = time.time()
        result = ask(pending)
        elapsed = round(time.time() - t0, 2)

    st.session_state.is_loading = False

    if result.get("error"):
        add_assistant("", [], elapsed, error=result["error"])
        st.markdown(
            f'<div class="msg-wrap-asst"><div class="bubble-error">⚠ {result["error"]}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        answer  = result.get("answer", "")
        sources = result.get("sources", [])

        slot = st.empty()
        streamed = ""
        for char in answer:
            if st.session_state.stop_flag:
                break
            streamed += char
            slot.markdown(
                f'<div class="msg-wrap-asst">'
                f'<div class="bubble-asst">{streamed.replace(chr(10),"<br>")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            time.sleep(0.006)

        # Final bubble with sources + meta — same class, style never shifts
        src_html = ""
        if sources:
            items = "".join(f"· {s}<br>" for s in sources)
            src_html = f'<div class="msg-sources"><b>Sources</b>{items}</div>'
        meta = f'<div class="msg-meta">⏱ {elapsed}s</div>'
        slot.markdown(
            f'<div class="msg-wrap-asst">'
            f'<div class="bubble-asst">{streamed.replace(chr(10),"<br>")}{src_html}{meta}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        add_assistant(answer, sources, elapsed)

    st.session_state.stop_flag  = False
    st.session_state.is_loading = False

    # Autoscroll after response
    st.markdown(
        "<script>setTimeout(()=>window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'}),100);</script>",
        unsafe_allow_html=True,
    )

# ── Input ─────────────────────────────────────────────────────────────────────
st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)
st.markdown("---")

with st.form("chat_form", clear_on_submit=True):
    query     = st.text_input(
        "Message", placeholder="Ask anything… (Enter to send)",
        label_visibility="hidden", key="chat_input",
    )
    submitted = st.form_submit_button("send")

if submitted and query and query.strip():
    st.session_state.pending_query = query.strip()
    st.rerun()

st.caption("Stella may make mistakes — verify important information")