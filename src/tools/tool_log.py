"""
KOHLER CONCORD — Tool Call Logger.

Logs every tool invocation for the eval/health dashboard.
"""

import json
import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TOOL_LOG_FILE = os.path.join("data", "mock", "tool_call_log.json")


def log_tool_call(
    tool_name: str,
    parameters: Dict[str, Any],
    result: Dict[str, Any],
    success: bool,
    role: str,
    error: Optional[str] = None,
) -> None:
    """Append a tool call record to the log."""
    entries = []
    if os.path.isfile(TOOL_LOG_FILE):
        try:
            with open(TOOL_LOG_FILE, "r") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, IOError):
            entries = []

    entries.append(
        {
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
            "success": success,
            "error": error,
            "role": role,
            "timestamp": datetime.now().isoformat(),
        }
    )

    os.makedirs(os.path.dirname(TOOL_LOG_FILE), exist_ok=True)
    with open(TOOL_LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2, default=str)


def get_tool_call_stats() -> Dict[str, Any]:
    """Return summary statistics for the dashboard."""
    if not os.path.isfile(TOOL_LOG_FILE):
        return {"total_calls": 0, "successful": 0, "failed": 0, "by_tool": {}}

    try:
        with open(TOOL_LOG_FILE, "r") as f:
            entries = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"total_calls": 0, "successful": 0, "failed": 0, "by_tool": {}}

    by_tool: Dict[str, int] = {}
    successful = 0
    for e in entries:
        name = e.get("tool_name", "unknown")
        by_tool[name] = by_tool.get(name, 0) + 1
        if e.get("success"):
            successful += 1

    return {
        "total_calls": len(entries),
        "successful": successful,
        "failed": len(entries) - successful,
        "by_tool": by_tool,
    }
