# Tuneps Tender Intelligence Agent — Project Documentation

## 1. Introduction

The Tuneps Tender Intelligence Agent is an OpenClaw-based AI assistant designed to monitor Tunisian public procurement opportunities published on the Tuneps platform and identify tenders relevant to ICT infrastructure activities.

The system focuses on opportunities aligned with Huawei Technologies Tunisia-style ICT infrastructure portfolios, including networks, datacenter, servers, storage, cloud infrastructure, cybersecurity, telecom infrastructure, enterprise communication, and related system integration.

The assistant is used mainly through WhatsApp commands, especially `scan tuneps`, and can also provide or analyze locally available RFP documents such as CCTP and CCAP files.

Important limitation: the agent does not currently have Tuneps login/download access. It can scan public listing metadata from Tuneps. Full RFP documents are only available when they have already been stored locally or when the user provides them.

---

## 2. Project Overview

### Project Name
Tuneps Tender Intelligence Agent

### Main Objective
Automatically scan Tuneps public tender listings, filter ICT-relevant opportunities, and support tender analysis through document-based CCTP and CCAP reports.

### Primary User Flow
1. User sends a WhatsApp command such as `scan tuneps`.
2. The assistant parses dates, buyer filters, ministry aliases, and deadline constraints.
3. The scanner queries Tuneps public APIs.
4. The system filters results based on ICT relevance rules.
5. The assistant returns a mobile-friendly tender intelligence report.
6. If local documents exist, the assistant can send CCTP/CCAP files or existing analysis documents.

### Main Components
- OpenClaw assistant runtime
- Tuneps scraping skill
- Node.js Tuneps scanner
- Local RFP document storage
- RFP analysis pipeline
- Huawei-oriented ICT relevance profile
- WhatsApp interface

---

## 3. Business Workflow

### 3.1 Tender Discovery Workflow

1. User requests a scan.
2. Assistant parses the request:
   - Publication date range
   - Buyer / authority filter
   - Deadline filter
   - Ministry nickname mapping
3. Scanner calls Tuneps public listing API.
4. Results are filtered by:
   - Buyer name
   - Publication date
   - Deadline window, if requested
   - ICT infrastructure relevance
5. Relevant tenders are displayed with:
   - Reference number
   - Title
   - Authority
   - Publication date
   - Submission deadline
   - Procedure
   - Evaluation method
   - Consortium permission
   - International/national status
   - Provisional guarantee
   - Tuneps URL

### 3.2 Relevance Filtering Workflow

The system excludes generic IT purchases and focuses on infrastructure-level opportunities.

Relevant scope includes:
- IP networks
- Core routers and switches
- LAN/WAN infrastructure
- Telecom infrastructure
- 4G/5G, radio, microwave, fiber
- Datacenter infrastructure
- Servers and hosting platforms
- Storage and backup
- Virtualization and private cloud
- Cybersecurity platforms
- Firewalls, SIEM, IDS/IPS, anti-DDoS
- Enterprise communication
- AI/HPC computing infrastructure
- System integration for infrastructure projects

Excluded scope includes:
- Standard computers
- Laptops and desktops
- Printers and scanners
- Office software renewals
- Microsoft license renewals without infrastructure scope
- Generic computer equipment
- Office supplies
- Basic maintenance
- Vehicles
- Construction works
- Medical equipment
- Food/catering/cleaning

Important rule: classification must consider business context, not only keywords. For example, radio-communication equipment is telecom infrastructure and should be treated as relevant even when common ICT keywords are absent.

### 3.3 RFP Document Workflow

When documents are locally available:
1. User requests a CCTP or CCAP document.
2. Assistant locates it under `~/.tuneps_data/documents/<ref>/`.
3. Assistant sends only the requested document.

When user asks to analyze a tender:
1. Assistant checks existing analyses under `~/.tuneps_data/analyses/<ref>/`.
2. If analysis documents exist, assistant sends the analysis DOCX files.
3. For Ministry of Defense / Mutuelle de l’Armée Nationale datacenter offer, the established CCTP and CCAP analysis format is used.

---

## 4. Main Features

### 4.1 WhatsApp Command Interface

The user interacts with the assistant directly from WhatsApp.

Examples:
- `scan tuneps`
- `scan tuneps for mod this year`
- `send me cctp document for this offer 20260301601`
- `analyse it`

### 4.2 Tender Scanning

The scanner supports:
- Today’s tenders
- This week
- This month
- This year
- Custom date ranges
- Buyer/authority filters
- Deadline filters
- Cached repeated scans

