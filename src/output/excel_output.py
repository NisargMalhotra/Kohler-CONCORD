"""
KOHLER CONCORD — Enterprise Excel Report Generator.

Produces a multi-sheet, styled Excel workbook with:
  - Executive Summary (metrics, sustainability, chart)
  - Detailed Response Data (with conditional formatting)
  - Citations & Sources
  - Conflict Radar
"""

import os
import time
import logging
from typing import Optional

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    PatternFill,
    Side,
)
from openpyxl.utils import get_column_letter

from src.config import VerifiedAnswer, FormatSpec, FormattedOutput, settings
from src.llm import efficiency_stats

logger = logging.getLogger(__name__)

# ── Styles ────────────────────────────────────────────────────────────────────

_KOHLER_BLACK = "000000"
_KOHLER_BLUE = "004B87"
_WHITE = "FFFFFF"
_LIGHT_GREEN = "E2EFDA"
_LIGHT_RED = "FCE4EC"
_LIGHT_YELLOW = "FFF9C4"

_HEADER_FONT = Font(bold=True, color=_WHITE, size=11)
_HEADER_FILL = PatternFill(start_color=_KOHLER_BLACK, end_color=_KOHLER_BLACK, fill_type="solid")
_TITLE_FONT = Font(bold=True, size=14, color=_KOHLER_BLUE)
_METRIC_LABEL_FONT = Font(bold=True, size=10)
_METRIC_VALUE_FONT = Font(size=10)
_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
_GREEN_FILL = PatternFill(start_color=_LIGHT_GREEN, end_color=_LIGHT_GREEN, fill_type="solid")
_RED_FILL = PatternFill(start_color=_LIGHT_RED, end_color=_LIGHT_RED, fill_type="solid")
_YELLOW_FILL = PatternFill(start_color=_LIGHT_YELLOW, end_color=_LIGHT_YELLOW, fill_type="solid")
_WRAP = Alignment(wrap_text=True, vertical="top")
_CENTER = Alignment(horizontal="center", vertical="center")


def _auto_width(ws, min_width: int = 12, max_width: int = 50) -> None:
    """Auto-adjust column widths based on content."""
    for col_cells in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col_cells[0].column)
        for cell in col_cells:
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except Exception:
                pass
        adjusted = min(max(max_len + 4, min_width), max_width)
        ws.column_dimensions[col_letter].width = adjusted


def _apply_header_row(ws, headers: list, row: int = 1) -> None:
    """Style a header row with Kohler black background."""
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _CENTER
        cell.border = _BORDER


# ── Main generator ────────────────────────────────────────────────────────────


