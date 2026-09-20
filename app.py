"""
KOHLER CONCORD — Streamlit Application Entry Point.

Main UI for the Kohler Unified Enterprise AI Agent with Trust Layer.
Provides: login gate, chat interface with streaming, citations panel,
conflict alerts, confidence badges, format selector, download buttons,
feedback buttons, eval dashboard, and sustainability counter.
"""

import os
import time
import streamlit as st

from src.agents.pipeline import run_agent_pipeline
from src.knowledge_base import KnowledgeBaseLoader, DocumentChunker, VectorStore
from src.config import (
    Persona,
    PERSONA_DISPLAY_NAMES,
    settings,
)
from src.llm import efficiency_stats
from src.ui.components import (
    render_confidence_badge,
    render_citations,
    render_conflicts,
    render_formatted_output,
    render_efficiency_stats,
    render_denial_messages,
)
from src.ui.dashboard import render_eval_dashboard
from src.ui.feedback import log_feedback
from eval.runner import EvalRunner

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="KOHLER CONCORD", page_icon="🏛️", layout="wide")


# ── Session state initialisation ──────────────────────────────────────────────


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "kb_initialized" not in st.session_state:
        st.session_state.kb_initialized = False
    if "eval_results" not in st.session_state:
        st.session_state.eval_results = []
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "active_persona" not in st.session_state:
        st.session_state.active_persona = None
    if "feedback_given" not in st.session_state:
        st.session_state.feedback_given = {}  # msg_index -> rating


# ── Login page ────────────────────────────────────────────────────────────────


def _get_app_password() -> str:
    """Read the shared app password from environment / .env file."""
    return os.getenv("APP_PASSWORD", "kohler2024")


def render_login() -> None:
    """
    Full-screen login page.  Blocks the rest of the app until the user
    authenticates.  Customer role skips the password step.
    """

    # Centre the login card using columns
    _pad_l, col, _pad_r = st.columns([1, 2, 1])

    with col:
        st.markdown("")
        st.markdown("")
        st.markdown(
            "<h1 style='text-align:center;'>🏛️ KOHLER CONCORD</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center; opacity:0.7;'>"
            "Unified Enterprise AI Agent with Trust Layer</p>",
            unsafe_allow_html=True,
        )
        st.markdown("")

        st.divider()

        # Role selector — pull list dynamically from config
        persona_options = list(PERSONA_DISPLAY_NAMES.values())
        selected_display = st.selectbox(
            "Select your role", persona_options, key="login_role_select"
        )

        # Resolve back to Persona enum
        selected_persona: Persona = Persona.EMPLOYEE
        for p, name in PERSONA_DISPLAY_NAMES.items():
            if name == selected_display:
                selected_persona = p
                break

        is_customer = selected_persona == Persona.CUSTOMER

        if is_customer:
            # No password needed for customers
            st.info("👋 Customers can continue without a password.")
            if st.button(
                "Continue as Customer", use_container_width=True, type="primary"
            ):
                st.session_state.authenticated = True
                st.session_state.active_persona = selected_persona
                st.rerun()
        else:
            # Password required for internal roles
            password = st.text_input("Password", type="password", key="login_pw")

            if st.button("Log In", use_container_width=True, type="primary"):
                expected = _get_app_password()
                if password == expected:
                    st.session_state.authenticated = True
                    st.session_state.active_persona = selected_persona
                    st.rerun()
                else:
                    st.error("❌ Incorrect password. Please try again.")

        st.divider()
        st.caption(
            "Internal roles require the shared enterprise password.  "
            "If you don't have it, contact your administrator."
        )


# ── KB initialisation ───────────────────────────────────────────────────────


def initialize_kb() -> None:
    """Load, chunk, and index the synthetic knowledge base."""
    with st.spinner("Loading knowledge base (first run downloads embedding model ~90 MB)…"):
        loader = KnowledgeBaseLoader()
        raw_docs = loader.load_all()
        if not raw_docs:
            st.error("No documents found. Check DATA_DIR in .env.")
            return

        chunker = DocumentChunker()
        chunks = chunker.chunk_documents(raw_docs)

        store = VectorStore()
        store.initialize(chunks)

        st.session_state.vector_store = store
        st.session_state.kb_initialized = True
        st.success(f"✅ Knowledge Base initialised — {len(chunks)} chunks indexed.")


# ── Evaluation runner ───────────────────────────────────────────────────────


