# Prompts Used to Build KOHLER CONCORD

> This file contains the prompts used during development of the KOHLER CONCORD project.

 1) You are a senior AI engineer and technical lead. Build a complete, runnable prototype for the KOHLER-MITWPU AI Research Lab case study, Track 3: "Kohler Unified Enterprise AI Agent."

## Track requirements
Build an enterprise-grade conversational AI agent that answers complex internal and external queries across HR policy, financial guidelines, customer support, privacy policies, and legal/compliance documentation. It must reason across multiple turns and format responses on demand per user instruction (JSON schema, downloadable Excel summaries, XML, ready-to-send draft emails).

Evaluation weights: Approach & Innovation 45%, Technical Execution 25%, UX & Feasibility 20%, Business & Sustainability Impact 10% (KOHLER values design excellence, water conservation, operational efficiency).

## Critical constraint: differentiation
Many students will build a basic RAG chatbot over PDFs with a "format as JSON" option. Do NOT build that. Build "KOHLER CONCORD": an agent whose core innovation is a TRUST LAYER around the LLM. It must include these five features:

1. Role- and permission-aware retrieval. Personas (Employee, HR Manager, Finance Analyst, Customer, Legal Counsel) each see only the documents they are entitled to. The same question gets a different, correctly scoped answer per persona, and the agent explains when it cannot share something instead of leaking it.

2. Policy Conflict Radar. When retrieved sources across domains contradict or interact (e.g., HR expense policy vs finance approval limits vs legal retention rules), the agent detects and surfaces the conflict, names the clauses involved, and recommends which takes precedence.

3. Self-verifying answer pipeline (multi-agent): Router -> Domain Specialist(s) -> Verifier/Critic -> Formatter. The Verifier checks every claim against retrieved text, attaches clause-level citations, assigns a confidence score, and forces the agent to abstain or ask a clarifying question when evidence is weak. No uncited claims.

4. Output Contracts. The user describes the desired format in natural language; the agent compiles it into a schema, generates the output, VALIDATES it (jsonschema for JSON, well-formedness for XML, real .xlsx download via openpyxl, draft emails with subject/tone/recipient fields), and auto-repairs on validation failure. Show the validation status in the UI.

5. Built-in evaluation and red-team dashboard. Include a golden question set (30+ items) plus adversarial tests (prompt injection, cross-role data leakage attempts, PII extraction, unsupported-claim traps). Show pass/fail, faithfulness, citation accuracy, and leakage-rate metrics in the app.

Sustainability tie-in (Kohler alignment): route simple queries to a smaller/cheaper model, cache repeated answers, and display a live "tokens and estimated energy saved" counter. Frame it as operational efficiency and responsible AI.

## Data
Do not assume documents are provided. Generate a realistic SYNTHETIC Kohler-style knowledge base (clearly labeled synthetic): HR policy (leave, remote work, expenses), finance guidelines (approval limits, procurement), customer support (warranty, returns, smart-fixture troubleshooting), privacy policy (data retention, consent), and legal/compliance (contracts, environmental compliance). Include 2-3 intentional cross-document conflicts so the Conflict Radar has something to find. Store as markdown/text with metadata (domain, access roles, clause IDs).

## Tech stack
- Python 3.11+, Streamlit UI (fast to build, good UX), chat interface with persona selector, citations panel, conflict alerts, confidence badges, format selector plus free-text format instruction, download buttons.
- Local vector store (ChromaDB or FAISS), hybrid retrieval (semantic + keyword), metadata filtering for permissions.
- LLM provider abstracted behind one interface, configured via environment variables (API key and model name from .env; never hardcode keys). Provide .env.example.
- jsonschema, openpyxl, lxml for the output layer.

