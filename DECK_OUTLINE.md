# KOHLER CONCORD — Presentation Deck Outline

## Slide 1: Problem & Insight
- **The Problem:** Enterprise knowledge is deeply siloed across HR, Finance, Legal, and Customer Support.
- **The Status Quo:** Current solutions (basic RAG chatbots) lack trust. They suffer from zero access control, no verification mechanisms, and complete unawareness of policy conflicts.
- **The Insight:** The core gap isn't in retrieval algorithms — it's in **TRUST**. Enterprises require an AI that knows what it doesn't know, strictly respects access boundaries, and catches policy contradictions automatically.
- **Kohler Alignment:** Design excellence means building AI that is as robust, safe, and reliable as Kohler's world-class engineering.

## Slide 2: Architecture & Trust Layer
- **CONCORD** = **CON**fidence + **CO**nflict **R**esolution + **D**ocument-grounded answers.
- **The 5 Trust Layer Features:** (Visual Flow Diagram goes here)
- **Multi-Agent Pipeline:** Router → Specialist → Verifier → Formatter. 
- **Persona-Driven Scope:** Show a visual example of how the exact same query receives different, correctly-scoped answers depending on whether the user is an Employee, a Finance Analyst, or a Customer.

## Slide 3: Tech Stack & Innovation
- **Tech Stack:** Python, Streamlit, ChromaDB, OpenAI API, local sentence-transformers.
- **Innovations Beyond Basic RAG:**
  - Hybrid retrieval augmented with permission-aware metadata filtering.
  - Self-verifying pipeline utilizing confidence scores and abstention logic.
  - **Policy Conflict Radar** (Our unique differentiator).
  - Output Contracts with hard validation (not just formatted text — but *validated* outputs).
  - Built-in red-team evaluation suite.
- **Sustainability:** Intelligent model routing, response caching, and live energy tracking parallel Kohler's commitment to operational efficiency and sustainability.

## Slide 4: Results & Business Impact
- **Eval Dashboard Results:** (Placeholder metrics) X% pass rate, Y% faithfulness, 0% data leakage across personas.
- **Business Value:**
  - Reduced legal & compliance risk via the Conflict Radar.
  - Faster employee onboarding and self-service.
  - Responsible AI implementation with highly verifiable, auditable answers.
- **Kohler Alignment:** Parallels with water conservation (efficient use of compute resources) and design excellence (trust by design).
- **Future Roadmap:** Fine-tuned local models, direct integration with live document stores (SharePoint/Confluence), and full SSO/RBAC integration.