### 4.3 Ministry Alias Mapping

User-friendly names are mapped to official Tuneps buyer names.

Examples:
- `mod` → `Ministère de la Défense Nationale`
- `défense` → `Ministère de la Défense Nationale`
- `présidence` → `Présidence du Gouvernement`
- `CCK` → `Centre de Calcul El-Khawarizmi`

### 4.4 ICT Relevance Filtering

The profile filter identifies tenders matching the company’s ICT infrastructure scope and excludes generic/non-relevant opportunities.

### 4.5 Public Tuneps Metadata Extraction

The scanner extracts public metadata from Tuneps, including:
- Reference number
- Title
- Authority
- Publication date
- Submission deadline
- Tender procedure
- Evaluation method
- Guarantee information
- Public details URL

### 4.6 Local RFP Document Management

Documents are stored under one unified data root:

```text
~/.tuneps_data/documents/<ref>/
```

Example:

```text
~/.tuneps_data/documents/20260301601/cctp.pdf
~/.tuneps_data/documents/20260301601/ccap.pdf
~/.tuneps_data/documents/20260301601/architecture.jpeg
```

### 4.7 RFP Analysis Output

Analysis files are stored under:

```text
~/.tuneps_data/analyses/<ref>/
```

Example:

```text
~/.tuneps_data/analyses/20260301601/CCTP_Analysis_Mutuelle_Armee_Huawei_Relevance.docx
~/.tuneps_data/analyses/20260301601/CCAP_Analysis_20260301601.docx
```

### 4.8 CCTP Analysis Format

CCTP analysis includes:
1. Extraction and mapping
2. Qualification requirements
3. Technical demand summary
4. Main technical risks
5. Relevance synthesis

For Huawei-relevant infrastructure tenders, the report explicitly states that the offer is top relevant for Huawei when supported by the technical scope.

### 4.9 CCAP Analysis Format

CCAP analysis includes:
1. Document overview
2. Participation conditions
3. Bid components
4. Financial guarantee
5. Submission rules
6. Evaluation
7. Key risks and observations

### 4.10 Decision-Support Language

The assistant must not present the final participation decision as a final bid/no-bid decision. Reports should support decision-making by describing relevance, fit, risks, constraints, and validation points.

---

## 5. System Architecture

### 5.1 High-Level Architecture

```text
WhatsApp User
   |
   v
OpenClaw Assistant Runtime
   |
   v
Tuneps Skill: tuneps-scrape
   |
   v
Node.js Scanner: scripts/tuneps.js
   |
   v
Tuneps Public API
   |
   v
Filtering + Report Rendering
   |
   v
WhatsApp Report Response
```

### 5.2 RFP Analysis Architecture

```text
Local RFP Documents
   |
   v
Parse Documents
   |
   v
Clean Markdown
   |
   v
Chunk Content
   |
   v
Generate Embeddings
   |
   v
Store/Retrieve with ChromaDB
   |
   v
LLM Analysis
   |
   v
DOCX / JSON / HTML / Markdown Outputs
```

### 5.3 Main Runtime Paths

Code and skills:

```text
~/.openclaw/workspace/
```

Tuneps scanner:

```text
~/.openclaw/workspace/skills/tuneps-scrape/
```

RFP pipeline code:

```text
~/.openclaw/workspace/rfp-pipeline/
```

Tender data:

```text
~/.tuneps_data/
```

---

## 6. Technologies Used

### Runtime and Automation
- OpenClaw
- WhatsApp integration through OpenClaw messaging runtime
- macOS host environment

### Tuneps Scanner
- Node.js
- JavaScript
- HTTPS requests
- dotenv
- Tuneps public API endpoints

### AI / LLM Components
- Groq API support in scanner and RFP pipeline
- OpenClaw model for contextual review when needed
- Huawei-oriented ICT profile rules

### RFP Pipeline
- Python
- Docling
- PyMuPDF
- Mistral API support for optional image/diagram OCR
- ftfy
- sentence-transformers
- ChromaDB
- Groq LLM API support

### Document Outputs
- PDF
- DOCX
- Markdown
- JSON
- HTML

---

## 7. Installation & Deployment

### 7.1 Prerequisites

Required:
- macOS/Linux/Windows host
- Node.js 22+ recommended
- Python 3.10+ for RFP pipeline
- OpenClaw installed and configured
- WhatsApp channel configured in OpenClaw

