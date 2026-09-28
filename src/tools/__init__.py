"""
KOHLER CONCORD — Tool Calling System.

Provides mock enterprise tools that the AI agent can execute:
  - create_support_ticket (Customer)
  - register_product (Customer)
  - check_pto_balance (HR Manager, Employee)
"""

from src.tools.registry import ToolRegistry, ToolDefinition, ToolResult
from src.tools.customer_tools import create_support_ticket, register_product
from src.tools.hr_tools import check_pto_balance
from src.tools.tool_log import log_tool_call, get_tool_call_stats


def build_tool_registry() -> ToolRegistry:
    """Build and return the global tool registry with all tools registered."""
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="create_support_ticket",
            description="Create a new support ticket for a customer complaint or issue. Use when the customer wants to file a complaint, report a problem, or escalate an issue.",
            parameters={
                "issue_summary": "Brief description of the customer's issue",
                "urgency": "low, medium, or high",
                "product": "Product name/model if mentioned, otherwise 'Not specified'",
            },
            roles=["customer"],
        ),
        create_support_ticket,
    )

    registry.register(
        ToolDefinition(
            name="register_product",
            description="Register a Kohler product with its serial number for warranty activation. Use when a customer wants to register a new product.",
            parameters={
                "product_name": "Name or model of the Kohler product",
                "serial_number": "The product's serial number",
            },
            roles=["customer"],
        ),
        register_product,
    )

    registry.register(
        ToolDefinition(
            name="check_pto_balance",
            description="Check an employee's PTO (Paid Time Off) balance. Use when someone asks about remaining vacation days, leave balance, or time off available for a specific employee.",
            parameters={
                "employee_id_or_name": "The employee's ID (e.g. EMP001) or full name",
            },
            roles=["hr_manager", "employee"],
        ),
        check_pto_balance,
    )

    return registry
