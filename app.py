import sqlite3
import asyncio
import os
import streamlit as st
from dotenv import load_dotenv
from virgofash import search
from google import genai

# Load environment variables from .env file if present
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Enterprise AI Research Assistant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Professional UI Styling ---
st.markdown("""
    <style>
        .main { background-color: #0e1117; color: #ffffff; }
        .stChatMessage { border-radius: 12px; padding: 15px; margin-bottom: 12px; border: 1px solid #262730; }
        h1 { font-family: 'Inter', sans-serif; font-weight: 700; color: #fafafa; }
    </style>
""", unsafe_allow_html=True)

st.title("🧠 Enterprise AI Research Assistant")
st.caption("Real-Time Web Augmented Generation Powered by Virgofash, Google Gemini, and Local SQLite Storage.")

# --- Database Setup (SQLite) ---
def init_db():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            sources TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Load chat history from SQLite database
def load_chat_history():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT role, content, sources FROM messages")
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "role": row[0],
            "content": row[1],
            "sources": row[2]
        })
    return history

def save_message_to_db(role, content, sources=""):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (role, content, sources) VALUES (?, ?, ?)", 
        (role, content, sources)
    )
    conn.commit()
    conn.close()

def clear_db():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# --- Sidebar Configuration & API Key Initialization ---
st.sidebar.header("Configuration Panel")

# 1. Check environment variables (.env file)
api_key = os.getenv("GEMINI_API_KEY")

# 2. Check Streamlit Secrets if .env is missing
if not api_key:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

# 3. Fallback to Sidebar Input if not found anywhere else
if not api_key:
    api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")

if api_key:
    client = genai.Client(api_key=api_key)
    st.sidebar.success("System Authenticated Successfully", icon="🟢")
else:
    st.sidebar.warning("Please provide your Gemini API Key via .env or sidebar to activate the agent.")

st.sidebar.divider()
if st.sidebar.button("Clear Conversation History", type="primary"):
    clear_db()
    st.session_state.messages = []
    st.rerun()

# --- Load History into Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

# --- Render Existing Chat History on UI ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources") and message["sources"] != "None" and message["sources"] != "":
            with st.expander("🔍 Verified Reference Sources"):
                st.write(message["sources"])

# --- Chat Input & Execution Logic ---
if prompt := st.chat_input("Enter your complex query or research topic..."):
    if not api_key:
        st.error("Authentication required. Please configure your Gemini API Key.")
    else:
        # 1. Save and display user query
        st.session_state.messages.append({"role": "user", "content": prompt, "sources": ""})
        save_message_to_db("user", prompt)
        
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Process Assistant Response
        with st.chat_message("assistant"):
            with st.spinner("Executing real-time web retrieval and synthesizing intelligence..."):
                
                # A. Fetch search data asynchronously via Virgofash
                async def fetch_search():
                    return await search(prompt)
                
                search_results = asyncio.run(fetch_search())

                # B. Maintain short-term context window (last 4 messages to save tokens)
                context_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages[-4:]])

                # C. Optimized, token-efficient prompt for Gemini
                full_prompt = f"""
                You are an advanced, professional AI Research Assistant. Provide an exhaustive, detailed, and deeply structured report addressing the user query. Use formal formatting, bullet points, technical breakdowns, and clear headings.
                
                Conversation Context:
                {context_history}
                
                Current Query: {prompt}
                
                Retrieved Web Intelligence:
                {search_results}
                """

                try:
                    # Using gemini-2.5-flash for maximum speed and minimal credit consumption
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=full_prompt,
                    )
                    ai_response = response.text
                except Exception as e:
                    ai_response = f"An error occurred during synthesis: {e}"

                # D. Render output on UI (Without images)
                st.markdown(ai_response)
                
                with st.expander("🔍 Verified Reference Sources"):
                    st.write(search_results)

                # 3. Persist assistant output and sources into SQLite database
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": ai_response,
                    "sources": str(search_results)
                })
                save_message_to_db("assistant", ai_response, str(search_results))