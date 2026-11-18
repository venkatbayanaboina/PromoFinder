#!/usr/bin/env python3
"""Render the concise Kuku Problem 1 solution document as a two-page PDF."""
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer


SOURCE = Path("doc/solution.md")
OUTPUTS = (
    Path("doc/solution.pdf"),
    Path("output/pdf/PromoFinder_Kuku_Solution.pdf"),
)

INK = colors.HexColor("#17233D")
MUTED = colors.HexColor("#5C6984")
CYAN = colors.HexColor("#087E8B")
VIOLET = colors.HexColor("#5B4B9A")
RULE = colors.HexColor("#B8C5D9")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=20, leading=23, textColor=INK, spaceAfter=3,
))
styles.add(ParagraphStyle(
    "ReportMeta", parent=styles["Normal"], fontName="Helvetica-Bold",
    fontSize=8.3, leading=10.2, textColor=CYAN, spaceAfter=7,
))
styles.add(ParagraphStyle(
    "Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=10.2, leading=12.3, textColor=VIOLET,
    spaceBefore=6, spaceAfter=2, keepWithNext=True,
))
styles.add(ParagraphStyle(
    "Body", parent=styles["Normal"], fontName="Helvetica",
    fontSize=8.15, leading=10.25, textColor=INK,
    alignment=TA_LEFT, spaceAfter=3,
))
styles.add(ParagraphStyle(
    "ReportBullet", parent=styles["Normal"], fontName="Helvetica",
    fontSize=8.05, leading=10.05, textColor=INK,
    leftIndent=10, firstLineIndent=-8, spaceAfter=1.2,
))
styles.add(ParagraphStyle(
    "ReportNumber", parent=styles["Normal"], fontName="Helvetica",
    fontSize=8.05, leading=10.05, textColor=INK,
    leftIndent=12, firstLineIndent=-10, spaceAfter=1.3,
))


def markup(text: str) -> str:
    """Escape body text, then restore the small Markdown subset used in the source."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font name="Helvetica-Oblique">\1</font>', text)
    return text


def source_blocks(lines):
    """Keep headings and list items separate while joining wrapped paragraphs."""
    blocks, current = [], []
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            if current:
                blocks.append(current)
                current = []
            continue
        special = (
            line == "<!-- PAGEBREAK -->"
            or line.startswith(("# ", "## ", "- "))
            or bool(re.match(r"^\d+\. ", line))
        )
        if special:
            if current:
                blocks.append(current)
                current = []
            blocks.append([line])
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def build_story() -> list:
    story = []
    for block in source_blocks(SOURCE.read_text(encoding="utf-8").splitlines()):
        first = block[0]
        content = " ".join(block)
        if first == "<!-- PAGEBREAK -->":
            story.append(PageBreak())
        elif first.startswith("# "):
            story.append(Paragraph(markup(first[2:]), styles["ReportTitle"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=CYAN,
                                    spaceBefore=1, spaceAfter=5))
        elif first.startswith("**"):
            story.append(Paragraph(markup(content), styles["ReportMeta"]))
        elif first.startswith("## "):
            story.append(Paragraph(markup(first[3:]), styles["Section"]))
        elif first.startswith("- "):
            story.append(Paragraph("&bull; " + markup(first[2:]), styles["ReportBullet"]))
        elif re.match(r"^\d+\. ", first):
            story.append(Paragraph(markup(first), styles["ReportNumber"]))
        else:
            story.append(Paragraph(markup(content), styles["Body"]))
    story.append(Spacer(1, 1))
    return story


def footer(canvas, document):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(15 * mm, 11.5 * mm, width - 15 * mm, 11.5 * mm)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(15 * mm, 7.5 * mm, "Kuku AI Generalist Assignment | PromoFinder")
    canvas.drawRightString(width - 15 * mm, 7.5 * mm, "Page {} of 2".format(document.page))
    canvas.restoreState()


def render(output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=13 * mm, bottomMargin=16 * mm,
        title="PromoFinder - Kuku AI Generalist Assignment",
        author="PromoFinder prototype",
    )
    document.build(build_story(), onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    for destination in OUTPUTS:
        render(destination)
        print("wrote {}".format(destination))
