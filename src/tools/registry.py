"""
KOHLER CONCORD — Tool Registry.

Defines available tools for each role and provides execution logic.
Tools let the AI agent take real actions (create tickets, check balances)
instead of just answering questions.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Describes a tool the LLM can call."""
    name: str
    description: str
    parameters: Dict[str, str]  # param_name -> description
    roles: List[str]  # which personas can use this tool


@dataclass
class ToolResult:
    """Result of executing a tool."""
    tool_name: str
    parameters: Dict[str, Any]
    success: bool
    result: Dict[str, Any]
    error: Optional[str] = None


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, definition: ToolDefinition, handler: Callable) -> None:
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def get_tools_for_role(self, role: str) -> List[ToolDefinition]:
        return [t for t in self._tools.values() if role in t.roles]

    def get_tools_prompt(self, role: str) -> str:
        """Build a prompt section describing available tools for the LLM."""
        tools = self.get_tools_for_role(role)
        if not tools:
            return ""

        lines = ["\n\nAVAILABLE TOOLS:"]
        lines.append(
            "If the user is asking you to PERFORM AN ACTION (not just answer a question), "
            "you may call a tool. To call a tool, include a 'tool_call' key in your JSON "
            "response instead of 'answer'. Format:"
        )
        lines.append(
            '{"tool_call": {"name": "<tool_name>", "parameters": {<param_dict>}}}'
        )
        lines.append("\nTools:")
        for t in tools:
            params_str = ", ".join(
                f'"{k}": "{v}"' for k, v in t.parameters.items()
            )
            lines.append(f"  - {t.name}: {t.description}")
            lines.append(f"    Parameters: {{{params_str}}}")
        lines.append(
            "\nIMPORTANT: Only call a tool when the user clearly wants an action "
            "performed. For informational questions, answer normally with 'answer', "
            "'cited_clauses', 'key_points'."
        )
        return "\n".join(lines)

    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with the given parameters."""
        if tool_name not in self._handlers:
            return ToolResult(
                tool_name=tool_name,
                parameters=parameters,
                success=False,
                result={},
                error=f"Unknown tool: {tool_name}",
            )
        try:
            handler = self._handlers[tool_name]
            result = handler(**parameters)
            return ToolResult(
                tool_name=tool_name,
                parameters=parameters,
                success=True,
                result=result,
            )
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return ToolResult(
                tool_name=tool_name,
                parameters=parameters,
                success=False,
                result={},
                error=str(e),
            )
