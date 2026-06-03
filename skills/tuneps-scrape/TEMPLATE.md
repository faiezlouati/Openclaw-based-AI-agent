# Tender Analysis Templates
## Persistent configuration for CCAP and CCTP analysis
## Used by build_cctp_docx.py and build_ccap_docx.py

---

## CCAP — Cahier des Charges Administratives (Administrative Tender Document)

### Source document
- File: `offres/documents/<ref>/ccap.pdf` (or `.txt` / scanned text)
- Language: Arabic (original) — translate key sections to English for analysis

### Analysis Sections (8 sections)

#### Section 1 — Document Overview
Fields extracted:
- Authority (buyer)
- Project name and reference number
- Tender number (N° X/DIV/YYYY)
- Document type = CCAP
- Original language
- Currency
- Bid validity period
- Temporary guarantee amount and form

#### Section 2 — Participation Conditions
- Article 2: Scope (number of lots, single/multiple, partial bid allowed?)
- Article 3: Eligibility conditions (professional, technical, financial)
- Article 4: Access to documents (TUNEPS portal reference)

#### Section 3 — Bid Components
Three sub-tables:
- 3.1 Financial Offer: documents required, signing/stamping requirements
- 3.2 Technical Offer: documents required (CCTP, technical forms, data sheets)
- 3.3 Administrative Documents: complete list with requirements

#### Section 4 — Financial Guarantee (Article governing guarantee)
Table with fields:
- Amount (TND)
- Form (bank guarantee / solidarity undertaking)
- Validity requirement
- Release conditions (per category of bidder)
- Seizure conditions (when guarantee is confiscated)

#### Section 5 — Submission Rules
- Online vs offline submission requirements
- Late submission rule (automatic rejection)
- Modification rules during submission window
- Oversized document handling (out-of-line submission)
- Registration requirement in TUNEPS

#### Section 6 — Evaluation
- Evaluation method (Moins-disant = lowest price wins, or weighted criteria)
- Stages of evaluation (administrative → technical → financial)
- Currency conversion rules (BCT rate on opening date)

#### Section 7 — Key Risks & Observations
Risk table with columns: #, Risk / Observation, Severity
Severity levels: 🔴 High | 🟡 Medium | 🟢 Low | 🟢 Positive
Typical risks:
- Validity period length
- Partial bid restrictions
- Guarantee amount vs project value ratio
- Out-of-line submission complexity
- Evaluation transparency
- Currency/authorization requirements

#### Section 8 — Currency & Language
- Accepted languages (Arabic / French / English)
- Currency rules (TND, foreign currency with BCT authorization)
- Exchange rate reference date

---

## CCTP — Cahier des Charges Techniques (Technical Specifications Document)

### Source document
- File: `offres/documents/<ref>/cctp.txt` (or extracted from PDF)
- Language: French (original)

### Analysis Sections (5 sections)

#### Section 1 — Project Overview
Fields extracted:
- Client / Buyer
- Project object
- Budget (if disclosed)
- Project type (AO ouvert / restreint / etc.)
- Timeline if mentioned

#### Section 2 — Items Summary
Table with columns: #, Item description, Quantity, Unit, Type (Hardware/Software/Service)
List all 8+ line items from the CCTP
Categorize by type

#### Section 3 — Technical Requirements by Item
For each major item:
- Technical specifications (exact values, brand names if specified, performance thresholds)
- Compliance requirements (must meet / exceed)
- Testing/acceptance criteria if mentioned

#### Section 4 — Main Technical Risks
Risk table with columns: #, Risk Description, Impact, Mitigation/Note
Severity: 🔴 High | 🟡 Medium | 🟢 Low
Typical risks:
- Over-specification limiting competition
- Ambiguous requirements
- Integration complexity
- Acceptance criteria too strict or unclear
- Single-brand lock-in risk
- Timeline compression

#### Section 5 — Relevance Synthesis
Overall assessment:
- Market competitiveness (good competition / limited bidders)
- Technical clarity (clear / partially defined / ambiguous)
- Compliance burden (high / medium / low)
- Recommendation note (positive / neutral / caution)

---

## Document Generation Rules

### Output file naming
- CCAP: `offres/analyses/<ref>/CCAP_Analysis_<ref>.docx`
- CCTP: `offres/analyses/<ref>/CCTP_Analysis_<ref>.docx`

### Color palette (Word document styling)
| Element | Hex Color |
|---------|-----------|
| Header background | #1F3864 (Navy) |
| Header text | #FFFFFF (White) |
| Section heading band | #1F3864 (Navy) |
| Accent / subtitles | #2E75B6 (Blue) |
| High risk indicator | #C00000 (Red) |
| Medium risk indicator | #FF6600 (Orange) |
| Low/Positive indicator | #375623 (Green) |
| Body text | #404040 (Grey) |
| Table alternate row | #BDD7EE (Light Blue) |

### Document formatting rules
- Page margins: top/bottom 1.5cm, left/right 1.8cm
- Body font size: 9pt
- Header font size: 14pt (document title), 10pt (section headings)
- Table header rows: repeat on page break (`<w:tblHeader/>` row property)
- Section headings: navy background, white bold text, 0.5 line spacing after
- Tables: grid style, 60 dxa cell margins
- Footer: document type, tender ref, "Generated by Tuneps Analyst" (8pt grey italic centered)

### Page limit
- Maximum 4 pages per document
- Sections may be condensed if content exceeds limit

### What NOT to include
- No budget estimates
- No vendor recommendations
- No CCAP risks in CCTP document (and vice versa)
- No architectural diagrams

---

## Workflow for analyzing a new tender

1. **Receive** raw documents (PDF/text) for the tender
2. **Identify** tender reference from filename or TUNEPS metadata
3. **Determine** document type: CCAP (administrative) or CCTP (technical) or both
4. **Copy** source documents to the single storage root:
   - `~/.tuneps_data/documents/<ref>/cctp.pdf` or `cctp.txt`
   - `~/.tuneps_data/documents/<ref>/ccap.pdf` or `ccap.txt`
5. **Run RFP/RAG analysis**:
   - `python3 ~/.openclaw/workspace/skills/rag-analyse/scripts/rag_analyse.py <ref> <doc_path> <doc_type>`
6. **Generate** CCAP analysis if administrative document available:
   - Read and translate key sections
   - Populate 8-section template
   - Output to `~/.tuneps_data/analyses/<ref>/`
7. **Generate** CCTP analysis if technical document available:
   - Read technical specifications
   - Populate 5-section template
   - Output to `~/.tuneps_data/analyses/<ref>/`
8. **Update** display in Tuneps scan to show document and analysis status for that tender ref

---

## File locations
- Analysis templates: `~/.openclaw/workspace/skills/tuneps-scrape/TEMPLATE.md` (this file)
- CCAP generator: `~/.openclaw/workspace/skills/tuneps-scrape/scripts/build_ccap_docx.py`
- CCTP generator: `~/.openclaw/workspace/skills/tuneps-scrape/scripts/build_cctp_docx.py`
- Tender documents: `~/.tuneps_data/documents/<ref>/`
- Analysis outputs: `~/.tuneps_data/analyses/<ref>/`
- Database: `~/.tuneps_data/db/tenders.db`
- RFP pipeline code: `~/.openclaw/workspace/rfp-pipeline/`
- RFP pipeline data/state: `~/.tuneps_data/rfp-pipeline/`