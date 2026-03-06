import time
import json
import streamlit as st
from api import ask, health_check
from store import init_store, add_user, add_assistant, clear_history

st.set_page_config(
    page_title="Stella", page_icon="✦",
    layout="centered", initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',system-ui,sans-serif!important}

#MainMenu,footer,header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebarNavLink"],
[data-testid="stSidebarNav"]{display:none!important}

.stApp{
    background:
        radial-gradient(1px 1px at  8% 15%,rgba(255,255,255,.60) 0%,transparent 100%),
        radial-gradient(1px 1px at 20% 60%,rgba(255,255,255,.45) 0%,transparent 100%),
        radial-gradient(1px 1px at 35%  8%,rgba(255,255,255,.55) 0%,transparent 100%),
        radial-gradient(1px 1px at 50% 75%,rgba(255,255,255,.40) 0%,transparent 100%),
        radial-gradient(1px 1px at 65% 30%,rgba(255,255,255,.55) 0%,transparent 100%),
        radial-gradient(1px 1px at 80% 85%,rgba(255,255,255,.42) 0%,transparent 100%),
        radial-gradient(1px 1px at 92% 12%,rgba(255,255,255,.50) 0%,transparent 100%),
        radial-gradient(1px 1px at 55% 45%,rgba(255,255,255,.32) 0%,transparent 100%),
        radial-gradient(2px 2px at  4%  4%,rgba(79,142,247,.35)  0%,transparent 100%),
        radial-gradient(2px 2px at 96% 96%,rgba(139,92,246,.28)  0%,transparent 100%),
        radial-gradient(ellipse 70% 40% at 50% 0%,rgba(79,142,247,.08) 0%,transparent 100%),
        linear-gradient(180deg,#050810 0%,#07091a 100%)!important;
    background-attachment:fixed!important;
}

.block-container{max-width:660px!important;padding:0.7rem 1.2rem 0.4rem!important}

/* ── Bubbles ── */
.msg-wrap-user{display:flex;justify-content:flex-end;margin:5px 0}
.msg-wrap-asst{display:flex;justify-content:flex-start;margin:5px 0}
.bubble-user{
    background:rgba(79,142,247,.16);border:1px solid rgba(79,142,247,.28);
    border-radius:10px;border-bottom-right-radius:3px;
    padding:9px 14px;max-width:82%;font-size:.875rem;
    line-height:1.65;color:#e2e8f0;white-space:pre-wrap;word-break:break-word;
}
.bubble-asst{
    background:#0f1624;border:1px solid #1e2d4a;
    border-radius:10px;border-bottom-left-radius:3px;
    padding:9px 14px;max-width:82%;font-size:.875rem;
    line-height:1.65;color:#e2e8f0;white-space:pre-wrap;word-break:break-word;
}
.bubble-error{
    background:rgba(255,255,255,.03);border:1px solid #1e2d4a;
    border-radius:10px;border-bottom-left-radius:3px;
    padding:9px 14px;max-width:82%;font-size:.82rem;color:#94a3b8;
}
.msg-sources{
    margin-top:7px;padding-top:7px;border-top:1px solid #1e2d4a;
    font-size:.70rem;color:#445069;
}
.msg-sources b{font-weight:600;text-transform:uppercase;letter-spacing:.04em;display:block;margin-bottom:2px}
.msg-meta{font-size:.68rem;color:#445069;margin-top:4px}

/* ── Form / input ── */
[data-testid="stForm"]{border:none!important;padding:0!important}
[data-testid="stFormSubmitButton"]{display:none!important}
.stTextInput input{
    background:#0f1624!important;border:1px solid #1e2d4a!important;
    border-radius:10px!important;color:#e2e8f0!important;
    font-family:'Inter',sans-serif!important;font-size:.875rem!important;
    padding:10px 14px!important;height:42px!important;
}
.stTextInput input:focus{border-color:#2e4470!important;box-shadow:none!important}
.stTextInput input::placeholder{color:#445069!important}
[data-testid="stTextInput"]{margin-bottom:0!important}

/* ── Logo button ── */
.logo-btn button{
    background:transparent!important;border:none!important;
    box-shadow:none!important;padding:0!important;
    min-height:unset!important;height:auto!important;width:auto!important;
    font-size:1.05rem!important;font-weight:700!important;
    background:linear-gradient(90deg,#4f8ef7,#8b5cf6)!important;
    -webkit-background-clip:text!important;
    -webkit-text-fill-color:transparent!important;
    background-clip:text!important;cursor:pointer!important;
}
.logo-btn button:hover{opacity:.72!important}
.logo-btn button:focus{outline:none!important;box-shadow:none!important}

/* ── Suggestion chips ── */
.sug-btn button{
    background:rgba(255,255,255,.03)!important;border:1px solid #1e2d4a!important;
    color:#94a3b8!important;border-radius:9px!important;
    font-size:.78rem!important;padding:7px 11px!important;
    text-align:left!important;transition:all .15s!important;width:100%!important;
}
.sug-btn button:hover{background:#192033!important;border-color:#2e4470!important;color:#e2e8f0!important}

/* ── Scroll FAB ── */
.fab-scroll{position:fixed;bottom:26px;right:20px;z-index:999;}
.fab-scroll a{
    display:flex;align-items:center;justify-content:center;
    width:34px;height:34px;border-radius:50%;
    background:rgba(15,22,36,.95);border:1px solid #1e2d4a;
    color:#94a3b8;font-size:14px;text-decoration:none;
    box-shadow:0 2px 12px rgba(0,0,0,.4);
    transition:background .15s,border-color .15s,color .15s;
}
.fab-scroll a:hover{background:#192033;border-color:#4f8ef7;color:#4f8ef7;}

/* ── Sidebar ── */
[data-testid="stSidebar"]{background:rgba(8,12,26,.98)!important;border-right:1px solid #1e2d4a!important}
.danger-btn button{
    background:transparent!important;border:1px solid #1e2d4a!important;
    color:#445069!important;border-radius:8px!important;
    font-size:.75rem!important;transition:all .15s!important;width:100%!important;
}
.danger-btn button:hover{border-color:#f87171!important;color:#f87171!important}

hr{border-color:#1e2d4a!important;margin:.3rem 0!important}
.stCaption{color:#445069!important}
.stSpinner > div{border-top-color:#4f8ef7!important}
</style>
""", unsafe_allow_html=True)

# ── Init ──────────────────────────────────────────────────────────────────────
init_store()
if "view"       not in st.session_state: st.session_state.view       = "home"
if "stop_flag"  not in st.session_state: st.session_state.stop_flag  = False
if "is_loading" not in st.session_state: st.session_state.is_loading = False

# Switch to chat if there are already messages
if st.session_state.messages and st.session_state.view == "home":
    st.session_state.view = "chat"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ✦ Stella")
    st.caption("RAG Document Assistant")
    st.divider()

    ok = health_check()
    st.caption("🟢 API Online" if ok else "🔴 API Offline")
    st.divider()

    n = len(st.session_state.messages)
    st.caption(f"**{n}** message{'s' if n != 1 else ''}")

    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if user_msgs:
        st.caption("**Questions asked**")
        for i, m in enumerate(user_msgs[-8:], 1):
            t = m["text"]
            st.caption(f"{i}. {t[:40]}{'…' if len(t)>40 else ''}")
        st.divider()

        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("🗑 Clear & go home", use_container_width=True):
            clear_history()
            st.session_state.view = "home"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.download_button(
            "⬇ Export history", use_container_width=True,
            data=json.dumps(st.session_state.messages, indent=2),
            file_name="stella_history.json", mime="application/json",
        )

# ══════════════════════════════════════════════════════════════════════════════
# HOME VIEW
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.view == "home":

    st.markdown("""
    <div style="text-align:center;padding:1.3rem 0 .5rem">
        <div style="font-size:2rem;font-weight:700;letter-spacing:-.02em;
            background:linear-gradient(130deg,#fff 40%,#4f8ef7 70%,#8b5cf6 100%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;margin-bottom:4px">✦ Stella</div>
        <div style="font-size:.76rem;color:#4f8ef7;font-weight:500;margin-bottom:5px">
            Intelligent Document Intelligence · Powered by RAG</div>
        <div style="font-size:.75rem;color:#94a3b8;line-height:1.6;max-width:420px;margin:0 auto">
            Fast, grounded answers from your internal knowledge base.
            Every response cites its source.</div>
    </div>
    <div style="display:flex;gap:8px;margin:.5rem 0 .7rem">
        <div style="flex:1;background:rgba(255,255,255,.03);border:1px solid #1e2d4a;border-radius:9px;padding:9px 11px">
            <div style="font-size:12px;color:#4f8ef7;margin-bottom:3px">◉</div>
            <div style="font-size:11px;font-weight:600;color:#e2e8f0;margin-bottom:2px">Mission</div>
            <div style="font-size:11px;color:#94a3b8;line-height:1.45">Make enterprise knowledge instantly accessible to every team member.</div>
        </div>
        <div style="flex:1;background:rgba(255,255,255,.03);border:1px solid #1e2d4a;border-radius:9px;padding:9px 11px">
            <div style="font-size:12px;color:#4f8ef7;margin-bottom:3px">◈</div>
            <div style="font-size:11px;font-weight:600;color:#e2e8f0;margin-bottom:2px">What Stella does</div>
            <div style="font-size:11px;color:#94a3b8;line-height:1.45">Searches and synthesises answers from your document library.</div>
        </div>
        <div style="flex:1;background:rgba(255,255,255,.03);border:1px solid #1e2d4a;border-radius:9px;padding:9px 11px">
            <div style="font-size:12px;color:#4f8ef7;margin-bottom:3px">◆</div>
            <div style="font-size:11px;font-weight:600;color:#e2e8f0;margin-bottom:2px">Cited sources</div>
            <div style="font-size:11px;color:#94a3b8;line-height:1.45">Every answer links back to its source so you can verify it.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    with st.form("home_form", clear_on_submit=True):
        home_q = st.text_input(
            "Query", placeholder="Ask anything… (Enter to send)",
            label_visibility="hidden", key="home_input",
        )
        home_submitted = st.form_submit_button("send")

    st.caption("Try asking")
    SUGGS = [
        "What documents can you search?",
        "Summarize the key topics",
        "Find specific information",
        "What are the main insights?",
    ]
    c1, c2 = st.columns(2)
    for i, q in enumerate(SUGGS):
        with (c1 if i % 2 == 0 else c2):
            st.markdown('<div class="sug-btn">', unsafe_allow_html=True)
            if st.button(q, key=f"sug_{i}", use_container_width=True):
                st.session_state.pending_query = q
                st.session_state.view = "chat"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    if home_submitted and home_q and home_q.strip():
        st.session_state.pending_query = home_q.strip()
        st.session_state.view = "chat"
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# CHAT VIEW
# ══════════════════════════════════════════════════════════════════════════════
else:
    # Scroll FAB
    st.markdown("""
    <div class="fab-scroll">
      <a id="sfab" href="#chat-bottom" title="Latest">↓</a>
    </div>
    <script>
    document.getElementById('sfab').addEventListener('click',function(e){
        e.preventDefault();
        var el=document.getElementById('chat-bottom');
        if(el)el.scrollIntoView({behavior:'smooth'});
    });
    </script>
    """, unsafe_allow_html=True)

    # Topbar — logo returns to home
    logo_col, label_col = st.columns([2, 10])
    with logo_col:
        st.markdown('<div class="logo-btn">', unsafe_allow_html=True)
        if st.button("✦ Stella", key="logo_home"):
            st.session_state.view = "home"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with label_col:
        st.markdown(
            '<p style="font-size:.68rem;color:#445069;margin:7px 0 0">RAG Document Intelligence</p>',
            unsafe_allow_html=True,
        )
    st.markdown('<hr style="margin:.2rem 0 .55rem;border-color:#1e2d4a">', unsafe_allow_html=True)

    # ── Render stored messages ────────────────────────────────────────────────
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

    # ── Handle pending query ──────────────────────────────────────────────────
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

            # Typewriter — single placeholder, style never changes
            slot     = st.empty()
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

            # Final — same bubble, append sources + meta
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

    # Bottom anchor for scroll FAB
    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)

    # ── Input ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.form("chat_form", clear_on_submit=True):
        chat_q    = st.text_input(
            "Message", placeholder="Ask anything… (Enter to send)",
            label_visibility="hidden", key="chat_input",
        )
        submitted = st.form_submit_button("send")

    if submitted and chat_q and chat_q.strip():
        st.session_state.pending_query = chat_q.strip()
        st.rerun()

    st.caption("Stella may make mistakes — verify important information")