import streamlit as st
from typing import List, Dict
from src.config import EvalResult

def render_eval_summary(results: List[EvalResult]) -> Dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    pass_rate = passed / total if total > 0 else 0
    
    avg_score = sum(r.score for r in results) / total if total > 0 else 0
    # Dummy leakage rate calculation, assuming details contains it if relevant
    leakage_count = sum(1 for r in results if r.details.get("leaked", False))
    leakage_rate = leakage_count / total if total > 0 else 0
    
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "avg_score": avg_score,
        "leakage_rate": leakage_rate
    }

def render_category_breakdown(results: List[EvalResult]) -> None:
    categories = {}
    for r in results:
        categories.setdefault(r.category, []).append(r.score)
        
    avg_scores = {k: sum(v)/len(v) for k, v in categories.items()}
    st.bar_chart(avg_scores)

def render_eval_dashboard(results: List[EvalResult]) -> None:
    st.header("Evaluation Dashboard")
    summary = render_eval_summary(results)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tests", summary["total"])
    col2.metric("Pass Rate", f"{summary['pass_rate']:.1%}")
    col3.metric("Avg Score", f"{summary['avg_score']:.2f}")
    col4.metric("Leakage Rate", f"{summary['leakage_rate']:.1%}")
    
    st.subheader("Category Breakdown")
    render_category_breakdown(results)
    
    st.subheader("Test Results")
    data = []
    for r in results:
        data.append({
            "Category": r.category,
            "Question": r.question,
            "Persona": r.persona,
            "Passed": "✅" if r.passed else "❌",
            "Score": r.score
        })
    st.dataframe(data)

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
