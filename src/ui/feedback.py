"""
KOHLER CONCORD — User Feedback Module.

Provides feedback logging to a local JSONL file and a summary reader
for the evaluation dashboard.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_FEEDBACK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "feedback")
_FEEDBACK_FILE = os.path.join(_FEEDBACK_DIR, "feedback_log.jsonl")


def _ensure_dir() -> None:
    os.makedirs(_FEEDBACK_DIR, exist_ok=True)


def log_feedback(
    rating: int,
    persona: str,
    question: str,
    answer: str,
    confidence: float = 0.0,
    cited_clauses: Optional[List[str]] = None,
    domains_used: Optional[List[str]] = None,
    comment: str = "",
) -> None:
    """Append one feedback record to the JSONL log."""
    _ensure_dir()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rating": "thumbs_up" if rating == 1 else "thumbs_down",
        "persona": persona,
        "question": question[:500],
        "answer": answer[:500],
        "confidence": round(confidence, 3),
        "cited_clauses": cited_clauses or [],
        "domains_used": domains_used or [],
        "comment": comment[:500],
    }
    with open(_FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_feedback_records() -> List[Dict[str, Any]]:
    """Read all feedback records from the log file."""
    if not os.path.isfile(_FEEDBACK_FILE):
        return []
    records = []
    with open(_FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def get_feedback_summary() -> Dict[str, Any]:
    """Compute aggregate metrics from the feedback log."""
    records = load_feedback_records()
    total = len(records)
    thumbs_up = sum(1 for r in records if r.get("rating") == "thumbs_up")
    thumbs_down = total - thumbs_up
    satisfaction = (thumbs_up / total * 100) if total > 0 else 0.0
    return {
        "total": total,
        "thumbs_up": thumbs_up,
        "thumbs_down": thumbs_down,
        "satisfaction_pct": round(satisfaction, 1),
    }
