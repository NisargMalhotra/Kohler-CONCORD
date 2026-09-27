"""
KOHLER CONCORD — Customer Support Experience UI.

A dedicated interface for customers, separate from the internal
enterprise chat. Provides two flows:
  - Get Help: complaint resolution with suggestion cards
  - Products & Info: product browsing and FAQ
"""

import time
import streamlit as st

from src.agents.customer_pipeline import run_customer_pipeline
from src.knowledge_base.customer_store import CustomerVectorStore
from src.llm import efficiency_stats
from src.ui.components import (
    render_confidence_badge,
    render_citations,
    render_efficiency_stats,
)
from src.ui.feedback import log_feedback


# ── Suggestion cards for "Get Help" ──────────────────────────────────────────

_HELP_SUGGESTIONS = [
    {"emoji": "🚰", "label": "My faucet is leaking",
     "query": "My faucet is leaking. How do I fix it?"},
    {"emoji": "📋", "label": "Check my warranty",
     "query": "What is the warranty on my Kohler product?"},
    {"emoji": "📦", "label": "Return a product",
     "query": "How do I return a defective Kohler product?"},
    {"emoji": "📡", "label": "Smart fixture not connecting",
     "query": "My Kohler smart faucet won't connect to WiFi. How do I fix it?"},
    {"emoji": "🚽", "label": "Toilet keeps running",
     "query": "My Kohler toilet keeps running. What should I do?"},
    {"emoji": "⚡", "label": "Generator won't start",
     "query": "My Kohler generator won't start. How do I troubleshoot it?"},
]

_INFO_SUGGESTIONS = [
    {"emoji": "💧", "label": "Water-saving products",
     "query": "Which Kohler products are WaterSense certified?"},
    {"emoji": "🏠", "label": "Smart home features",
     "query": "What smart home features does KOHLER Konnect offer?"},
    {"emoji": "🔧", "label": "Installation requirements",
     "query": "What are the installation requirements for Kohler products?"},
    {"emoji": "🛡️", "label": "Warranty coverage",
     "query": "What does the Kohler warranty cover and not cover?"},
]


# ── Streaming helper ─────────────────────────────────────────────────────────

def _stream_text(text: str):
    words = text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        time.sleep(0.02)


# ── Feedback ─────────────────────────────────────────────────────────────────

def _render_customer_feedback(msg_index: int, result: dict) -> None:
    fb_key = f"cust_fb_{msg_index}"
    if msg_index in st.session_state.get("customer_feedback_given", {}):
        prev = st.session_state.customer_feedback_given[msg_index]
        label = "👍" if prev == 1 else "👎"
        st.caption(f"Feedback recorded: {label}")
        return

    rating = st.feedback("thumbs", key=fb_key)
    if rating is not None:
        if "customer_feedback_given" not in st.session_state:
            st.session_state.customer_feedback_given = {}
        st.session_state.customer_feedback_given[msg_index] = rating

        log_feedback(
            rating=rating,
            persona="customer",
            question=result.get("_question", ""),
            answer=result.get("content", result.get("answer", "")),
            confidence=result.get("confidence", 0.0),
            cited_clauses=[
                c.get("clause_id", "") if isinstance(c, dict) else ""
                for c in result.get("citations", [])
            ],
            domains_used=result.get("domains_used", []),
            comment="",
        )
        st.caption("✅ Thanks for your feedback!")


# ── Assistant extras ─────────────────────────────────────────────────────────

def _render_customer_extras(result: dict) -> None:
    if result.get("should_abstain"):
        st.info(
            f"ℹ️ {result.get('abstention_reason', 'I may not have enough info to fully answer this.')}"
        )
    if result.get("needs_human"):
        action = result.get("suggested_action", "")
        st.warning(
            "👤 **This may need human assistance.** "
            + (f"{action} " if action else "")
            + "Call **1-800-4-KOHLER** or visit [kohler.com/support](https://www.kohler.com/support)."
        )
    if "confidence" in result:
        render_confidence_badge(result.get("confidence", 0.0))
    if result.get("citations"):
        render_citations(result["citations"])


# ── Main customer UI ─────────────────────────────────────────────────────────

