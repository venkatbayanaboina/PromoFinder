#!/usr/bin/env python3
"""Render doc/solution.md into a clean 2-page PDF using reportlab."""
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                HRFlowable)

SRC = Path("doc/solution.md")
OUT = Path("doc/solution.pdf")

styles = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=15,
                            leading=18, spaceAfter=4),
    "meta": ParagraphStyle("meta", fontName="Helvetica-Oblique", fontSize=8.5,
                           leading=11, textColor="#555555", spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11,
                         leading=13, spaceBefore=8, spaceAfter=3),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.7,
                           leading=11.6, alignment=TA_LEFT, spaceAfter=3),
    "li": ParagraphStyle("li", fontName="Helvetica", fontSize=8.7,
                         leading=11.6, leftIndent=10, spaceAfter=2),
}

def esc(t: str) -> str:
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)
    t = t.replace("`", "")
    return t

story = []
lines = SRC.read_text(encoding="utf-8").splitlines()
# group consecutive non-blank lines into blocks so **bold** spanning wrapped
# lines converts correctly; headings and list items always stand alone
def starts_block(line: str) -> bool:
    return bool(re.match(r"^(# |## |\d+\. )", line))

blocks, cur = [], []
for line in lines:
    if not line.strip():
        if cur:
            blocks.append(cur)
            cur = []
        continue
    if line.startswith(("# ", "## ")):          # headings are standalone
        if cur:
            blocks.append(cur)
            cur = []
        blocks.append([line.rstrip()])
    elif starts_block(line):                     # list item + its continuations
        if cur:
            blocks.append(cur)
        cur = [line.rstrip()]
    else:
        cur.append(line.rstrip())
if cur:
    blocks.append(cur)

for block in blocks:
    first = block[0]
    text = " ".join(block)
    if first.startswith("# "):
        story.append(Paragraph(esc(text[2:]), styles["title"]))
    elif first.startswith("## "):
        story.append(HRFlowable(width="100%", thickness=0.6, color="#999999",
                                spaceBefore=4, spaceAfter=3))
        story.append(Paragraph(esc(text[3:]), styles["h2"]))
    elif re.match(r"^\d+\. ", text):
        story.append(Paragraph(esc(text), styles["li"]))
    elif text.startswith("**Problem chosen"):
        story.append(Paragraph(esc(text), styles["meta"]))
    else:
        story.append(Paragraph(esc(text), styles["body"]))

doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                        leftMargin=18*mm, rightMargin=18*mm,
                        topMargin=14*mm, bottomMargin=14*mm,
                        title="Promo Finder - Kuku AI Generalist Assignment")
doc.build(story)
print(f"wrote {OUT}")
