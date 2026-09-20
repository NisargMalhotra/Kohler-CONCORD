"""Generate KOHLER CONCORD 4-slide presentation deck as PDF."""

from fpdf import FPDF


class DeckPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)

    def slide_bg(self):
        """Dark background for all slides."""
        self.set_fill_color(18, 18, 28)
        self.rect(0, 0, 297, 210, "F")

    def gold_bar(self):
        """Accent bar at top."""
        self.set_fill_color(196, 164, 105)
        self.rect(0, 0, 297, 4, "F")

    def slide_number(self, n, total=4):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 140)
        self.set_xy(270, 195)
        self.cell(20, 10, f"{n}/{total}", align="R")

    def heading(self, text, y=18):
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(196, 164, 105)
        self.set_xy(20, y)
        self.cell(257, 14, text)

    def subheading(self, text, y=35):
        self.set_font("Helvetica", "", 14)
        self.set_text_color(180, 180, 200)
        self.set_xy(20, y)
        self.cell(257, 8, text)

    def bullet(self, text, x, y, bold_part="", width=120):
        self.set_xy(x, y)
        if bold_part:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(230, 230, 245)
            self.cell(self.get_string_width(bold_part) + 1, 7, bold_part, new_x="END")
            self.set_font("Helvetica", "", 11)
            self.set_text_color(180, 180, 200)
            self.multi_cell(width - self.get_string_width(bold_part) - 1, 7, text)
        else:
            self.set_font("Helvetica", "", 11)
            self.set_text_color(180, 180, 200)
            self.multi_cell(width, 7, text)

    def section_label(self, text, x, y):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(196, 164, 105)
        self.set_xy(x, y)
        self.cell(120, 8, text)