## Repository deliverables (build all)
- /src (clean, modular, typed, commented), /data (synthetic KB), /eval (golden and adversarial sets plus runner), app entry point
- README.md with setup and run instructions (one-command run script), architecture diagram (Mermaid), and design decisions
- PROMPTS.md documenting every system prompt, agent instruction, and workflow used, structured so it converts cleanly to the required "Prompts Documentation" PDF
- DECK_OUTLINE.md: a 4-slide outline (1. Problem and insight, 2. Architecture and trust layer, 3. Tech stack and innovation, 4. Results from eval dashboard and business impact)
- DEMO_SCRIPT.md: a 2-3 minute video script showing: persona-scoped answers, conflict detection, a validated Excel/JSON output, an injection attack being blocked, and the eval dashboard
- EMAIL_TEMPLATE.md with subject "PRN_Name_Title of Project"

## How to work
- I have very little time. Build in this priority order and make each stage runnable before moving on: (1) synthetic KB plus basic retrieval and chat, (2) permission-aware retrieval and citations, (3) Output Contracts with validation, (4) Verifier and abstention, (5) Conflict Radar, (6) eval dashboard, (7) efficiency counter, (8) docs.
- Do not ask me questions; state assumptions briefly and proceed.
- Give complete file contents, not snippets. Include a test I can run to confirm it works.
- Keep the code robust: handle API errors, empty retrieval, and malformed model output gracefully.
- At the end, list what is fully working versus partial so I can be honest in the demo.

My name: [YOUR NAME]. PRN: [YOUR PRN].


2) which api key is recommended

3) Hey, the app is working well now and I'm happy with how it looks and behaves, so please don't change anything about the existing features, layout, or styling. I only want to add one thing on top of it: a login page that shows up first, before the main app opens.

Right now there's a persona selector in the app where I can switch between the roles (Employee, HR Manager, Finance Analyst, Customer, Legal Counsel, and whatever else I've added). I want that selector to go away from the main app and become the starting login screen instead.

Here's how I want the login to work:

1. When someone opens the app, they only see a clean login page. Nothing from the main app should be visible or reachable until they log in.
2. On that page they choose their role from a dropdown or a set of buttons. Please pick up the role list from what's already in the project code so it stays in sync, don't hardcode a new list.
3. For every role except Customer, ask for a password. There's one common password shared by all of these roles. Don't hardcode it in the source. Read it from the .env file (something like APP_PASSWORD) and add it to .env.example with a demo value.
4. Customer doesn't need a password, because customers are new and don't have an account. If they pick Customer, show a simple "Continue as Customer" button that takes them straight in.
5. If the password is wrong, show a clear error message and stay on the login page. If it's right, take them into the app.
6. Once logged in, the role they chose should be the active persona for the whole session. All the existing permission-aware retrieval, citations, and access rules should keep working exactly as before, just using the logged-in role. They shouldn't be able to switch roles from inside the app anymore.
7. Add a Logout button somewhere sensible (like the sidebar) that clears the session and sends them back to the login page, so a different role can log in.
8. Use st.session_state for the login state, and make sure the main app can't be reached without logging in first (for example by stopping the script if the user isn't authenticated).
9. Make the login page look neat and match the current look and feel of the app. Show the app name and a short one-line tagline.

Please tell me exactly which files you changed, give me the complete updated code for those files, and update the README with a short note on how login works and where to set the password. And please test that everything else still runs the same as before.

4) Thanks, the login page works great. I want to make two more improvements to the agent itself. Please keep everything else exactly as it is, including the login, the UI, and the existing features.

1. Real multi-turn memory

The task says the agent should reason across multiple turns, but right now the chat history only shows up in the UI. The backend only sends the current question to the LLM, so follow-ups like "can you summarize that previous answer?" or "what about for contractors?" don't work properly.

Please fix this:
- Pass st.session_state.messages into run_agent_pipeline() (if the names are different in my code, use whatever matches).
- Take the last 3 or 4 exchanges and add them to the Specialist's prompt as a short conversation history, so it can answer follow-ups in context.
- For retrieval, if the new question is a follow-up that depends on earlier turns, first rewrite it into a standalone question using the recent history, and use that for the document search. Skip retrieval when the user is only asking about the previous answer (like "summarize that" or "put that in a table").
- The Verifier should still check claims against the retrieved sources, but it shouldn't wrongly flag a follow-up answer as uncited just because it reused the previous answer.
- Keep the history short and truncated so it doesn't waste tokens. Include the history tokens in the tokens/energy counter.
- Clear the chat history whenever someone logs out or a different role logs in, so nothing from one role's conversation can leak into another's session.

