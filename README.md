# Math Coaching Assistant

An AI-powered math coaching assistant for high school students, built for the
AI Engineering take-home project. The assistant guides students to work
through problems themselves rather than handing them answers, using a
diagnose-then-guide loop and multiple-choice questions instead of open-ended
prompts.


## How to run it
**[Live Demo →](https://math-coaching-assistant-kwgnmavlutsvwojehvmawp.streamlit.app/)**
### Run it locally (optional)
If you'd rather run it yourself or look at the code in action:
1. Clone this repo and `cd` into it.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Get a free Gemini API key from [aistudio.google.com](https://aistudio.google.com)
   (click "Get API key" → "Create API key").
4. Copy the secrets template and add your key:
   ```
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Then open `.streamlit/secrets.toml` and paste your key in place of
   `your-api-key-here`.
5. Run the app:
   ```
   streamlit run app.py
   ```
6. Type a math problem into the chat box to start, or tell the assistant
   what topic you're stuck on.

## Approach and key decisions

**Diagnose before guiding, not just "give a hint."** Rather than reacting to
whatever the student says with a generic prompt, the system prompt requires
the model to first work out the correct solution privately, then diagnose
*which specific step* the student's input suggests they're stuck on, before
responding. This mirrors how a real tutor would approach a student who says
"I don't get it" — the first move is figuring out *what* they don't get, not
guessing.

**Multiple-choice over open-ended questions.** Early versions of this prompt
used open-ended guiding questions (e.g. "What do you think we should do
first?"). In practice, student answers to open-ended questions are hard to
diagnose reliably — a vague or off-target answer doesn't tell you much. Multiple
choice, where the wrong options are designed to reflect common
misconceptions at that step, makes the student's specific error much easier
to pinpoint, and turns every wrong answer into a diagnostic signal rather
than a dead end.

**Escalating to fundamentals when a student is stuck on the same type of
step repeatedly.** A student who keeps missing "how to isolate a variable"
across several attempts likely doesn't have an isolated procedural gap —
they may not understand what an equation actually represents. The prompt
instructs the model to recognize this pattern and temporarily step back to a
more foundational question before returning to the original problem, rather
than cycling through superficially different rephrasings of the same step.

**Explicitly restating the current state of the problem at each step.**
During testing, I noticed that once the conversation moved past 2-3 steps,
it became hard to follow what the equation actually looked like at that
point — the assistant would ask "what should we do to the right side?"
without ever stating what the equation currently was. I updated the prompt
to require the model to explicitly state the current form of the
equation/expression after each operation, before presenting the next
question, so a student isn't expected to track the arithmetic mentally on
their own on top of the reasoning.

**System prompt kept in a separate file, not embedded in the code.** The
full system prompt lives in `system_prompt.md` rather than as a large string
constant inside `app.py`. This keeps the prompt (which is the core design
artifact of this project) readable on its own, versionable independently of
application logic, and easy to iterate on without touching or risking
breaking the Python code.

**Structured JSON output, enforced by the API, not just requested in the
prompt.** The model is asked to return a JSON object with a `message` field
and an `options` field (empty when there's no multiple-choice question). This
is enforced via Gemini's `response_schema` / `response_mime_type` config,
not just described in the prompt text, so the app can reliably parse it into
a chat bubble and a set of clickable buttons rather than hoping the model's
formatting is consistent.

**Low temperature (0.4), not zero.** The assistant needs consistency (a
wrong answer shouldn't get a wildly different diagnosis if the student
rephrases slightly), but a small amount of variation keeps repeated
follow-up questions from sounding robotic and identical every time.

**Self-check before sending.** The prompt asks the model to verify its own
math and confirm its multiple-choice options are logically sound (correct
option genuinely correct, distractors genuinely wrong) before each response.
This doesn't guarantee correctness, but reduces the risk of the model
guiding a student toward the wrong step.

## What to improve with more time

- **Verify math correctness independently of the LLM.** Right now, the
  assistant's math correctness depends entirely on the model's own reasoning
  and self-check. For a production version, I'd add a lightweight symbolic
  math check (e.g. with `sympy`) to verify the model's stated correct answer
  and flag disagreements, rather than trusting the LLM's self-report.
- **Persist sessions across reloads.** Conversation state currently lives in
  Streamlit's `session_state`, so it resets if the browser tab is closed. A
  real product would persist this (e.g. to a database) so a student could
  resume a problem later.
- **Track which misconceptions a student hits repeatedly across sessions**,
  to give a teacher or the student themselves visibility into recurring
  gaps, not just the current problem.
- **Guardrails for off-topic or inappropriate input** beyond the current
  simple redirect — e.g. detecting attempts to get the assistant to just
  solve the problem outright through rephrased requests.
- **Support image input** (e.g. a photo of a handwritten problem), using
  Gemini's multimodal capabilities, since students often have a problem on
  paper rather than typed out.

## A note on the model

The spec suggested Gemini 1.5 Flash/Pro; those have since been superseded.
This project uses `gemini-3-flash-preview`, which is confirmed by Google's
own documentation to have a free tier, in the same spirit as the original
recommendation (a free, capable Gemini model).

## Example conversations

See `example_conversations/` for transcripts demonstrating the diagnose →
multiple-choice → recap loop, including a case where the student struggles
repeatedly and the assistant steps back to a foundational concept.

