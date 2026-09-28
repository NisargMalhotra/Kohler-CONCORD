"""
KOHLER CONCORD — Customer Tools.

Mock implementations of customer-facing actions:
  - create_support_ticket: logs a new support ticket
  - register_product: registers a product by serial number
"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)

TICKETS_FILE = os.path.join("data", "mock", "support_tickets.json")
REGISTRY_FILE = os.path.join("data", "mock", "product_registry.json")


def _load_json(path: str) -> list:
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_json(path: str, data: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def create_support_ticket(
    issue_summary: str,
    urgency: str = "medium",
    product: str = None,
) -> Dict[str, Any]:
    """Create a new support ticket and persist it."""
    tickets = _load_json(TICKETS_FILE)
    ticket_id = f"TKT-{1001 + len(tickets)}"

    ticket = {
        "ticket_id": ticket_id,
        "issue_summary": issue_summary,
        "urgency": urgency.lower() if urgency else "medium",
        "product": product or "Not specified",
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "timestamp": time.time(),
    }
    tickets.append(ticket)
    _save_json(TICKETS_FILE, tickets)

    logger.info(f"Support ticket created: {ticket_id}")
    return {
        "ticket_id": ticket_id,
        "status": "open",
        "message": f"Support ticket {ticket_id} has been created successfully.",
        "next_steps": (
            "A support representative will review your ticket within 24 hours. "
            "For urgent issues, call 1-800-4-KOHLER."
        ),
    }


def register_product(
    product_name: str,
    serial_number: str,
) -> Dict[str, Any]:
    """Register a Kohler product."""
    registry = _load_json(REGISTRY_FILE)

    # Check for duplicate
    for entry in registry:
        if entry.get("serial_number") == serial_number:
            return {
                "success": False,
                "message": f"Serial number {serial_number} is already registered.",
                "registration_id": entry.get("registration_id", "unknown"),
            }

    reg_id = f"REG-{2001 + len(registry)}"
    entry = {
        "registration_id": reg_id,
        "product_name": product_name,
        "serial_number": serial_number,
        "registered_at": datetime.now().isoformat(),
        "warranty_status": "active",
    }
    registry.append(entry)
    _save_json(REGISTRY_FILE, registry)

    logger.info(f"Product registered: {reg_id} ({product_name})")
    return {
        "success": True,
        "registration_id": reg_id,
        "product_name": product_name,
        "serial_number": serial_number,
        "warranty_status": "active",
        "message": (
            f"Your {product_name} (serial: {serial_number}) has been registered. "
            f"Registration ID: {reg_id}. Warranty is now active."
        ),
    }
