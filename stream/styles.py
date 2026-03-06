import streamlit as st


def inject(page: str = "home"):
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{{font-family:'Inter',system-ui,sans-serif!important}}

#MainMenu,footer,header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebarNavLink"],
[data-testid="stSidebarNav"]{{display:none!important}}

.stApp{{
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
}}

.block-container{{max-width:660px!important;padding:0.8rem 1.2rem 0.5rem!important}}

/* ── Bubbles (consistent across pages) ── */
.msg-wrap-user{{display:flex;justify-content:flex-end;margin:5px 0}}
.msg-wrap-asst{{display:flex;justify-content:flex-start;margin:5px 0}}

.bubble-user{{
    background:rgba(79,142,247,.16);
    border:1px solid rgba(79,142,247,.28);
    border-radius:10px;border-bottom-right-radius:3px;
    padding:9px 14px;max-width:82%;
    font-size:.875rem;line-height:1.65;
    color:#e2e8f0;white-space:pre-wrap;word-break:break-word;
}}
.bubble-asst{{
    background:#0f1624;border:1px solid #1e2d4a;
    border-radius:10px;border-bottom-left-radius:3px;
    padding:9px 14px;max-width:82%;
    font-size:.875rem;line-height:1.65;
    color:#e2e8f0;white-space:pre-wrap;word-break:break-word;
}}
.bubble-error{{
    background:rgba(255,255,255,.03);border:1px solid #1e2d4a;
    border-radius:10px;border-bottom-left-radius:3px;
    padding:9px 14px;max-width:82%;
    font-size:.82rem;color:#94a3b8;
}}
.msg-sources{{
    margin-top:7px;padding-top:7px;
    border-top:1px solid #1e2d4a;
    font-size:.70rem;color:#445069;
}}
.msg-sources b{{
    font-weight:600;text-transform:uppercase;
    letter-spacing:.04em;display:block;margin-bottom:2px;
}}
.msg-meta{{font-size:.68rem;color:#445069;margin-top:4px}}

/* ── Input form ── */
[data-testid="stForm"]{{border:none!important;padding:0!important}}

.stTextInput input{{
    background:#0f1624!important;border:1px solid #1e2d4a!important;
    border-radius:10px!important;color:#e2e8f0!important;
    font-family:'Inter',sans-serif!important;font-size:.875rem!important;
    padding:10px 14px!important;height:42px!important;
}}
.stTextInput input:focus{{border-color:#2e4470!important;box-shadow:none!important}}
.stTextInput input::placeholder{{color:#445069!important}}
[data-testid="stTextInput"]{{margin-bottom:0!important}}

/* ── Submit button ── */
[data-testid="stFormSubmitButton"] button{{
    background:#4f8ef7!important;border:none!important;
    color:#fff!important;border-radius:10px!important;
    font-size:1.05rem!important;font-weight:700!important;
    height:42px!important;width:100%!important;
    padding:0!important;transition:opacity .15s!important;
    margin-top:0!important;
}}
[data-testid="stFormSubmitButton"] button:hover{{opacity:.82!important}}

/* ── Stop button ── */
.stop-wrap [data-testid="stButton"] button,
.stop-wrap .stButton button{{
    background:rgba(248,113,113,.1)!important;
    border:1px solid rgba(248,113,113,.3)!important;
    color:#f87171!important;border-radius:10px!important;
    height:38px!important;font-size:.8rem!important;
    padding:0 14px!important;transition:all .15s!important;
    width:auto!important;
}}
.stop-wrap .stButton button:hover{{background:rgba(248,113,113,.2)!important}}

/* ── Suggestion chips (home page) ── */
{''.join([
".sug-btn .stButton button{background:rgba(255,255,255,.03)!important;border:1px solid #1e2d4a!important;",
"color:#94a3b8!important;border-radius:9px!important;font-size:.78rem!important;",
"padding:7px 11px!important;text-align:left!important;transition:all .15s!important;width:100%!important}",
".sug-btn .stButton button:hover{background:#192033!important;border-color:#2e4470!important;color:#e2e8f0!important}",
]) if page == 'home' else ''}

/* ── Clear / export (sidebar) ── */
.danger-btn .stButton button{{
    background:transparent!important;border:1px solid #1e2d4a!important;
    color:#445069!important;border-radius:8px!important;
    font-size:.75rem!important;padding:5px 10px!important;
    transition:all .15s!important;width:100%!important;
}}
.danger-btn .stButton button:hover{{border-color:#f87171!important;color:#f87171!important}}

hr{{border-color:#1e2d4a!important;margin:.35rem 0!important}}
.stCaption{{color:#445069!important}}
.stSpinner > div{{border-top-color:#4f8ef7!important}}

/* ── Sidebar ── */
[data-testid="stSidebar"]{{
    background:rgba(8,12,26,.98)!important;
    border-right:1px solid #1e2d4a!important;
}}
</style>
""", unsafe_allow_html=True)