def render_customer_experience(customer_store: CustomerVectorStore) -> None:
    """Full customer-facing experience replacing the default chat for Customer persona."""

    # Initialize customer-specific session state
    if "customer_help_messages" not in st.session_state:
        st.session_state.customer_help_messages = []
    if "customer_info_messages" not in st.session_state:
        st.session_state.customer_info_messages = []
    if "customer_feedback_given" not in st.session_state:
        st.session_state.customer_feedback_given = {}
    if "customer_mode" not in st.session_state:
        st.session_state.customer_mode = "🛠️ Get Help"

    # ── Sidebar ──────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("# 🏛️ KOHLER Support")
        st.caption("Your personal Kohler assistant")
        st.divider()

        st.markdown("**Logged in as:** 🛒 Customer")

        if st.button("🔓 Logout", use_container_width=True, key="cust_logout"):
            st.session_state.authenticated = False
            st.session_state.active_persona = None
            st.session_state.customer_help_messages = []
            st.session_state.customer_info_messages = []
            st.session_state.customer_feedback_given = {}
            st.rerun()

        st.divider()

        mode = st.radio(
            "What would you like to do?",
            ["🛠️ Get Help", "📦 Products & Info"],
            key="customer_mode_radio",
        )
        st.session_state.customer_mode = mode

        st.divider()
        st.markdown("### 🌱 Sustainability")
        render_efficiency_stats(efficiency_stats)

        st.divider()
        st.caption("Need a human? Call **1-800-4-KOHLER**")

    # ── Route to the correct mode ────────────────────────────────────
    if st.session_state.customer_mode == "🛠️ Get Help":
        _render_help_mode(customer_store)
    else:
        _render_info_mode(customer_store)


def _render_help_mode(customer_store: CustomerVectorStore) -> None:
    """Complaint resolution flow with suggestion cards."""
    st.markdown("## 🛠️ How can we help you today?")
    st.caption("Select a common issue or type your own question below.")

    # Show suggestion cards only if chat is empty
    messages = st.session_state.customer_help_messages
    if not messages:
        cols = st.columns(3)
        for i, suggestion in enumerate(_HELP_SUGGESTIONS):
            with cols[i % 3]:
                if st.button(
                    f"{suggestion['emoji']} {suggestion['label']}",
                    use_container_width=True,
                    key=f"help_sug_{i}",
                ):
                    # Inject the suggestion as the first user message
                    st.session_state.customer_help_messages.append(
                        {"role": "user", "content": suggestion["query"]}
                    )
                    st.rerun()
        st.divider()

    # Render chat history
    for idx, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg.get("content", msg.get("answer", "")))
            if msg["role"] == "assistant":
                _render_customer_extras(msg)
                _render_customer_feedback(idx, msg)

    # Process the last user message if it hasn't been answered
    if messages and messages[-1]["role"] == "user":
        user_input = messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.status("Finding the best answer for you...", expanded=True) as status:
                result = run_customer_pipeline(
                    query=user_input,
                    mode="help",
                    customer_store=customer_store,
                    conversation_history=messages,
                )
                status.update(label="✅ Ready", state="complete", expanded=False)

            answer_text = result.get("answer", "")
            try:
                st.write_stream(_stream_text(answer_text))
            except Exception:
                st.markdown(answer_text)

            _render_customer_extras(result)

            msg_data = {
                "role": "assistant",
                "content": answer_text,
                "_question": user_input,
                **result,
            }
            messages.append(msg_data)
            new_idx = len(messages) - 1
            _render_customer_feedback(new_idx, msg_data)

    # Chat input
    user_input = st.chat_input("Describe your issue...")
    if user_input:
        messages.append({"role": "user", "content": user_input})
        st.rerun()


def _render_info_mode(customer_store: CustomerVectorStore) -> None:
    """Product information browsing flow."""
    st.markdown("## 📦 Products & Information")
    st.caption("Ask about any Kohler product, feature, warranty, or specification.")

    messages = st.session_state.customer_info_messages

    # Show suggestion cards only if chat is empty
    if not messages:
        cols = st.columns(2)
        for i, suggestion in enumerate(_INFO_SUGGESTIONS):
            with cols[i % 2]:
                if st.button(
                    f"{suggestion['emoji']} {suggestion['label']}",
                    use_container_width=True,
                    key=f"info_sug_{i}",
                ):
                    st.session_state.customer_info_messages.append(
                        {"role": "user", "content": suggestion["query"]}
                    )
                    st.rerun()
        st.divider()

    # Render chat history
    for idx, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg.get("content", msg.get("answer", "")))
            if msg["role"] == "assistant":
                _render_customer_extras(msg)
                _render_customer_feedback(1000 + idx, msg)  # offset to avoid key collision

    # Process the last user message if it hasn't been answered
    if messages and messages[-1]["role"] == "user":
        user_input = messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.status("Looking that up for you...", expanded=True) as status:
                result = run_customer_pipeline(
                    query=user_input,
                    mode="info",
                    customer_store=customer_store,
                    conversation_history=messages,
                )
                status.update(label="✅ Ready", state="complete", expanded=False)

            answer_text = result.get("answer", "")
            try:
                st.write_stream(_stream_text(answer_text))
            except Exception:
                st.markdown(answer_text)

            _render_customer_extras(result)

            msg_data = {
                "role": "assistant",
                "content": answer_text,
                "_question": user_input,
                **result,
            }
            messages.append(msg_data)
            new_idx = 1000 + len(messages) - 1
            _render_customer_feedback(new_idx, msg_data)

    # Chat input
    user_input = st.chat_input("Ask about Kohler products...")
    if user_input:
        messages.append({"role": "user", "content": user_input})
        st.rerun()
