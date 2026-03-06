import app.frontend.stream as st 
import requests
import time

# --- CONFIGURATION ---
API_URL = "http://localhost:8000/chat"  
APP_TITLE = "Stella ⭐ - Space Assistant"

# --- PAGE CONFIG ---
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⭐",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING (ChatGPT Look & Feel) ---
st.markdown("""
<style>
    /* Main Container */
    .stApp {
        background-color: #f0f2f5;
    }
    /* Chat Message Containers */
    .stChatMessage {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    /* User Message Styling */
    .stChatMessage[data-testid="user"] {
        background-color: #e3f2fd;
    }
    /* Input Box Styling */
    .stChatInput {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 700px;
        z-index: 1000;
    }
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time())}"

# --- SIDEBAR ---
with st.sidebar:
    st.title("⭐ Stella")
    st.caption("Your Space Navigation Assistant")
    
    st.divider()
    
    # New Chat Button
    if st.button("✨ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = f"session_{int(time.time())}"
        st.rerun()
    
    st.divider()
    
    # Quick Prompts
    st.subheader("Try asking:")
    prompt_suggestions = [
        "What is SpaceWing?",
        "How do I book a flight?",
        "Safety protocols"
    ]
    for prompt in prompt_suggestions:
        if st.button(prompt, key=f"suggest_{prompt}"):
            st.session_state.active_prompt = prompt
    
    st.divider()
    
    # Chat History (Scrollable in Sidebar)
    st.subheader("Chat History")
    if not st.session_state.messages:
        st.caption("No messages yet.")
    else:
        # Display last 5 messages as a summary
        for i, msg in enumerate(st.session_state.messages[-5:]):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            preview = content[:20] + "..." if len(content) > 20 else content
            st.caption(f"**{role.capitalize()}**: {preview}")

# --- MAIN CHAT AREA ---

# Header
st.header("Space Wing FAQ Assistant")
st.caption("Powered by Local LLM (Llama 3.2) & RAG")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("📚 Sources"):
                for src in message["sources"]:
                    st.write(f"- {src}")

# --- INPUT HANDLING ---

# Check if a quick prompt was clicked
active_prompt = st.session_state.pop("active_prompt", None)

if prompt := st.chat_input("Ask about space travel...", key="chat_input"):
    # Use the active prompt if set, otherwise use the typed prompt
    final_prompt = active_prompt if active_prompt else prompt
    
    # 1. Display User Message
    st.chat_message("user").markdown(final_prompt)
    st.session_state.messages.append({"role": "user", "content": final_prompt})

    # 2. Call API
    with st.chat_message("assistant"):
        # Placeholder for streaming effect
        message_placeholder = st.empty()
        message_placeholder.markdown("🧠 Thinking...")
        
        try:
            payload = {
                "question": final_prompt,
                "session_id": st.session_state.session_id
            }
            
            # Show spinner while waiting
            with st.spinner("Consulting star charts..."):
                response = requests.post(API_URL, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "I couldn't process that.")
                sources = data.get("sources", [])
                intent = data.get("intent", "SAFE")
                
                # Update UI
                message_placeholder.markdown(answer)
                
                if sources:
                    with st.expander("📚 Sources"):
                        for src in sources:
                            st.write(f"- {src}")
                
                # Save to history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": answer,
                    "sources": sources
                })
            else:
                error_msg = f"⚠️ API Error: {response.status_code}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

        except requests.exceptions.Timeout:
            message_placeholder.error("⏱️ Request timed out. The stars are busy.")
        except requests.exceptions.ConnectionError:
            message_placeholder.error("🔌 Could not connect to backend. Is Docker running?")
        except Exception as e:
            message_placeholder.error(f"❌ Unexpected Error: {e}")

# --- FOOTER ---
st.markdown("---")
st.caption("SpaceWing FAQ System v1.0 | Powered by Docker & Ollama")