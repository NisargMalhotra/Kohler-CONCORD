"""
KOHLER CONCORD — Configuration and Shared Data Models.

Core types, enums, permission mappings, and application settings
used across all modules of the Kohler Unified Enterprise AI Agent.

All settings are loaded from environment variables (via .env file).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════


class Persona(str, Enum):
    """User roles with different document access permissions."""

    EMPLOYEE = "employee"
    HR_MANAGER = "hr_manager"
    FINANCE_ANALYST = "finance_analyst"
    CUSTOMER = "customer"
    LEGAL_COUNSEL = "legal_counsel"


class Domain(str, Enum):
    """Knowledge base document domains."""

    HR = "hr"
    FINANCE = "finance"
    CUSTOMER_SUPPORT = "customer_support"
    PRIVACY = "privacy"
    LEGAL = "legal"


# ═══════════════════════════════════════════════════════════════════════════════
# Permission Mappings
# ═══════════════════════════════════════════════════════════════════════════════

PERSONA_DOMAIN_ACCESS: Dict[Persona, List[Domain]] = {
    Persona.EMPLOYEE: [Domain.HR, Domain.CUSTOMER_SUPPORT],
    Persona.HR_MANAGER: [Domain.HR, Domain.PRIVACY, Domain.CUSTOMER_SUPPORT],
    Persona.FINANCE_ANALYST: [Domain.FINANCE, Domain.LEGAL],
    Persona.CUSTOMER: [Domain.CUSTOMER_SUPPORT, Domain.PRIVACY],
    Persona.LEGAL_COUNSEL: [
        Domain.HR,
        Domain.FINANCE,
        Domain.PRIVACY,
        Domain.LEGAL,
        Domain.CUSTOMER_SUPPORT,
    ],
}

PERSONA_ACCESS_LEVELS: Dict[Persona, List[str]] = {
    Persona.EMPLOYEE: ["public", "internal"],
    Persona.HR_MANAGER: ["public", "internal", "hr_confidential"],
    Persona.FINANCE_ANALYST: ["public", "internal", "finance_restricted"],
    Persona.CUSTOMER: ["public"],
    Persona.LEGAL_COUNSEL: [
        "public",
        "internal",
        "hr_confidential",
        "finance_restricted",
        "legal_privileged",
    ],
}

PERSONA_DISPLAY_NAMES: Dict[Persona, str] = {
    Persona.EMPLOYEE: "👤 Employee",
    Persona.HR_MANAGER: "👔 HR Manager",
    Persona.FINANCE_ANALYST: "📊 Finance Analyst",
    Persona.CUSTOMER: "🛒 Customer",
    Persona.LEGAL_COUNSEL: "⚖️ Legal Counsel",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Document:
    """A retrieved document chunk with metadata."""

    content: str
    metadata: Dict[str, Any]
    # Expected metadata keys:
    #   domain: str (Domain value)
    #   access_level: str ("public", "internal", "hr_confidential", etc.)
    #   clause_id: str (e.g., "HR-POL-003.2")
    #   source_file: str (e.g., "hr_policy.md")
    #   title: str (section title)
    #   chunk_id: str (unique identifier for this chunk)
    score: float = 0.0


@dataclass
class Conflict:
    """A detected conflict between two policy clauses."""

    clause_a_id: str
    clause_b_id: str
    domain_a: str
    domain_b: str
    text_a: str
    text_b: str
    description: str
    recommendation: str
    severity: str = "medium"  # "low", "medium", "high"


@dataclass
class Citation:
    """A citation linking a claim to a specific source text passage."""

    clause_id: str
    source_file: str
    relevant_text: str
    domain: str


@dataclass
class VerifiedAnswer:
    """Output of the Verifier agent — answer with citations and confidence."""

    answer: str
    citations: List[Citation]
    confidence: float  # 0.0 to 1.0
    should_abstain: bool
    abstention_reason: Optional[str] = None
    conflicts: List[Conflict] = field(default_factory=list)
    domains_used: List[str] = field(default_factory=list)


@dataclass
class FormatSpec:
    """Desired output format specification parsed from user instructions."""

    format_type: str  # "json", "xml", "excel", "email", "plain"
    schema: Optional[Dict[str, Any]] = None
    instructions: Optional[str] = None
    email_to: Optional[str] = None
    email_subject: Optional[str] = None
    email_tone: Optional[str] = None


@dataclass
class FormattedOutput:
    """Result of formatting an answer into the requested output contract."""

    content: str
    format_type: str
    validation_passed: bool
    validation_errors: List[str] = field(default_factory=list)
    file_path: Optional[str] = None
    file_bytes: Optional[bytes] = None


@dataclass
class EvalResult:
    """Result of evaluating a single test case."""

    question_id: str
    question: str
    persona: str
    expected_behavior: str
    actual_response: str
    passed: bool
    score: float
    details: Dict[str, Any] = field(default_factory=dict)
    category: str = ""


@dataclass
class EfficiencyStats:
    """Tracks token usage and energy savings for the sustainability counter."""

    total_tokens_used: int = 0
    tokens_saved_by_cache: int = 0
    tokens_saved_by_routing: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    small_model_calls: int = 0
    large_model_calls: int = 0

    @property
    def total_tokens_saved(self) -> int:
        return self.tokens_saved_by_cache + self.tokens_saved_by_routing

    @property
    def estimated_energy_saved_wh(self) -> float:
        """Rough estimate: ~0.001 Wh per 1000 tokens for cloud LLM inference."""
        return self.total_tokens_saved * 0.000001

    @property
    def estimated_co2_saved_g(self) -> float:
        """Rough estimate based on average US grid carbon intensity (~0.4 kg CO2/kWh)."""
        return self.estimated_energy_saved_wh * 0.4


# ═══════════════════════════════════════════════════════════════════════════════
# Application Settings
# ═══════════════════════════════════════════════════════════════════════════════


class Settings:
    """Application settings loaded from environment variables."""

    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_MODEL_SMALL: str = os.getenv("LLM_MODEL_SMALL", "gpt-4o-mini")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHROMA_DIR: str = os.getenv("CHROMA_DIR", "./chroma_db")
    DATA_DIR: str = os.getenv("DATA_DIR", "./data/knowledge_base")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")


settings = Settings()
