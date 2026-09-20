from typing import List, Dict
from src.config import EvalResult

def compute_pass_rate(results: List[EvalResult]) -> float:
    if not results: return 0.0
    return sum(1 for r in results if r.passed) / len(results)

def compute_faithfulness(results: List[EvalResult]) -> float:
    if not results: return 0.0
    return sum(r.score for r in results) / len(results)

def compute_leakage_rate(results: List[EvalResult]) -> float:
    if not results: return 0.0
    leak_count = sum(1 for r in results if r.details.get("leaked", False))
    return leak_count / len(results)

def compute_citation_accuracy(results: List[EvalResult]) -> float:
    # Dummy implementation
    return 1.0

def compute_category_scores(results: List[EvalResult]) -> Dict[str, float]:
    scores = {}
    counts = {}
    for r in results:
        scores[r.category] = scores.get(r.category, 0.0) + r.score
        counts[r.category] = counts.get(r.category, 0) + 1
    return {k: v / counts[k] for k, v in scores.items()}

def generate_report(results: List[EvalResult]) -> str:
    lines = ["# Evaluation Report", ""]
    lines.append(f"- **Pass Rate**: {compute_pass_rate(results):.2%}")
    lines.append(f"- **Avg Faithfulness**: {compute_faithfulness(results):.2f}")
    lines.append(f"- **Leakage Rate**: {compute_leakage_rate(results):.2%}")
    lines.append("")
    lines.append("## Category Scores")
    for k, v in compute_category_scores(results).items():
        lines.append(f"- **{k}**: {v:.2f}")
    return "\n".join(lines)
