"""
report_generator.py
--------------------
Generates a professional PDF analysis report using ReportLab, summarizing:
    - Executive summary (counts + health score)
    - Conflicts
    - Redundancies
    - Staleness findings
    - Recommendations
"""

import io
from datetime import datetime
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from detector.conflict import Conflict
from detector.redundancy import Redundancy
from detector.stale import StaleFinding


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            fontSize=22,
            leading=26,
            spaceAfter=6,
            textColor=colors.HexColor("#0d2b4e"),
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            fontSize=15,
            leading=18,
            spaceBefore=18,
            spaceAfter=8,
            textColor=colors.HexColor("#0d2b4e"),
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubText",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#555555"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            fontSize=9.5,
            leading=13,
        )
    )
    return styles


def _health_score(total_statements: int, conflicts: int, redundancies: int, stale_docs: int, total_docs: int) -> int:
    """Compute a 0-100 overall policy health score."""
    if total_statements == 0 and total_docs == 0:
        return 100

    score = 100.0
    score -= min(conflicts * 8, 40)
    score -= min(redundancies * 4, 20)
    if total_docs > 0:
        stale_ratio = stale_docs / total_docs
        score -= stale_ratio * 30
    return max(0, round(score))


def generate_pdf_report(
    documents: List,
    conflicts: List[Conflict],
    redundancies: List[Redundancy],
    stale_findings: List[StaleFinding],
) -> bytes:
    """Generate the full PDF report as raw bytes.

    Args:
        documents: List of parsed PolicyDocument objects.
        conflicts: List of Conflict objects.
        redundancies: List of Redundancy objects.
        stale_findings: List of StaleFinding objects.

    Returns:
        Raw PDF file bytes, ready to be sent as a Flask response or saved
        to disk.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title="Policy Conflict & Staleness Report",
    )
    styles = _build_styles()
    story = []

    total_statements = sum(len(d.statements) for d in documents)
    stale_docs = sum(1 for f in stale_findings if f.is_stale)
    health = _health_score(total_statements, len(conflicts), len(redundancies), stale_docs, len(documents))

    # --- Title ---
    story.append(Paragraph("Policy Conflict &amp; Staleness Detector", styles["ReportTitle"]))
    story.append(
        Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            styles["SubText"],
        )
    )
    story.append(Spacer(1, 0.25 * inch))

    # --- Executive Summary ---
    story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
    summary_data = [
        ["Metric", "Value"],
        ["Policy Documents Analyzed", str(len(documents))],
        ["Total Obligation Statements", str(total_statements)],
        ["Conflicts Detected", str(len(conflicts))],
        ["Redundant Statement Pairs", str(len(redundancies))],
        ["Stale Documents", str(stale_docs)],
        ["Overall Health Score", f"{health} / 100"],
    ]
    summary_table = Table(summary_data, colWidths=[3.2 * inch, 2.5 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d2b4e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    # --- Conflicts ---
    story.append(Paragraph(f"Conflicts Detected ({len(conflicts)})", styles["SectionHeading"]))
    if not conflicts:
        story.append(Paragraph("No conflicting policy statements were detected.", styles["BodySmall"]))
    else:
        for i, c in enumerate(conflicts, start=1):
            story.append(
                Paragraph(
                    f"<b>{i}. Topic:</b> {c.topic} &nbsp;&nbsp; <b>Action:</b> {c.action} "
                    f"&nbsp;&nbsp; <b>Severity:</b> {c.severity}",
                    styles["BodySmall"],
                )
            )
            story.append(
                Paragraph(
                    f"&bull; [{c.statement_a.source_file}] {c.statement_a.text}",
                    styles["BodySmall"],
                )
            )
            story.append(
                Paragraph(
                    f"&bull; [{c.statement_b.source_file}] {c.statement_b.text}",
                    styles["BodySmall"],
                )
            )
            story.append(Spacer(1, 0.12 * inch))

    story.append(Spacer(1, 0.15 * inch))

    # --- Redundancies ---
    story.append(Paragraph(f"Redundant Statements ({len(redundancies)})", styles["SectionHeading"]))
    if not redundancies:
        story.append(Paragraph("No redundant policy statements were detected.", styles["BodySmall"]))
    else:
        for i, r in enumerate(redundancies, start=1):
            story.append(
                Paragraph(
                    f"<b>{i}. Topic:</b> {r.topic} &nbsp;&nbsp; <b>Action:</b> {r.action} "
                    f"&nbsp;&nbsp; <b>Cross-document:</b> {'Yes' if r.cross_document else 'No'}",
                    styles["BodySmall"],
                )
            )
            story.append(
                Paragraph(
                    f"&bull; [{r.statement_a.source_file}] {r.statement_a.text}",
                    styles["BodySmall"],
                )
            )
            story.append(
                Paragraph(
                    f"&bull; [{r.statement_b.source_file}] {r.statement_b.text}",
                    styles["BodySmall"],
                )
            )
            story.append(Spacer(1, 0.12 * inch))

    story.append(PageBreak())

    # --- Staleness ---
    stale_only = [f for f in stale_findings if f.is_stale]
    story.append(Paragraph(f"Stale / Outdated Policies ({len(stale_only)})", styles["SectionHeading"]))
    if not stale_only:
        story.append(Paragraph("No stale policy documents were detected.", styles["BodySmall"]))
    else:
        for i, f in enumerate(stale_only, start=1):
            reasons = "; ".join(f.reasons)
            story.append(
                Paragraph(
                    f"<b>{i}. {f.document_title}</b> ({f.source_file})",
                    styles["BodySmall"],
                )
            )
            story.append(Paragraph(f"Reasons: {reasons}", styles["BodySmall"]))
            story.append(Spacer(1, 0.1 * inch))

    story.append(Spacer(1, 0.2 * inch))

    # --- Recommendations ---
    story.append(Paragraph("Recommendations", styles["SectionHeading"]))
    recommendations = []
    if conflicts:
        recommendations.append(
            "Resolve all detected conflicts by assigning a single policy owner "
            "per topic/action pair and deprecating the losing statement."
        )
    if redundancies:
        recommendations.append(
            "Consolidate redundant statements into a single authoritative "
            "policy document to reduce maintenance overhead and drift risk."
        )
    if stale_only:
        recommendations.append(
            "Schedule an immediate review cycle for all stale documents and "
            "remove references to deprecated technologies (e.g. SSL, TLS 1.0, "
            "SHA-1, MD5, Windows Server 2008/2012)."
        )
    recommendations.append(
        "Establish a recurring policy review cadence of no more than 12 months "
        "to prevent future staleness."
    )
    recommendations.append(
        "Adopt a centralized policy repository with topic tagging to make "
        "future conflict and redundancy detection continuous rather than ad hoc."
    )

    for rec in recommendations:
        story.append(Paragraph(f"&bull; {rec}", styles["BodySmall"]))
        story.append(Spacer(1, 0.06 * inch))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