def run_evaluation() -> None:
    if not st.session_state.get("kb_initialized"):
        st.error("Initialise the Knowledge Base first.")
        return

    with st.spinner("Running evaluation suite…"):
        runner = EvalRunner(st.session_state.vector_store)
        progress_bar = st.progress(0)

        def on_progress(current: int, total: int) -> None:
            progress_bar.progress(current / max(total, 1))

        results = runner.run_all(progress_callback=on_progress)
        st.session_state.eval_results = results
        progress_bar.empty()
        st.success(f"✅ Evaluation complete — {len(results)} tests run.")


# ── Format mapping ──────────────────────────────────────────────────────────

FORMAT_MAP = {
    "Plain Text": "",
    "JSON": "Format the response as a JSON object",
    "XML": "Format the response as XML",
    "Excel Download": "Create an Excel spreadsheet summary",
    "Draft Email": "Draft a professional email summarising this",
}


# ── Streaming helper ─────────────────────────────────────────────────────────


def _stream_text(text: str):
    """Generator that yields text word-by-word for st.write_stream."""
    words = text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        time.sleep(0.02)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _render_assistant_extras(result: dict) -> None:
    """Renders badges, citations, conflicts, and formatted outputs."""
    if result.get("is_injection"):
        st.error("🛡️ **Security Alert:** Potential prompt injection detected and blocked.")
    if result.get("should_abstain"):
        st.info(f"ℹ️ **Insufficient Evidence:** {result.get('abstention_reason', 'Not enough supporting documents.')}")
    if "confidence" in result:
        render_confidence_badge(result.get("confidence", 0.0))
    if result.get("denied_domains"):
        render_denial_messages(result["denied_domains"])
    if result.get("citations"):
        render_citations(result["citations"])
    if result.get("conflicts"):
        render_conflicts(result["conflicts"])
    if result.get("format_output"):
        render_formatted_output(result["format_output"])


def _render_feedback(msg_index: int, result: dict) -> None:
    """Render thumbs-up / thumbs-down feedback widget for one message."""
    fb_key = f"fb_{msg_index}"

    # Already submitted?
    if msg_index in st.session_state.feedback_given:
        prev = st.session_state.feedback_given[msg_index]
        label = "👍" if prev == 1 else "👎"
        st.caption(f"Feedback recorded: {label}")
        return

    rating = st.feedback("thumbs", key=fb_key)

    if rating is not None:
        st.session_state.feedback_given[msg_index] = rating

        persona_val = ""
        if st.session_state.active_persona:
            persona_val = st.session_state.active_persona.value

        # Extract info from the result dict
        question = result.get("_question", "")
        answer = result.get("content", result.get("answer", ""))
        confidence = result.get("confidence", 0.0)
        cited = [c.get("clause_id", "") if isinstance(c, dict) else "" for c in result.get("citations", [])]
        domains = result.get("domains_used", [])

        # For thumbs down, show comment box
        comment = ""
        if rating == 0:  # thumbs down
            comment = st.text_input(
                "What went wrong? (optional)",
                key=f"fb_comment_{msg_index}",
                placeholder="Tell us how we can improve…",
            )

        log_feedback(
            rating=rating,
            persona=persona_val,
            question=question,
            answer=answer,
            confidence=confidence,
            cited_clauses=cited,
            domains_used=domains,
            comment=comment,
        )
        st.caption("✅ Thanks for your feedback!")


def _do_logout() -> None:
    """Clear auth state and send user back to login."""
    st.session_state.authenticated = False
    st.session_state.active_persona = None
    st.session_state.messages = []
    st.session_state.feedback_given = {}
    st.rerun()


# ── Main (post-login) ──────────────────────────────────────────────────────


