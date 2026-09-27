"""
KOHLER CONCORD — Evaluation Dashboard with System Health Panel.

Displays evaluation results (from saved file or live run), system
health metrics, and user feedback summaries.
"""

import streamlit as st
from typing import List, Dict, Optional

from src.config import EvalResult
from src.llm import efficiency_stats


def render_system_health() -> None:
    """System Health panel showing live reliability metrics."""
    st.subheader("🏥 System Health")

    total_queries = efficiency_stats.cache_hits + efficiency_stats.cache_misses
    cache_hit_rate = (
        efficiency_stats.cache_hits / max(total_queries, 1)
    )
    api_calls_saved = efficiency_stats.cache_hits + efficiency_stats.small_model_calls

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Cache Hit Rate", f"{cache_hit_rate:.0%}")
    c2.metric("Semantic Hits", efficiency_stats.semantic_cache_hits)
    c3.metric("Avg Latency", f"{efficiency_stats.avg_response_time_ms:.0f} ms")
    c4.metric("Degraded Responses", efficiency_stats.degraded_responses)
    c5.metric("API Calls Saved", api_calls_saved)

    # Estimated cost savings
    estimated_cost_saved = efficiency_stats.total_tokens_saved * 0.000002  # ~$2 per 1M tokens
    st.caption(
        f"💰 Estimated cost avoided: ${estimated_cost_saved:.4f} · "
        f"🌱 CO₂ saved: {efficiency_stats.estimated_co2_saved_g:.4f} g · "
        f"⚡ Energy saved: {efficiency_stats.estimated_energy_saved_wh:.4f} Wh"
    )
    st.divider()


def render_eval_summary(results: List[EvalResult]) -> Dict:
    """Compute summary statistics from eval results."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    pass_rate = passed / total if total > 0 else 0

    avg_score = sum(r.score for r in results) / total if total > 0 else 0
    leakage_count = sum(1 for r in results if r.details.get("leaked", False))
    leakage_rate = leakage_count / total if total > 0 else 0

    degraded_count = sum(
        1 for r in results
        if r.details.get("verification_level", "full") not in ("full", "n/a")
    )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "avg_score": avg_score,
        "leakage_rate": leakage_rate,
        "degraded_count": degraded_count,
    }


def render_category_breakdown(results: List[EvalResult]) -> None:
    """Bar chart of average score per category."""
    categories = {}
    for r in results:
        categories.setdefault(r.category, []).append(r.score)

    avg_scores = {k: sum(v) / len(v) for k, v in categories.items()}
    st.bar_chart(avg_scores)


def render_eval_dashboard(results: List[EvalResult]) -> None:
    """Full evaluation dashboard with health panel."""
    render_system_health()

    st.header("Evaluation Dashboard")
    summary = render_eval_summary(results)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Tests", summary["total"])
    col2.metric("Pass Rate", f"{summary['pass_rate']:.1%}")
    col3.metric("Avg Score", f"{summary['avg_score']:.2f}")
    col4.metric("Leakage Rate", f"{summary['leakage_rate']:.1%}")
    col5.metric("Degraded", summary["degraded_count"])

    st.subheader("Category Breakdown")
    render_category_breakdown(results)

    st.subheader("Test Results")
    data = []
    for r in results:
        vlevel = r.details.get("verification_level", "full")
        data.append({
            "ID": r.question_id,
            "Category": r.category,
            "Question": r.question[:80],
            "Persona": r.persona,
            "Passed": "✅" if r.passed else "❌",
            "Score": round(r.score, 2),
            "Verification": vlevel,
        })
    st.dataframe(data, use_container_width=True)

    # Feedback summary
    st.divider()
    st.subheader("User Feedback Summary")
    from src.ui.feedback import get_feedback_summary
    fb = get_feedback_summary()
    if fb["total"] > 0:
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Total Feedback", fb["total"])
        fc2.metric("👍 Thumbs Up", fb["thumbs_up"])
        fc3.metric("👎 Thumbs Down", fb["thumbs_down"])
        fc4.metric("Satisfaction", f"{fb['satisfaction_pct']}%")
    else:
        st.info("No feedback collected yet. Interact with the chat and rate answers to see metrics here.")
