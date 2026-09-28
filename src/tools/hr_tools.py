"""
KOHLER CONCORD — HR Tools.

Mock implementations of HR-facing actions:
  - check_pto_balance: looks up employee PTO balance
"""

import json
import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

PTO_FILE = os.path.join("data", "mock", "pto_balances.json")


def check_pto_balance(employee_id_or_name: str) -> Dict[str, Any]:
    """Look up PTO balance for an employee."""
    if not os.path.isfile(PTO_FILE):
        return {
            "found": False,
            "message": "PTO database not available. Please contact HR.",
        }

    with open(PTO_FILE, "r") as f:
        data = json.load(f)

    employees = data.get("employees", [])
    search = employee_id_or_name.strip().lower()

    for emp in employees:
        if (
            emp.get("id", "").lower() == search
            or emp.get("name", "").lower() == search
            or search in emp.get("name", "").lower()
        ):
            return {
                "found": True,
                "employee_id": emp["id"],
                "employee_name": emp["name"],
                "department": emp.get("department", "Unknown"),
                "pto_total": emp["pto_total"],
                "pto_used": emp["pto_used"],
                "pto_remaining": emp["pto_remaining"],
                "message": (
                    f"{emp['name']} ({emp['id']}) has {emp['pto_remaining']} PTO days "
                    f"remaining out of {emp['pto_total']} total ({emp['pto_used']} used)."
                ),
            }

    return {
        "found": False,
        "message": (
            f"No employee found matching '{employee_id_or_name}'. "
            "Please check the ID or name and try again."
        ),
    }
