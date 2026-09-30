"""
Student Coaching Assistant
A math coaching assistant that guides high school students to solve problems
themselves through diagnostic multiple-choice questions, rather than just
giving them answers.
"""

import json
import streamlit as st
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "gemini-3-flash-preview"  # Free-tier text model (see README for notes)
TEMPERATURE = 0.4  # Low-ish temperature: we want consistent, reliable reasoning,
                    # not creative variation, but a little flexibility in phrasing.

with open("system_prompt.md", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

WELCOME_MESSAGE = (
    "Hi! I'm here to help you work through a math problem. "
    "Type in a problem you're working on, or tell me what topic you're stuck on, "
    "and we'll go through it step by step."
)

# JSON schema handed to the model via response_schema, so the API itself
# enforces valid, parseable JSON output rather than relying on the prompt
# instructions alone (which models can occasionally ignore).
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "message": {"type": "STRING"},
        "options": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
    },
    "required": ["message", "options"],
}

# ---------------------------------------------------------------------------
# Gemini setup
# ---------------------------------------------------------------------------


def get_client():
    """Configure and return a fresh Gemini API client using the key from secrets."""
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error(
            "No Gemini API key found. Add GEMINI_API_KEY to your "
            ".streamlit/secrets.toml file (see README)."
        )
        st.stop()
    return genai.Client(api_key=api_key)
  

def build_contents(messages):
    """Convert our message list into the Content format the API expects."""
    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    return contents


def call_assistant(client, messages):
    """
    Send the full conversation to Gemini (stateless call each time) and
    parse the JSON response.
    """
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=TEMPERATURE,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=build_contents(messages),
        config=config,
    )
    raw_text = (response.text or "").strip()
    try:
        parsed = json.loads(raw_text)
        return {"message": parsed.get("message", ""), "options": parsed.get("options", []) or []}
    except (json.JSONDecodeError, AttributeError):
        return {"message": raw_text or "Sorry, something went wrong on my end.", "options": []}


# ---------------------------------------------------------------------------
# Streamlit app
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Student Coaching Assistant", page_icon="📐")
st.title("📐 Student Coaching Assistant")

st.markdown(
    """
    <style>
    div.stButton > button {
        white-space: normal;
        height: auto;
        word-wrap: break-word;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# session_state["messages"] stores the full conversation for display purposes.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Holds text that should be sent to the model on this run, whether it came
# from typing or from clicking an option button.
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

if "last_options" not in st.session_state:
    st.session_state.last_options = []

client = get_client()

# --- Sidebar: reset button ---
with st.sidebar:
    st.markdown("### Session")
    if st.button("🔄 Start a new problem"):
        for key in ("messages", "pending_input", "last_options"):
            st.session_state.pop(key, None)
        st.rerun()

# --- Render existing conversation ---
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.write(WELCOME_MESSAGE)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- Render option buttons for the latest assistant turn, if any ---
if st.session_state.last_options and st.session_state.messages:
    st.write("")  # small spacing
    cols = st.columns(len(st.session_state.last_options))
    for i, option_text in enumerate(st.session_state.last_options):
        label = f"{chr(65 + i)}. {option_text}"
        if cols[i].button(label, key=f"option_{len(st.session_state.messages)}_{i}"):
            st.session_state.pending_input = option_text
            st.session_state.last_options = []  # clear so buttons don't linger

# --- Free-text input, always available alongside the option buttons ---
typed = st.chat_input("Type your answer, a question, or a new problem...")
if typed:
    st.session_state.pending_input = typed
    st.session_state.last_options = []

# --- If there's a pending input (from typing or a button click), send it ---
if st.session_state.pending_input:
    user_text = st.session_state.pending_input
    st.session_state.pending_input = None

    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = call_assistant(client, st.session_state.messages)
            except Exception as e:
                result = {
                    "message": f"Sorry, I ran into an error talking to the model: {e}",
                    "options": [],
                }
        st.write(result["message"])

    st.session_state.messages.append({"role": "assistant", "content": result["message"]})
    st.session_state.last_options = result["options"]
    st.rerun()