Optional:
- Mistral API key for diagram/image OCR
- Groq API key for LLM filtering/analysis
- LibreOffice or Microsoft Word for legacy document conversion

### 7.2 Clone Repository

```bash
git clone https://github.com/faiezlouati/Openclaw-based-AI-agent.git
cd Openclaw-based-AI-agent
```

### 7.3 Install Tuneps Scanner Dependencies

```bash
cd ~/.openclaw/workspace/skills/tuneps-scrape
npm install
```

### 7.4 Configure Environment

Create or update:

```text
~/.openclaw/workspace/skills/tuneps-scrape/.env
```

Required only if LLM-based filtering/translation is used:

```env
GROQ_API_KEY=your_key_here
```

Do not commit `.env` files.

### 7.5 Install RFP Pipeline Dependencies

```bash
cd ~/.openclaw/workspace/rfp-pipeline
python3 -m venv ~/.tuneps_data/rfp-pipeline/venv
source ~/.tuneps_data/rfp-pipeline/venv/bin/activate
pip install -r requirements.txt
```

### 7.6 Data Directory Setup

Use exactly one data root:

```text
~/.tuneps_data/
```

Recommended directories:

```bash
mkdir -p ~/.tuneps_data/documents
mkdir -p ~/.tuneps_data/analyses
mkdir -p ~/.tuneps_data/db
mkdir -p ~/.tuneps_data/exports
mkdir -p ~/.tuneps_data/rfp-pipeline
```

---

## 8. Configuration

### 8.1 Tuneps Scanner Configuration

Main script:

```text
~/.openclaw/workspace/skills/tuneps-scrape/scripts/tuneps.js
```

Main command format:

```bash
node scripts/tuneps.js DATE_FROM DATE_TO BUYER_FILTER DEADLINE_DAYS --profile-filter --output /tmp/tuneps_output.txt
```

Arguments:

| Argument | Meaning | Example |
|---|---|---|
| DATE_FROM | Publication start date | `2026-01-01` |
| DATE_TO | Publication end date | `2026-07-15` |
| BUYER_FILTER | Buyer/authority filter | `Ministère de la Défense Nationale` |
| DEADLINE_DAYS | Deadline window | `0` for no filter |

### 8.2 Cache

Scanner cache directory:

```text
/tmp/tuneps_cache
```

Repeated scans with identical parsed parameters can reuse cached output.

### 8.3 RFP Pipeline Configuration

Company profile:

```text
~/.openclaw/workspace/rfp-pipeline/config/company_profile.json
```

Contains:
- Company name
- Sector
- Product lines
- Keywords
- Exclusion keywords
- Relevance thresholds
- RAG queries

Analysis prompts:

```text
~/.openclaw/workspace/rfp-pipeline/config/analysis_prompts.json
```

Contains:
- System prompt
- Scoring guidance
- Expected JSON schema
- CCTP report format
- CCAP report format

### 8.4 Storage Configuration

Strict data root:

```text
~/.tuneps_data/
```

Do not create active tender data folders under `~/.openclaw/workspace`.

Compatibility symlinks may exist:

```text
~/.openclaw/workspace/offres/documents
~/.openclaw/workspace/offres/analyses
```

---

## 9. User Guide

### 9.1 Scan Today’s Tenders

WhatsApp command:

```text
scan tuneps
```

Equivalent script command:

```bash
cd ~/.openclaw/workspace/skills/tuneps-scrape
node scripts/tuneps.js 2026-07-15 2026-07-15 "" 0 --profile-filter --output /tmp/tuneps_output.txt
```

### 9.2 Scan Ministry of Defense This Year

WhatsApp command:

```text
scan tuneps for mod this year
```

Parsed as:

```text
DATE_FROM=2026-01-01
DATE_TO=2026-07-15
BUYER_FILTER=Ministère de la Défense Nationale
DEADLINE_DAYS=0
```

### 9.3 Request a CCTP Document

WhatsApp command:

```text
send me cctp document for this offer 20260301601
```

Assistant looks for:

```text
~/.tuneps_data/documents/20260301601/cctp.pdf
```

### 9.4 Request an Analysis

WhatsApp command:

```text
analyse it
```

Assistant sends existing analysis files from:

```text
~/.tuneps_data/analyses/<ref>/
```

### 9.5 Scan Output Rules

For `scan tuneps`, the assistant must display the script output exactly as generated:
- No translation
- No reformatting
- No extra headers
- No added commentary

If no relevant offer is found, the assistant may provide a short exclusion explanation and list excluded ICT-looking raw candidates when available.

---

