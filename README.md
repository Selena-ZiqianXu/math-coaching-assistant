# Math Coaching Assistant

An AI-powered math coaching assistant for high school students, built for the
AI Engineering take-home project. The assistant guides students to work
through problems themselves rather than handing them answers, using a
diagnose-then-guide loop and multiple-choice questions instead of open-ended
prompts.


## How to run it
**[Live Demo →](https://math-coaching-assistant-kwgnmavlutsvwojehvmawp.streamlit.app/)**
1. Type a math problem into the chat box (e.g. "Solve for x: 2x + 5 = 13"),
   or describe what topic you're stuck on.
2. The assistant will diagnose where you're likely stuck and ask a
   multiple-choice question. Click an option, or type a different answer or
   question if you'd rather respond in your own words.
3. Once you've fully solved the problem, the assistant gives a short recap
   of how you got there.
4. Use the "Start a new problem" button in the sidebar to reset and begin a
   different problem.
   
### Run it locally (optional)
If you'd rather run it yourself or look at the code in action:
1. Get a free Gemini API key from [aistudio.google.com](https://aistudio.google.com) (click "Get API key" → "Create API key").
2. Clone this repo and `cd` into it.
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

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


## Approach and key decisions

**Diagnose before guiding, instead of just giving a hint.**  
The assistant is instructed to first work out the correct solution privately, then use the student’s latest response to figure out what specific step they are struggling with. If a student says “I don’t get it,” the goal is not to immediately give another hint, but to first identify what exactly is causing the confusion.

**Use multiple-choice questions instead of open-ended ones.**  
Earlier versions used questions like “What do you think we should do first?” But open-ended answers were often too vague to tell what the student actually misunderstood. From a behavioral science perspective, they can also add cognitive load: the student has to solve the math problem while also deciding how to phrase a response. Multiple-choice questions reduce that response friction by making the next action clearer and easier, while still requiring the student to make an active choice. The wrong options can also be designed around common misconceptions, turning each response into a useful diagnostic signal.

**Step back to fundamentals when the same difficulty keeps appearing.**  
If a student repeatedly struggles with the same type of step, such as isolating a variable, the problem may be more basic than that one procedure. In that case, the assistant is told to briefly return to a more fundamental idea, such as what an equation represents, before coming back to the original problem.

**Restate the current form of the problem at each step.**  
During testing, I found that after a few steps, it became easy to lose track of what the equation currently looked like. The assistant might ask what to do next without showing the updated equation. To avoid this, the prompt requires it to state the current equation or expression after each operation before asking the next question.

**Keep the system prompt in a separate file.**  
The full prompt is stored in `system_prompt.md` instead of directly inside `app.py`. This makes it easier to read and edit the prompt without mixing it with the application code.

**Use structured JSON output enforced by the API.**  
The model returns a JSON object with a `message` field and an `options` field. When there is no multiple-choice question, `options` is empty. This structure is enforced through Gemini’s `response_schema` and `response_mime_type`, so the app can reliably separate the chat response from the answer buttons.

**Use a low temperature, but not zero.**  
I set the temperature to 0.4 because the assistant should behave consistently, especially when diagnosing similar mistakes. At the same time, a small amount of variation helps keep repeated follow-up questions from sounding exactly the same.

**Ask the model to self-check before responding.**  
Before sending each response, the prompt tells the model to check its math and make sure the multiple-choice options are valid: the correct answer should actually be correct, and the distractors should be clearly wrong. This cannot eliminate mistakes completely, but it helps reduce them.

## What to improve with more time

- **Verify math correctness independently of the LLM.**  
  Right now, the assistant relies on the model’s own reasoning and self-check for math correctness. In a production version, I would add a lightweight symbolic math check, such as `sympy`, to verify key calculations and flag cases where the model’s answer does not match the checker.

- **Persist sessions across reloads.**  
  Conversation history currently lives in Streamlit’s `session_state`, so it is lost when the browser session ends. A production version could store sessions in a database so students can return to a problem later and continue where they left off.

- **Track recurring misconceptions across sessions.**  
  The current version only responds to mistakes within the active conversation. A future version could keep track of concepts a student repeatedly struggles with and surface those patterns to the student or a teacher.

- **Add stronger guardrails for off-topic or inappropriate input.**  
  The current prompt includes a basic redirect, but a production version could handle cases such as repeated attempts to get the assistant to give away the full solution instead of working through the problem step by step.

- **Support image input.**  
  Students often have problems on paper rather than typed out, so a future version could use Gemini’s multimodal capabilities to accept photos of handwritten or printed math problems.

- **Support LaTeX input and rendering.**  
  Adding LaTeX support would make it easier for students to enter and read more complex mathematical expressions, such as fractions, exponents, square roots, and matrices, without relying on plain-text notation.

## A note on the model

The spec suggested Gemini 1.5 Flash/Pro; those have since been superseded.
This project uses `gemini-3-flash-preview`, which is confirmed by Google's
own documentation to have a free tier, in the same spirit as the original
recommendation (a free, capable Gemini model).

## Example conversations

See `example_conversations/` for transcripts demonstrating the diagnose →
multiple-choice → recap loop.