def format_excel(answer: VerifiedAnswer, spec: FormatSpec) -> FormattedOutput:
    """Generate an enterprise-grade Excel report."""
    wb = Workbook()

    # ── Sheet 1: Executive Summary ────────────────────────────────────
    ws_sum = wb.active
    ws_sum.title = "Executive Summary"
    ws_sum.sheet_properties.tabColor = _KOHLER_BLUE

    ws_sum.cell(row=1, column=1, value="KOHLER CONCORD — AI Analysis Report").font = _TITLE_FONT
    ws_sum.merge_cells("A1:D1")
    ws_sum.cell(row=2, column=1, value=f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}").font = Font(italic=True, size=9)

    # Metrics block
    total_queries = efficiency_stats.cache_hits + efficiency_stats.cache_misses
    cache_rate = efficiency_stats.cache_hits / max(total_queries, 1)
    citation_count = len(answer.citations)
    has_citations = citation_count > 0

    metrics = [
        ("Confidence Score", f"{answer.confidence:.0%}"),
        ("Citations Found", str(citation_count)),
        ("Domains Analysed", ", ".join(answer.domains_used) if answer.domains_used else "—"),
        ("Conflicts Detected", str(len(answer.conflicts))),
        ("", ""),  # spacer
        ("— Sustainability Metrics —", ""),
        ("Total Tokens Used", f"{efficiency_stats.total_tokens_used:,}"),
        ("Tokens Saved (Cache)", f"{efficiency_stats.tokens_saved_by_cache:,}"),
        ("Tokens Saved (Routing)", f"{efficiency_stats.tokens_saved_by_routing:,}"),
        ("Cache Hit Rate", f"{cache_rate:.0%}"),
        ("Semantic Cache Hits", str(efficiency_stats.semantic_cache_hits)),
        ("Degraded Responses", str(efficiency_stats.degraded_responses)),
        ("Energy Saved", f"{efficiency_stats.estimated_energy_saved_wh:.4f} Wh"),
        ("CO₂ Saved", f"{efficiency_stats.estimated_co2_saved_g:.4f} g"),
        ("Est. Cost Saved", f"${efficiency_stats.total_tokens_saved * 0.000002:.4f}"),
    ]

    for i, (label, value) in enumerate(metrics, start=4):
        lc = ws_sum.cell(row=i, column=1, value=label)
        vc = ws_sum.cell(row=i, column=2, value=value)
        lc.font = _METRIC_LABEL_FONT
        vc.font = _METRIC_VALUE_FONT
        vc.alignment = Alignment(horizontal="right")

    # Token breakdown bar chart
    chart_data_start = len(metrics) + 6
    ws_sum.cell(row=chart_data_start, column=1, value="Category").font = _HEADER_FONT
    ws_sum.cell(row=chart_data_start, column=1).fill = _HEADER_FILL
    ws_sum.cell(row=chart_data_start, column=2, value="Tokens").font = _HEADER_FONT
    ws_sum.cell(row=chart_data_start, column=2).fill = _HEADER_FILL
    chart_rows = [
        ("Used", efficiency_stats.total_tokens_used),
        ("Saved (Cache)", efficiency_stats.tokens_saved_by_cache),
        ("Saved (Routing)", efficiency_stats.tokens_saved_by_routing),
    ]
    for j, (cat, val) in enumerate(chart_rows, start=chart_data_start + 1):
        ws_sum.cell(row=j, column=1, value=cat)
        ws_sum.cell(row=j, column=2, value=val)

    chart = BarChart()
    chart.type = "col"
    chart.title = "Token Usage Breakdown"
    chart.y_axis.title = "Tokens"
    chart.style = 10
    chart.width = 18
    chart.height = 12
    data_ref = Reference(ws_sum, min_col=2, min_row=chart_data_start, max_row=chart_data_start + len(chart_rows))
    cats_ref = Reference(ws_sum, min_col=1, min_row=chart_data_start + 1, max_row=chart_data_start + len(chart_rows))
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.shape = 4
    ws_sum.add_chart(chart, f"D4")

    ws_sum.column_dimensions["A"].width = 25
    ws_sum.column_dimensions["B"].width = 20

    # ── Sheet 2: Detailed Response ────────────────────────────────────
    ws_detail = wb.create_sheet(title="Response Detail")
    ws_detail.sheet_properties.tabColor = "4472C4"

    detail_headers = ["Answer", "Confidence", "Domains", "Cited Clauses", "Abstains", "Abstention Reason"]
    _apply_header_row(ws_detail, detail_headers)

    cited_ids = ", ".join(c.clause_id for c in answer.citations) if answer.citations else "—"
    domains_str = ", ".join(answer.domains_used) if answer.domains_used else "—"
    row_data = [
        answer.answer,
        answer.confidence,
        domains_str,
        cited_ids,
        "Yes" if answer.should_abstain else "No",
        answer.abstention_reason or "—",
    ]
    for col_idx, val in enumerate(row_data, 1):
        cell = ws_detail.cell(row=2, column=col_idx, value=val)
        cell.border = _BORDER
        cell.alignment = _WRAP

    # Conditional formatting: red if low confidence, green if cache served
    conf_cell = ws_detail.cell(row=2, column=2)
    if answer.confidence < 0.6:
        conf_cell.fill = _RED_FILL
    elif answer.confidence >= 0.8:
        conf_cell.fill = _GREEN_FILL
    else:
        conf_cell.fill = _YELLOW_FILL

    ws_detail.column_dimensions["A"].width = 80
    ws_detail.row_dimensions[2].height = 120
    _auto_width(ws_detail, min_width=15)
    ws_detail.column_dimensions["A"].width = 80  # override for answer column

    # ── Sheet 3: Citations ────────────────────────────────────────────
    ws_cit = wb.create_sheet(title="Citations & Sources")
    ws_cit.sheet_properties.tabColor = "70AD47"
    cit_headers = ["Clause ID", "Source File", "Relevant Text", "Domain"]
    _apply_header_row(ws_cit, cit_headers)
    for i, c in enumerate(answer.citations, start=2):
        ws_cit.cell(row=i, column=1, value=c.clause_id).border = _BORDER
        ws_cit.cell(row=i, column=2, value=c.source_file).border = _BORDER
        cell_text = ws_cit.cell(row=i, column=3, value=c.relevant_text)
        cell_text.border = _BORDER
        cell_text.alignment = _WRAP
        ws_cit.cell(row=i, column=4, value=c.domain).border = _BORDER
    _auto_width(ws_cit)

    # ── Sheet 4: Conflicts ────────────────────────────────────────────
    ws_conf = wb.create_sheet(title="Conflict Radar")
    ws_conf.sheet_properties.tabColor = "FF0000"
    conf_headers = ["Clause A", "Clause B", "Domain A", "Domain B", "Description", "Recommendation", "Severity"]
    _apply_header_row(ws_conf, conf_headers)
    for i, cf in enumerate(answer.conflicts, start=2):
        ws_conf.cell(row=i, column=1, value=cf.clause_a_id).border = _BORDER
        ws_conf.cell(row=i, column=2, value=cf.clause_b_id).border = _BORDER
        ws_conf.cell(row=i, column=3, value=cf.domain_a).border = _BORDER
        ws_conf.cell(row=i, column=4, value=cf.domain_b).border = _BORDER
        desc_cell = ws_conf.cell(row=i, column=5, value=cf.description)
        desc_cell.border = _BORDER
        desc_cell.alignment = _WRAP
        rec_cell = ws_conf.cell(row=i, column=6, value=cf.recommendation)
        rec_cell.border = _BORDER
        rec_cell.alignment = _WRAP
        sev_cell = ws_conf.cell(row=i, column=7, value=cf.severity)
        sev_cell.border = _BORDER
        # Severity color
        if cf.severity == "high":
            sev_cell.fill = _RED_FILL
        elif cf.severity == "medium":
            sev_cell.fill = _YELLOW_FILL
        else:
            sev_cell.fill = _GREEN_FILL
    _auto_width(ws_conf)

    # ── Save ──────────────────────────────────────────────────────────
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    filename = f"Kohler_Report_{int(time.time())}.xlsx"
    filepath = os.path.join(settings.OUTPUT_DIR, filename)

    try:
        wb.save(filepath)
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        return FormattedOutput(
            content=(
                f"📊 **Enterprise Report generated** — {filename}\n"
                f"Contains: Executive Summary, Response Detail, "
                f"{len(answer.citations)} citation(s), "
                f"{len(answer.conflicts)} conflict(s)."
            ),
            format_type="excel",
            validation_passed=True,
            file_path=filepath,
            file_bytes=file_bytes,
        )
    except Exception as e:
        logger.error(f"Failed to generate Excel: {e}")
        return FormattedOutput(
            content="Failed to generate Excel file.",
            format_type="excel",
            validation_passed=False,
            validation_errors=[str(e)],
        )