## 10. Use Case: Ministry of Defense

### 10.1 User Request

```text
scan tuneps for mod this year
```

### 10.2 Parsed Parameters

```text
DATE_FROM=2026-01-01
DATE_TO=2026-07-15
BUYER_FILTER=Ministère de la Défense Nationale
DEADLINE_DAYS=0
```

### 10.3 Result Summary

The scan found 169 Ministry of Defense tenders and identified 2 relevant ICT infrastructure opportunities:

1. `20260302670` — Acquisition of equipment, cables and network connectors
2. `20260301601` — Acquisition and implementation of a computer platform to host applications

### 10.4 Tender 20260301601

Title:

```text
The acquisition and implementation of a computer platform to host applications.
```

Authority:

```text
Ministry of National Defense
```

Submission deadline:

```text
2026-04-21 09:00:00.0
```

Local documents available:

```text
~/.tuneps_data/documents/20260301601/cctp.pdf
~/.tuneps_data/documents/20260301601/ccap.pdf
~/.tuneps_data/documents/20260301601/architecture.jpeg
```

Available analyses:

```text
~/.tuneps_data/analyses/20260301601/CCTP_Analysis_Mutuelle_Armee_Huawei_Relevance.docx
~/.tuneps_data/analyses/20260301601/CCAP_Analysis_20260301601.docx
```

### 10.5 Business Interpretation

This tender is highly aligned with Huawei-style ICT infrastructure because it concerns a platform to host applications, including datacenter/application hosting infrastructure. It is relevant to cloud, server, storage, virtualization, networking, cybersecurity, and system integration profiles depending on the final CCTP scope.

---

## 11. Repository Structure

### 11.1 Main Workspace

```text
~/.openclaw/workspace/
├── AGENTS.md
├── SOUL.md
├── IDENTITY.md
├── USER.md
├── TOOLS.md
├── HEARTBEAT.md
├── skills/
│   └── tuneps-scrape/
├── rfp-pipeline/
├── reference/
└── offres/                  # compatibility symlinks / templates
```

### 11.2 Tuneps Skill

```text
skills/tuneps-scrape/
├── SKILL.md
├── TEMPLATE.md
├── package.json
├── package-lock.json
├── .env                     # local only, not committed
├── scripts/
│   ├── tuneps.js
│   ├── build_ccap_docx.py
│   └── build_cctp_docx.py
└── references/
    └── abbreviations.md
```

### 11.3 RFP Pipeline

```text
rfp-pipeline/
├── README.md
├── requirements.txt
├── run_pipeline.ps1
├── setup-python.ps1
├── step1_parse.py
├── step2_clean.py
├── step3_chunk.py
├── step4_embed.py
├── step5_analyse.py
├── config/
│   ├── company_profile.json
│   └── analysis_prompts.json
├── input/
└── output/
```

### 11.4 Data Storage

```text
~/.tuneps_data/
├── documents/
│   └── <ref>/
├── analyses/
│   └── <ref>/
├── db/
│   └── tenders.db
├── exports/
└── rfp-pipeline/
```

---

## 12. GitHub Repository

Current Git remote:

```text
https://github.com/faiezlouati/Openclaw-based-AI-agent
```

Recommended repository content:
- OpenClaw workspace configuration files without secrets
- Tuneps scraping skill
- RFP pipeline code
- Prompt templates
- Documentation
- Example sanitized outputs

Do not commit:
- `.env` files
- API keys
- Private WhatsApp metadata
- Private tender documents unless authorized
- Local ChromaDB if large/private
- Sensitive internal analysis files if not intended for publication

Recommended `.gitignore` entries:

```gitignore
.env
node_modules/
__pycache__/
*.pyc
.venv/
venv/
chroma_db/
input/
output/
*.pdf
*.docx
*.doc
~/.tuneps_data/
```

---

## 13. Troubleshooting

### 13.1 Scan Returns Zero Tenders

Possible causes:
- No public tenders for the selected date range
- Buyer filter too strict
- Tuneps API temporary issue
- Date range parsed incorrectly

Actions:
- Try a wider date range
- Remove buyer filter
- Run raw JSON mode for inspection

```bash
node scripts/tuneps.js 2026-01-01 2026-07-15 "" 0 --raw-json /tmp/tuneps_candidates.json
```

### 13.2 Relevant Tender Missing

Possible causes:
- Title uses unusual wording
- Strict profile filter excluded it
- Business context requires manual review