def main() -> None:
    init_session()

    # ── Gate: show login page if not authenticated ────────────────
    if not st.session_state.authenticated:
        render_login()
        st.stop()  # Nothing below runs until login succeeds

    # The persona is locked to whatever was chosen at login
    selected_persona: Persona = st.session_state.active_persona

    # ── Sidebar ───────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("# 🏛️ KOHLER CONCORD")
        st.caption("Unified Enterprise AI Agent with Trust Layer")
        st.divider()

        # Show logged-in role (read-only)
        display_name = PERSONA_DISPLAY_NAMES.get(selected_persona, str(selected_persona))
        st.markdown(f"**Logged in as:** {display_name}")

        # Logout button
        if st.button("🔓 Logout", use_container_width=True):
            _do_logout()

        st.divider()

        # Format selector
        format_options = list(FORMAT_MAP.keys())
        selected_format = st.selectbox("Output Format", format_options)
        custom_fmt = st.text_input(
            "Custom format instruction",
            placeholder="e.g. 'Draft email to john@kohler.com in formal tone'",
        )

        st.divider()

        # KB init button
        if st.button("🔄 Initialise Knowledge Base", use_container_width=True):
            initialize_kb()

        # Eval button
        if st.button("🧪 Run Evaluation Suite", use_container_width=True):
            run_evaluation()

        st.divider()

        # Efficiency / sustainability counter
        st.markdown("### 🌱 Sustainability")
        render_efficiency_stats(efficiency_stats)

    # ── Main area tabs ──────────────────────────────────────────────────
    tab_chat, tab_eval, tab_kb = st.tabs(
        ["💬 Chat", "📊 Eval Dashboard", "🔍 Knowledge Base"]
    )

    # ── Tab 1: Chat ───────────────────────────────────────────────────
    with tab_chat:
        # Render history
        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg.get("content", msg.get("answer", "")))
                if msg["role"] == "assistant":
                    _render_assistant_extras(msg)
                    _render_feedback(idx, msg)

        # User input
        user_input = st.chat_input("Ask a question…")
        if user_input:
            st.session_state.messages.append(
                {"role": "user", "content": user_input}
            )
            with st.chat_message("user"):
                st.markdown(user_input)

            if not st.session_state.get("kb_initialized"):
                with st.chat_message("assistant"):
                    st.warning(
                        "⚠️ Knowledge base not initialised. "
                        "Click **Initialise Knowledge Base** in the sidebar."
                    )
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": "Please initialise the knowledge base first.",
                        }
                    )
            else:
                with st.chat_message("assistant"):
                    # Build format instruction
                    fmt_instr = custom_fmt or FORMAT_MAP.get(
                        selected_format, ""
                    )
                    has_structured_format = bool(fmt_instr.strip())

                    # ── Pipeline with live status ─────────────────────
                    with st.status("🧠 Processing your question…", expanded=True) as status:
                        status.update(label="📡 Routing question…")
                        result = run_agent_pipeline(
                            query=user_input,
                            persona=selected_persona,
                            format_instruction=fmt_instr,
                            vector_store=st.session_state.vector_store,
                            conversation_history=st.session_state.messages,
                        )
                        status.update(label="✅ Complete", state="complete", expanded=False)

                    answer_text = result.get("answer", "")

                    # Stream or display the answer
                    if has_structured_format and result.get("format_output"):
                        # Structured output — no streaming, show validated result
                        st.markdown(answer_text)
                    else:
                        # Stream the verified answer word-by-word
                        try:
                            st.write_stream(_stream_text(answer_text))
                        except Exception:
                            # Fallback: show complete answer if streaming fails
                            st.markdown(answer_text)

                    # Render all badges and extras
                    _render_assistant_extras(result)

                    # Save to history (include _question for feedback logging)
                    msg_data = {
                        "role": "assistant",
                        "content": answer_text,
                        "_question": user_input,
                        **result,
                    }
                    st.session_state.messages.append(msg_data)

                    # Render feedback for the new message
                    new_idx = len(st.session_state.messages) - 1
                    _render_feedback(new_idx, msg_data)

    # ── Tab 2: Eval Dashboard ───────────────────────────────────────
    with tab_eval:
        if st.session_state.eval_results:
            render_eval_dashboard(st.session_state.eval_results)
        else:
            st.info(
                "Click **Run Evaluation Suite** in the sidebar to generate results."
            )

    # ── Tab 3: Knowledge Base browser ───────────────────────────────
    with tab_kb:
        if st.session_state.get("kb_initialized"):
            store = st.session_state.vector_store
            stats = store.get_collection_stats()
            st.metric("Indexed Chunks", stats.get("count", 0))

            search_q = st.text_input("🔍 Search the Knowledge Base")
            if search_q:
                results = store.search(search_q, top_k=10)
                for doc in results:
                    with st.expander(
                        f"[{doc.metadata.get('domain', '?')}] "
                        f"{doc.metadata.get('clause_id', '?')} — "
                        f"{doc.metadata.get('title', 'Untitled')}"
                    ):
                        st.caption(
                            f"Source: {doc.metadata.get('source_file')} · "
                            f"Access: {doc.metadata.get('access_level')} · "
                            f"Score: {doc.score:.3f}"
                        )
                        st.markdown(doc.content)
        else:
            st.info("Initialise the Knowledge Base to browse documents.")


if __name__ == "__main__":
    main()
