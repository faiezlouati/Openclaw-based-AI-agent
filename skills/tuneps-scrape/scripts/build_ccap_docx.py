#!/usr/bin/env python3
"""
build_ccap_docx.py — Generate CCAP (Cahier des Charges Administratives) analysis
as a formatted Word document in English.

Usage: python3 build_ccap_docx.py <tender_ref> <output_dir>
"""

import sys
import re
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Palette ──────────────────────────────────────────────────────────────────
NAVY        = RGBColor(0x1F, 0x38, 0x64)
ACCENT_BLUE = RGBColor(0x2E, 0x75, 0xB6)
HIGH_RED    = RGBColor(0xC0, 0x00, 0x00)
MED_ORANGE  = RGBColor(0xFF, 0x66, 0x00)
LOW_GREEN   = RGBColor(0x37, 0x56, 0x23)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
BODY_GREY   = RGBColor(0x40, 0x40, 0x40)
LIGHT_BLUE  = RGBColor(0xBD, 0xD7, 0xEE)

# ── Helpers ──────────────────────────────────────────────────────────────────
def set_cell_bg(cell, hex_color):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  hex_color)
    tcPr.append(shd)

def set_cell_text(cell, text, bold=False, color=None, size=9, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ''
    p = cell.paragraphs[0]
    p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.color.rgb = color if color else BODY_GREY

def add_table_header(table, headers, bg='1F3864'):
    row = table.rows[0]
    for i, hdr in enumerate(headers):
        cell = row.cells[i]
        set_cell_bg(cell, bg)
        set_cell_text(cell, hdr, bold=True, color=WHITE, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)
    for cell in row.cells:
        for prm in cell._tc.get_or_add_tcPr().iter(qn('w:tcMar')):
            for tag in ['top', 'bottom', 'left', 'right']:
                el = OxmlElement(f'w:{tag}')
                el.set(qn('w:w'),    '60')
                el.set(qn('w:type'), 'dxa')
                prm.append(el)

def add_table_row(table, values, alert=None, alert_map=None):
    row = table.add_row()
    alert_map = alert_map or {'🔴': HIGH_RED, '🟡': MED_ORANGE, '🟢': LOW_GREEN}
    for i, val in enumerate(values):
        cell = row.cells[i]
        color = alert_map.get(alert[i], BODY_GREY) if alert and i == 0 else BODY_GREY
        set_cell_text(cell, val, color=color, size=9)
    for cell in row.cells:
        for prm in cell._tc.get_or_add_tcPr().iter(qn('w:tcMar')):
            for tag in ['top', 'bottom', 'left', 'right']:
                el = OxmlElement(f'w:{tag}')
                el.set(qn('w:w'),    '60')
                el.set(qn('w:type'), 'dxa')
                prm.append(el)

def make_header_section(doc, title, subtitle=None):
    # Coloured heading band
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = NAVY
    if subtitle:
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(subtitle)
        r2.font.size = Pt(10)
        r2.font.color.rgb = ACCENT_BLUE
    doc.add_paragraph('')

def add_section_heading(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = WHITE
    run.font.highlight_color = None
    # shade paragraph background
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  '1F3864')
    pPr.append(shd)
    doc.add_paragraph('')

def add_body(doc, text, bold=False, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(1)
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(9)
    run.font.color.rgb = BODY_GREY

def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Cm(0.5 + level * 0.5)
    run = p.add_run(text)
    run.font.size = Pt(9)
    run.font.color.rgb = BODY_GREY

def add_numbered(doc, text, level=0):
    p = doc.add_paragraph(style='List Number')
    p.paragraph_format.left_indent = Cm(0.5 + level * 0.5)
    run = p.add_run(text)
    run.font.size = Pt(9)
    run.font.color.rgb = BODY_GREY

# ── Main builder ───────────────────────────────────────────────────────────────
def build_ccap_docx(tender_ref, src_md, out_docx):
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin   = Cm(1.8)
        section.right_margin  = Cm(1.8)

    # ── Header band ──
    title = f"CCAP ANALYSIS — {tender_ref}"
    subtitle = "Administrative Tender Document | Ministry of National Defence"
    make_header_section(doc, title, subtitle)

    # ── Section 1: Document Overview ──
    add_section_heading(doc, "1. Document Overview")
    t1 = doc.add_table(rows=1, cols=2)
    t1.style = 'Table Grid'
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    add_table_header(t1, ['Field', 'Detail'])
    rows1 = [
        ('Authority', 'Ministry of National Defence — General Directorate for ICT'),
        ('Project', 'Acquisition and installation of integrated servers'),
        ('Tender Reference', 'N° 06/DIV/2026'),
        ('Document Type', 'Cahier des Charges Administratives (CCAP)'),
        ('Language', 'Arabic (original); English translation'),
        ('Currency', 'Tunisian Dinar (TND)'),
        ('Bid Validity', '120 days from submission deadline'),
        ('Temporary Guarantee', '5,000 TND'),
    ]
    for r in rows1:
        add_table_row(t1, r)
    doc.add_paragraph('')

    # ── Section 2: Participation Conditions ──
    add_section_heading(doc, "2. Participation Conditions")
    add_body(doc, "Article 2 — Scope", bold=True)
    add_bullet(doc, "Single lot consisting of 8 line items")
    add_bullet(doc, "Bidders must submit for the entire lot — partial bids are NOT accepted")
    add_body(doc, "Article 3 — Eligibility", bold=True)
    add_bullet(doc, "Participating suppliers must demonstrate professional, technical, and financial qualifications")
    add_body(doc, "Article 4 — Access to Documents", bold=True)
    add_bullet(doc, "Complete tender package available via TUNEPS online portal upon publication")
    doc.add_paragraph('')

    # ── Section 3: Bid Components ──
    add_section_heading(doc, "3. Bid Components")

    # 3.1 Financial Offer
    add_body(doc, "3.1 Financial Offer", bold=True)
    t3a = doc.add_table(rows=1, cols=2)
    t3a.style = 'Table Grid'
    add_table_header(t3a, ['Document', 'Requirements'])
    add_table_row(t3a, ['Financial Commitment Letter', 'Completed, signed, stamped per Appendix 1 template'])
    add_table_row(t3a, ['Detailed Estimative Invoice', 'Itemized per component, signed and stamped'])
    doc.add_paragraph('')

    # 3.2 Technical Offer
    add_body(doc, "3.2 Technical Offer", bold=True)
    t3b = doc.add_table(rows=1, cols=2)
    t3b.style = 'Table Grid'
    add_table_header(t3b, ['Document', 'Requirements'])
    add_table_row(t3b, ['Signed CCTP', 'Initialed every page; signed and stamped on final page'])
    add_table_row(t3b, ['Technical Bid Forms', 'Completed per templates in technical specifications'])
    add_table_row(t3b, ['Technical Data Sheets', 'Completed per lot item, signed and stamped'])
    doc.add_paragraph('')

    # 3.3 Administrative Documents
    add_body(doc, "3.3 Administrative Documents", bold=True)
    t3c = doc.add_table(rows=1, cols=2)
    t3c.style = 'Table Grid'
    add_table_header(t3c, ['Document', 'Requirements'])
    add_table_row(t3c, ['Temporary Financial Guarantee', 'Bank guarantee or solidarity undertaking; 120-day validity'])
    add_table_row(t3c, ['Declaration of Non-Collusion', 'Sworn statement via TUNEPS portal'])
    add_table_row(t3c, ['Declaration — No Conflict of Interest', 'Sworn statement via TUNEPS portal'])
    add_table_row(t3c, ['Manager Identification Card', 'Civil status card + national ID copy + 2 photos'])
    add_table_row(t3c, ['Company Registry Extract', 'Within 3 months of issue date'])
    doc.add_paragraph('')

    # ── Section 4: Financial Guarantee ──
    add_section_heading(doc, "4. Financial Guarantee (Article 10)")
    t4 = doc.add_table(rows=1, cols=2)
    t4.style = 'Table Grid'
    add_table_header(t4, ['Element', 'Detail'])
    add_table_row(t4, ['Amount', '5,000 TND'])
    add_table_row(t4, ['Form', 'Bank guarantee or solidarity liability undertaking'])
    add_table_row(t4, ['Validity', 'Must cover full bid validity period (minimum 120 days)'])
    add_table_row(t4, ['Release — Non-selected bidders', 'Within 20 days of contract award notification'])
    add_table_row(t4, ['Release — Selected bidder', 'Upon submission of final performance guarantee'])
    add_table_row(t4, ['Release — Automatically rejected', 'Immediate release'])
    add_table_row(t4, ['Seizure — Withdrawal during validity', 'Bid withdrawal after submission deadline'])
    add_table_row(t4, ['Seizure — Contract refusal', 'Selected bidder refuses to sign within deadline'])
    add_table_row(t4, ['Seizure — No final guarantee', 'Selected bidder fails to provide final performance guarantee'])
    doc.add_paragraph('')

    # ── Section 5: Submission Rules ──
    add_section_heading(doc, "5. Submission Rules (Article 8)")
    add_body(doc, "Online Submission (via TUNEPS)", bold=True)
    add_bullet(doc, "Registration in TUNEPS is MANDATORY before the submission deadline")
    add_bullet(doc, "Financial and technical offers submitted via TUNEPS portal")
    add_body(doc, "Late Submissions", bold=True)
    add_bullet(doc, "Bids received or modified after the deadline are AUTOMATICALLY REJECTED — no exceptions")
    add_body(doc, "Modifications", bold=True)
    add_bullet(doc, "Modifications permitted during the submission window")
    add_bullet(doc, "After deadline: no modification, correction, addition, or withdrawal is allowed")
    add_bullet(doc, "Bids containing additions/modifications must identify altered items by signing person")
    add_body(doc, "Oversized Technical Bids", bold=True)
    add_bullet(doc, "If online submission volume is exceeded, remaining technical documents may be sent offline")
    add_bullet(doc, "Offline submission list must be declared in the electronic bid")
    doc.add_paragraph('')

    # ── Section 6: Evaluation ──
    add_section_heading(doc, "6. Evaluation (Article 13)")
    t6 = doc.add_table(rows=1, cols=2)
    t6.style = 'Table Grid'
    add_table_header(t6, ['Phase', 'Activity'])
    add_table_row(t6, ['Stage 1', 'Administrative compliance + financial guarantee verification'])
    add_table_row(t6, ['Stage 2', 'Financial offer correction — arithmetic/material errors corrected; ascending price ranking'])
    add_table_row(t6, ['Stage 3', 'Lowest evaluated compliant bid wins (Moins-disant)'])
    doc.add_paragraph('')

    # ── Section 7: Key Risks ──
    add_section_heading(doc, "7. Key Risks & Observations")
    t7 = doc.add_table(rows=1, cols=3)
    t7.style = 'Table Grid'
    add_table_header(t7, ['#', 'Risk / Observation', 'Severity'])
    risks = [
        ('1', '120-day bid validity is relatively long — bidders must maintain pricing for 4 months', '🟡 Medium'),
        ('2', 'Single-lot / 8 items — no partial bid option increases risk for specialist suppliers', '🔴 High'),
        ('3', '5,000 TND temporary guarantee (0.1% of 5M project) is unusually low — potential budget constraint or risk allocation preference', '🟡 Medium'),
        ('4', 'Out-of-line document submission explicitly permitted — creates administrative complexity', '🟡 Medium'),
        ('5', 'Non-public bid opening session — reduced transparency in evaluation', '🟡 Medium'),
        ('6', 'BCT authorization required for foreign currency bids — procedural burden', '🟢 Low'),
        ('7', '20-day guarantee release for non-selected bidders — reasonable', '🟢 Low'),
        ('8', '7-day cure period for missing documents after opening — unusual, potentially bidder-friendly', '🟢 Positive'),
    ]
    for r in risks:
        add_table_row(t7, r, alert=[r[2][0]] * 3 if r[2] else None)
    doc.add_paragraph('')

    # ── Footer note ──
    p_f = doc.add_paragraph()
    p_f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_f = p_f.add_run(f"CCAP Analysis | Tender Ref: {tender_ref} | Generated by Tuneps Analyst")
    run_f.font.size = Pt(8)
    run_f.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    run_f.italic = True

    doc.save(out_docx)
    print(f"✅ CCAP DOCX saved → {out_docx}")

if __name__ == '__main__':
    tender_ref = sys.argv[1] if len(sys.argv) > 1 else '20260301601'
    out_dir   = Path(sys.argv[2] if len(sys.argv) > 2 else '.').resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_docx  = out_dir / f"CCAP_Analysis_{tender_ref}.docx"
    build_ccap_docx(tender_ref, None, str(out_docx))