Actions:
1. Fetch raw candidates.
2. Review titles manually with ICT/Huawei scope.
3. Re-render using `--include-refs`.

```bash
node scripts/tuneps.js 2026-01-01 2026-07-15 "" 0 --include-refs REF1,REF2 --output /tmp/tuneps_output.txt
```

### 13.3 GROQ_API_KEY Error

Cause:
- `.env` is missing or does not contain `GROQ_API_KEY`.

Fix:

```env
GROQ_API_KEY=your_key_here
```

### 13.4 CCTP/CCAP Document Not Found

Expected path:

```text
~/.tuneps_data/documents/<ref>/
```

Fix:
- Upload the document manually.
- Confirm the reference number.
- Enable Tuneps login/download access if automatic download is required in the future.

### 13.5 Analysis File Not Found

Expected path:

```text
~/.tuneps_data/analyses/<ref>/
```

Fix:
- Generate a new analysis using the RFP pipeline or document generation scripts.
- Confirm the tender reference.

### 13.6 WhatsApp Duplicate Attachment Rendering

When sending multiple files, send one attachment per message when possible to avoid duplicate rendering issues.

### 13.7 RFP Pipeline Parsing Problems

Possible causes:
- Scanned PDF without text layer
- Complex tables
- Arabic/French mixed formatting
- Missing optional OCR API key

Actions:
- Enable Mistral OCR for diagrams/images if needed.
- Inspect parsed Markdown.
- Run steps individually to locate the failing stage.

```bash
python step1_parse.py
python step2_clean.py
python step3_chunk.py
python step4_embed.py
python step5_analyse.py
```

### 13.8 Data Stored in Wrong Location

Rule:

```text
Use ~/.tuneps_data/ only for tender/RFP data.
```

Fix:
- Move documents to `~/.tuneps_data/documents/<ref>/`.
- Move analyses to `~/.tuneps_data/analyses/<ref>/`.
- Keep workspace only for code, prompts, skills, templates, and documentation.

---

## Appendix A — Key Commands

### Scan Today

```bash
cd ~/.openclaw/workspace/skills/tuneps-scrape
node scripts/tuneps.js 2026-07-15 2026-07-15 "" 0 --profile-filter --output /tmp/tuneps_output.txt
```

### Scan Ministry of Defense This Year

```bash
cd ~/.openclaw/workspace/skills/tuneps-scrape
node scripts/tuneps.js 2026-01-01 2026-07-15 "Ministère de la Défense Nationale" 0 --profile-filter --output /tmp/tuneps_output.txt
```

### Raw Candidate Export

```bash
cd ~/.openclaw/workspace/skills/tuneps-scrape
node scripts/tuneps.js 2026-01-01 2026-07-15 "" 0 --raw-json /tmp/tuneps_candidates.json
```

### Render Specific References

```bash
cd ~/.openclaw/workspace/skills/tuneps-scrape
node scripts/tuneps.js 2026-01-01 2026-07-15 "" 0 --include-refs 20260301601 --output /tmp/tuneps_output.txt
```

---

## Appendix B — Public API Endpoints Used

The scanner uses public Tuneps API endpoints:

```text
POST https://www.tuneps.tn/api2/portail/bid/master/data
GET  https://www.tuneps.tn/api2/portail/bid/master/<id>
GET  https://www.tuneps.tn/api2/portail/vBidCls/lot?bidNo=<bidNo>
```

Public detail page format:

```text
https://www.tuneps.tn/portail/offres/details/<epBidMasterId>/<reference>
```

---

## Appendix C — Current Known Example Files

Tender `20260301601`:

```text
Documents:
~/.tuneps_data/documents/20260301601/cctp.pdf
~/.tuneps_data/documents/20260301601/ccap.pdf
~/.tuneps_data/documents/20260301601/architecture.jpeg

Analyses:
~/.tuneps_data/analyses/20260301601/CCTP_Analysis_Mutuelle_Armee_Huawei_Relevance.docx
~/.tuneps_data/analyses/20260301601/CCAP_Analysis_20260301601.docx
```

Tender `20260600248`:

```text
Documents:
~/.tuneps_data/documents/20260600248/cctp.pdf
~/.tuneps_data/documents/20260600248/ccap.pdf

Analyses:
~/.tuneps_data/analyses/20260600248_oaca_radiocommunication/CCTP_Analysis_OACA_Radiocommunication_20260600248.docx
~/.tuneps_data/analyses/20260600248_oaca_radiocommunication/CCAP_Analysis_OACA_Radiocommunication_20260600248.docx
```