2. Kohler values in the answers

Kohler cares a lot about water conservation and design excellence, and I want the agent to reflect that. Please edit the Specialist system prompt so that when the domain is Customer Support, the agent naturally highlights water-saving features when they're relevant to the customer's question, like WaterSense-certified products, low-flow options, touchless or sensor tech, and leak-prevention features.

Some rules for this:
- Only mention it when it's relevant. Don't force a sustainability line into unrelated answers like a warranty or return question.
- Don't invent claims. Only mention certifications or features that exist in our knowledge base. If needed, add a few water-saving product details to the synthetic Customer Support documents so the agent can cite them properly, and keep them clearly labeled as synthetic.
- Keep the tone helpful and not salesy.

Finally:
- Add 4 or 5 new test cases to the eval set: follow-up questions that need memory, a check that a follow-up doesn't leak another role's data, and a check that the water-saving mention appears for a relevant support question and doesn't appear for an irrelevant one.
- Update PROMPTS.md with the changed Specialist prompt and the new query-rewriting prompt.
- Tell me exactly which files you changed, give me the complete updated code for them, and make sure the app still runs as before.

5) Great, the memory and the Kohler values changes are working. I want to add two more things now, both about making the app feel more polished. Please keep everything else exactly as it is, including the login, the multi-turn memory, the pipeline, and the current look.

1. Streaming text generation

Right now the app shows a spinner, waits for the whole pipeline to finish, and then dumps the full answer on screen. I want the answer to type out like ChatGPT so it feels faster.

- Use st.write_stream() to stream the final answer.
- Important: my pipeline has a Verifier step, and I don't want to show unverified text to the user. So please don't stream the Specialist's raw output. Instead, while the Router, Specialist, and Verifier run, show a small live status (for example with st.status) with steps like "Routing question", "Retrieving sources", "Verifying claims". After verification, stream the final checked answer.
- For structured outputs (JSON, XML, Excel, draft emails with validation), don't stream. Show the validated result normally, along with the validation status and download buttons.
- Everything else, like the citations panel, confidence badge, and conflict alerts, should appear right after the streamed text finishes.
- The full answer must still be saved properly into st.session_state.messages so multi-turn memory and the chat history keep working.
- Add error handling so if the stream fails, the user still sees the complete answer instead of a blank message.

2. Feedback buttons

I want simple thumbs up and thumbs down buttons under every assistant answer, so I can say we built the foundation for a continuous improvement loop.

- Use st.feedback("thumbs") if my Streamlit version supports it. If not, use two simple buttons.
- Make sure each answer has its own unique key, so clicking on one doesn't affect the others, and a rerun doesn't save duplicates.
- When someone clicks, save one record to a local file called feedback/feedback_log.jsonl with: timestamp, logged-in role, the question, the answer, the rating, the confidence score, the cited source IDs, and the domain it was routed to.
- If they click thumbs down, show an optional small text box asking "What went wrong?" and save that comment too.
- Show a small "Feedback summary" section on the eval dashboard: total thumbs up, total thumbs down, and the satisfaction percentage. Read it from the file.
- Add the feedback folder to .gitignore so real feedback data doesn't get committed, but include a small sample file so the dashboard has something to show in the demo.

Also:
- Add a couple of tests: one that checks a feedback record gets written correctly, and one that checks structured outputs don't go through the streaming path.
- Update the README and PROMPTS.md with these changes.
- Tell me exactly which files you changed, give me the complete updated code for them, and confirm the app still runs as before.

6) dont change anything but tell me can i add two three api keys together? to increase the speed of evaluation suite because its taking almost 15 20 minutes to evaluate the project.

7) Push the project on GitHub.

