"""
KOHLER CONCORD — Streamlit UI Components.

Reusable rendering helpers for the chat interface: confidence badges,
citation panels, conflict alerts, formatted output with download buttons,
efficiency counters, and access-denial messages.

All functions accept both dataclass instances and plain dicts so they
work with both live pipeline output and serialised session-state history.
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

import streamlit as st

from src.config import Citation, Conflict, EfficiencyStats, FormattedOutput


# ── helpers ───────────────────────────────────────────────────────────────────

def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Retrieve attribute or dict key transparently."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ── public components ─────────────────────────────────────────────────────────

def render_confidence_badge(confidence: float) -> None:
    """Display a colour-coded confidence indicator."""
    if confidence >= 0.7:
        st.markdown(f"🟢 **High Confidence** ({confidence:.0%})")
    elif confidence >= 0.4:
        st.markdown(f"🟡 **Medium Confidence** ({confidence:.0%})")
    else:
        st.markdown(f"🔴 **Low Confidence** ({confidence:.0%})")


def render_citations(citations: List[Union[Citation, Dict]]) -> None:
    """Expandable citation list with clause IDs and source text."""
    if not citations:
        return
    with st.expander(f"📄 Citations ({len(citations)})", expanded=False):
        for c in citations:
            clause = _get(c, "clause_id", "?")
            source = _get(c, "source_file", "?")
            text = _get(c, "relevant_text", "")
            domain = _get(c, "domain", "")
            st.markdown(
                f"**[{clause}]** `{source}` · *{domain}*"
            )
            st.markdown(f"> {text}")
            st.markdown("---")


def render_conflicts(conflicts: List[Union[Conflict, Dict]]) -> None:
    """Warning block listing detected policy conflicts."""
    if not conflicts:
        return
    st.warning(f"⚠️ **Policy Conflict Radar** — {len(conflicts)} conflict(s) detected")
    for c in conflicts:
        a_id = _get(c, "clause_a_id", "?")
        b_id = _get(c, "clause_b_id", "?")
        d_a = _get(c, "domain_a", "?")
        d_b = _get(c, "domain_b", "?")
        desc = _get(c, "description", "")
        rec = _get(c, "recommendation", "")
        sev = _get(c, "severity", "medium")

        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "🟡")
        st.markdown(
            f"{icon} **{a_id}** ({d_a}) ↔ **{b_id}** ({d_b})"
        )
        st.markdown(f"  {desc}")
        st.markdown(f"  💡 *Recommendation:* {rec}")
        st.markdown("---")


def render_formatted_output(output: Union[FormattedOutput, Dict]) -> None:
    """Show formatted content with validation badge and download button."""
    fmt_type = _get(output, "format_type", "plain")
    valid = _get(output, "validation_passed", False)
    errors = _get(output, "validation_errors", [])
    content = _get(output, "content", "")
    file_bytes = _get(output, "file_bytes", None)
    file_path = _get(output, "file_path", None)

    # Validation badge
    if valid:
        st.success(f"✅ Output validated — **{fmt_type.upper()}**")
    else:
        st.error(f"❌ Validation failed — **{fmt_type.upper()}**")
        for err in errors:
            st.caption(f"  • {err}")

    # Unique key to avoid StreamlitDuplicateElementId on history replay
    _uid = str(hash((fmt_type, str(content)[:100], str(file_path))))

    # Content display
    if fmt_type in ("json", "xml"):
        lang = "json" if fmt_type == "json" else "xml"
        st.code(content, language=lang)
    elif fmt_type == "email":
        st.text_area("Draft Email", content, height=250, key=f"fmt_email_{_uid}")
    elif content:
        st.text_area("Formatted Output", content, height=200, key=f"fmt_out_{_uid}")

    # Download button
    if file_bytes:
        fname = file_path or f"output.{fmt_type}"
        if isinstance(fname, str) and "/" in fname:
            fname = fname.rsplit("/", 1)[-1]
        if isinstance(fname, str) and "\\" in fname:
            fname = fname.rsplit("\\", 1)[-1]
        st.download_button(
            label=f"⬇️ Download {fmt_type.upper()} file",
            data=file_bytes,
            file_name=fname,
            use_container_width=True,
            key=f"dl_{_uid}",
        )


def render_efficiency_stats(stats: EfficiencyStats) -> None:
    """Sidebar sustainability metrics."""
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tokens Used", f"{stats.total_tokens_used:,}")
        st.metric("Cache Hits", stats.cache_hits)
        st.metric("Small Model Calls", stats.small_model_calls)
    with col2:
        st.metric("Tokens Saved", f"{stats.total_tokens_saved:,}")
        st.metric("Energy Saved", f"{stats.estimated_energy_saved_wh:.4f} Wh")
        st.metric("CO₂ Saved", f"{stats.estimated_co2_saved_g:.4f} g")


def render_denial_messages(messages: List[str]) -> None:
    """Info messages about access-restricted domains."""
    if not messages:
        return
    for m in messages:
        st.info(f"🔒 {m}")
