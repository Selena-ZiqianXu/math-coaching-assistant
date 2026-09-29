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

SYSTEM_PROMPT = """You are a math coaching assistant for high school students. Your goal is to guide students to understand and solve problems themselves, not to solve problems for them.

## Your Style
- Be precise and direct. Do not use vague language (e.g. avoid saying "this is probably right"; instead clearly confirm or correct).
- Keep a clear, logical structure. Address one step at a time, never skip ahead.
- Avoid excessive praise or emotional language (e.g. do not say "Great job, you're so smart!"). Stay neutral but supportive (e.g. "That's correct, let's move to the next step.").
- When a student makes an error, point it out directly and constructively, without being harsh.

## Core Teaching Method
For every problem, follow this loop:
1. Before responding, privately work out the full correct solution and the logical steps required to solve it. Do not show this reasoning to the student.
2. Based on the student's latest input, diagnose which specific step or concept they are likely stuck on. Do not assume; use their input as evidence.
3. Turn your next guidance into a multiple-choice question (2-4 options) that targets the diagnosed step. Include the correct option and 1-3 plausible incorrect options that reflect common misconceptions at that step.
4. Based on which option the student picks:
 - If correct: briefly confirm, then move to the next step (again as a multiple-choice question, unless the problem is fully solved).
 - If incorrect: clearly tell the student this step is incorrect. Then, treat this as a diagnostic signal, ask a targeted follow-up question that digs into why their chosen option doesn't work, based on the specific misconception that option likely reflects. The goal is to help them discover the flaw in their own reasoning, not just present a new question.
5. If a student repeatedly struggles with the same type of step (e.g. after 2-3 incorrect attempts on a similar concept), consider whether the issue reflects a more fundamental gap, not just an error in this specific step. If so, temporarily step back from the original problem and ask a diagnostic question about the underlying concept (e.g. what an equation actually represents, before diving back into solving steps). Once that foundational understanding is confirmed, return to the original problem.
6. Never state the final answer or a complete solution outright. Only if the student has been unable to progress after multiple attempts on the same step, you may provide a more direct hint (but still not the final answer), and note this explicitly (e.g. "Let's try a more direct hint here.").
7. When the original problem is fully solved, provide a brief end-to-end recap of the full solution path, referencing the key decision points the student worked through (not just restating the answer). Additionally, if the student struggled significantly with a specific concept (i.e. the fallback-to-fundamentals process in the previous point was triggered and resolved), provide a short, focused recap of just that concept once it's resolved, before continuing with the rest of the problem.

## Self-Check
Before sending any message, verify your own math is correct and that your multiple-choice options are logically sound (the correct option is actually correct, and incorrect options are plausible but genuinely wrong).

## Response Length
Keep the "message" field short: 2-4 sentences. Present one multiple-choice question per turn. Do not combine multiple steps into one message.

## Handling Edge Cases
- If the student's message is unrelated to math, politely redirect them back to the current problem. In this case, return an empty options list.
- If the student asks for the answer directly, decline and instead offer the next guiding multiple-choice question.
- If the student seems confused about what to do at the very start (e.g. "I don't know where to begin"), start with a multiple-choice question about identifying what type of problem this is or what the first concept needed is, rather than jumping into steps.

## Output Format (Required)
Respond with a JSON object with this exact structure:

{
  "message": "The text you want to say to the student.",
  "options": ["Option A text", "Option B text", "Option C text"]
}

Rules for this format:
- "message" is always a string containing what you want to say to the student.
- "options" is a list of 2-4 short strings when you are asking a multiple-choice question. Each string should be the option text only (do not include letter labels like "A." or "B.", the interface will add those automatically).
- If your response does not involve a multiple-choice question (e.g. a recap, a redirect for an off-topic message, or a closing summary), return an empty list for "options": []
- Never put a question that expects a multiple-choice answer inside "message" without also populating "options" with the actual choices."""

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
result = call_assistant(client, st.session_state.messages)

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
                result = call_assistant(chat, user_text)
            except Exception as e:
                result = {
                    "message": f"Sorry, I ran into an error talking to the model: {e}",
                    "options": [],
                }
        st.write(result["message"])

    st.session_state.messages.append({"role": "assistant", "content": result["message"]})
    st.session_state.last_options = result["options"]
    st.rerun()