def build_deck():
    pdf = DeckPDF()

    # ── SLIDE 1: Title ──────────────────────────────────────────────────
    pdf.add_page()
    pdf.slide_bg()
    pdf.gold_bar()

    pdf.set_font("Helvetica", "B", 42)
    pdf.set_text_color(240, 240, 255)
    pdf.set_xy(20, 50)
    pdf.cell(257, 20, "KOHLER CONCORD", align="C")

    pdf.set_font("Helvetica", "", 18)
    pdf.set_text_color(196, 164, 105)
    pdf.set_xy(20, 75)
    pdf.cell(257, 12, "Unified Enterprise AI Agent with Trust Layer", align="C")

    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(160, 160, 180)
    pdf.set_xy(20, 100)
    pdf.cell(257, 10, "KOHLER-MITWPU AI Research Lab  |  Track 3: Enterprise Knowledge Agent", align="C")

    pdf.set_xy(20, 120)
    pdf.cell(257, 10, "Multi-Agent RAG  |  Role-Based Access  |  Self-Verifying Pipeline", align="C")

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(196, 164, 105)
    pdf.set_xy(20, 155)
    pdf.cell(257, 10, "Nisarg Malhotra  |  PRN: 1262243207", align="C")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(140, 140, 160)
    pdf.set_xy(20, 167)
    pdf.cell(257, 10, "MIT-WPU, School of Computer Science", align="C")

    pdf.slide_number(1)

    # ── SLIDE 2: Core Approach & Innovation ──────────────────────────────
    pdf.add_page()
    pdf.slide_bg()
    pdf.gold_bar()
    pdf.heading("Core Approach & Innovation")
    pdf.subheading("What makes CONCORD different from a standard chatbot?")

    # Left column
    pdf.section_label("The Problem", 20, 52)
    pdf.bullet("Enterprise knowledge is scattered across HR, Finance, Legal,", 24, 62, width=125)
    pdf.bullet("Privacy, and Customer Support silos. A naive LLM has no", 24, 69, width=125)
    pdf.bullet("access control, hallucinates, and can't detect policy conflicts.", 24, 76, width=125)

    pdf.section_label("Our Solution: Trust Layer Architecture", 20, 92)
    bullets_left = [
        ("1. Permission-Aware RAG: ", "6 personas, domain-level RBAC, access-level filtering."),
        ("2. Policy Conflict Radar: ", "Auto-detects contradictions across 3 known cross-doc conflicts."),
        ("3. Self-Verifying Pipeline: ", "Router -> Specialist -> Verifier chain with confidence scoring."),
        ("4. Output Contracts: ", "JSON/XML/Email/Excel with schema validation before display."),
        ("5. Red-Team Eval Suite: ", "48 tests: injection attacks, data leakage, factual faithfulness."),
    ]
    y = 104
    for bold, rest in bullets_left:
        pdf.bullet(rest, 24, y, bold_part=bold, width=125)
        y += 14

    # Right column
    pdf.section_label("Key Innovation", 160, 52)
    innovations = [
        "Multi-agent pipeline where NO unverified",
        "text reaches the user. The Verifier agent",
        "fact-checks every claim against source",
        "documents and assigns a confidence score.",
        "",
        "Sustainability-first: model routing sends",
        "simple queries to smaller models, caching",
        "avoids redundant API calls, and a live",
        "carbon/energy counter tracks savings.",
        "",
        "Continuous improvement loop: thumbs",
        "up/down feedback on every answer feeds",
        "into a JSONL dataset for future RLHF.",
    ]
    y = 62
    for line in innovations:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(180, 180, 200)
        pdf.set_xy(164, y)
        pdf.cell(120, 7, line)
        y += 7

    pdf.slide_number(2)

    # ── SLIDE 3: Architecture & Tech Stack ───────────────────────────────
    pdf.add_page()
    pdf.slide_bg()
    pdf.gold_bar()
    pdf.heading("System Architecture & Tech Stack")

    # Pipeline flow
    pdf.section_label("9-Step Agent Pipeline", 20, 48)

    steps = [
        "User Query",
        "Injection\nDetector",
        "Query\nRewriter",
        "Router",
        "Hybrid\nRetriever",
        "Domain\nSpecialist",
        "Verifier",
        "Response\nGuard",
        "Formatter",
    ]
    x_start = 16
    box_w = 28
    gap = 3
    for i, step in enumerate(steps):
        x = x_start + i * (box_w + gap)
        # Box
        pdf.set_fill_color(35, 35, 55)
        pdf.set_draw_color(196, 164, 105)
        pdf.rect(x, 60, box_w, 22, "DF")
        # Arrow
        if i < len(steps) - 1:
            ax = x + box_w
            pdf.set_fill_color(196, 164, 105)
            pdf.set_draw_color(196, 164, 105)
            pdf.line(ax, 71, ax + gap, 71)
        # Label
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(230, 230, 245)
        lines = step.split("\n")
        for j, ln in enumerate(lines):
            pdf.set_xy(x, 64 + j * 7)
            pdf.cell(box_w, 7, ln, align="C")

    # Step number labels
    pdf.set_font("Helvetica", "", 6)
    pdf.set_text_color(196, 164, 105)
    for i in range(9):
        x = x_start + i * (box_w + gap)
        pdf.set_xy(x, 56)
        pdf.cell(box_w, 5, f"Step {i}", align="C")

    # Tech stack - left
    pdf.section_label("Tech Stack", 20, 92)
    tech_left = [
        ("Frontend: ", "Streamlit 1.64 with streaming (st.write_stream)"),
        ("LLM: ", "Groq API + Qwen 3.8-27B (OpenAI-compatible)"),
        ("Embeddings: ", "all-MiniLM-L6-v2 (sentence-transformers)"),
        ("Vector DB: ", "ChromaDB with BM25 hybrid retrieval"),
        ("Language: ", "Python 3.13"),
    ]
    y = 104
    for bold, rest in tech_left:
        pdf.bullet(rest, 24, y, bold_part=bold, width=125)
        y += 10

    # Features - right
    pdf.section_label("Security & Trust Features", 160, 92)
    tech_right = [
        ("RBAC: ", "6 roles x 5 domains x 4 access levels"),
        ("Injection Defense: ", "Regex + heuristic prompt guard"),
        ("Verification: ", "LLM-as-judge fact-checking"),
        ("Eval Suite: ", "48 automated tests (38 golden + 10 adversarial)"),
        ("Feedback: ", "JSONL logging with satisfaction metrics"),
    ]
    y = 104
    for bold, rest in tech_right:
        pdf.bullet(rest, 164, y, bold_part=bold, width=120)
        y += 10

    # Data
    pdf.section_label("Knowledge Base", 20, 160)
    pdf.bullet("5 synthetic Kohler policy documents (HR, Finance, Customer Support, Privacy, Legal)", 24, 172, width=250)
    pdf.bullet("3 intentional cross-document conflicts for conflict detection testing", 24, 180, width=250)

    pdf.slide_number(3)

    # ── SLIDE 4: Innovation Pitch & Impact ───────────────────────────────
    pdf.add_page()
    pdf.slide_bg()
    pdf.gold_bar()
    pdf.heading("Innovation Pitch & Business Impact")

    # Left: Why this matters
    pdf.section_label("Why This Matters for Kohler", 20, 48)
    why_items = [
        "Employees get instant, verified answers from company policies",
        "HR, Finance, Legal data stays siloed - no cross-role leakage",
        "Customers see water-saving & sustainability highlights naturally",
        "Policy conflicts are surfaced proactively, not discovered in audits",
        "Every answer is traceable: citations, confidence, source documents",
    ]
    y = 60
    for item in why_items:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(196, 164, 105)
        pdf.set_xy(22, y)
        pdf.cell(5, 7, ">")
        pdf.set_text_color(200, 200, 215)
        pdf.set_xy(28, y)
        pdf.cell(130, 7, item)
        y += 11

    # Right: Metrics
    pdf.section_label("Key Metrics", 160, 48)

    metrics = [
        ("0%", "Data Leakage Rate"),
        ("48", "Automated Test Cases"),
        ("32/32", "Smoke Tests Passing"),
        ("6", "Role-Based Personas"),
        ("3", "Detected Policy Conflicts"),
    ]
    y = 62
    for val, label in metrics:
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(196, 164, 105)
        pdf.set_xy(164, y)
        pdf.cell(30, 10, val)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(180, 180, 200)
        pdf.set_xy(198, y + 2)
        pdf.cell(80, 7, label)
        y += 16

    # Bottom: Sustainability
    pdf.section_label("Sustainability & Efficiency", 20, 132)
    sus_items = [
        "Live token counter tracks API usage and estimated energy/CO2 savings",
        "Smart model routing: simple queries use smaller models, saving compute",
        "Response caching prevents redundant LLM calls for repeated questions",
        "Customer Support answers naturally highlight WaterSense(R) and water-saving features",
    ]
    y = 144
    for item in sus_items:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(130, 200, 130)
        pdf.set_xy(22, y)
        pdf.cell(5, 7, ">")
        pdf.set_text_color(180, 180, 200)
        pdf.set_xy(28, y)
        pdf.cell(250, 7, item)
        y += 10

    # Footer
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(196, 164, 105)
    pdf.set_xy(20, 186)
    pdf.cell(257, 10, "KOHLER CONCORD - Where Enterprise AI Meets Trust", align="C")

    pdf.slide_number(4)

    # Save
    pdf.output("KOHLER_CONCORD_Deck.pdf")
    print("Generated: KOHLER_CONCORD_Deck.pdf")


if __name__ == "__main__":
    build_deck()
