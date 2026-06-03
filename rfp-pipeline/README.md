# RFP Pipeline

Automated analysis pipeline for Tunisian public procurement documents (CCAP / CCTP).  
Determines whether a tender is relevant to an ICT infrastructure company by parsing, cleaning, chunking, embedding, and querying documents with an LLM.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Running the Pipeline](#running-the-pipeline)
8. [Step-by-Step Code Explanation](#step-by-step-code-explanation)
   - [Step 1 — Parse](#step-1--parse-step1_parsepy)
   - [Step 2 — Clean](#step-2--clean-step2_cleanpy)
   - [Step 3 — Chunk](#step-3--chunk-step3_chunkpy)
   - [Step 4 — Embed](#step-4--embed-step4_embedpy)
   - [Step 5 — Analyse](#step-5--analyse-step5_analysepy)
9. [Output Files](#output-files)
10. [Configuration Files](#configuration-files)

---

## Overview

This pipeline processes PDF and DOCX procurement documents (CCAP/CCTP) through five sequential steps:

```
PDF / DOCX  →  Markdown  →  Cleaned MD  →  Chunks  →  ChromaDB  →  HTML Report
             (Step 1)      (Step 2)      (Step 3)    (Step 4)      (Step 5)
```

The final output is a relevance score (0–100), a BID / REVIEW / SKIP recommendation, and a full HTML report listing matched product lines and extracted technical requirements.

---

## Architecture

```
rfp-pipeline/
│
├── input/                        ← Drop your PDF / DOCX / DOC files here
│
├── output/                       ← All intermediate and final output files
│   ├── <name>_parsed.md          ← Raw Markdown from Docling (step1)
│   ├── <name>_cleaned.md         ← Cleaned Markdown (step2)
│   ├── <name>_metadata.json      ← Document type, language, word count (step2)
│   ├── <name>_chunks.json        ← Chunk array with metadata (step3)
│   ├── <name>_chunks_report.md   ← Human-readable chunk evaluation (step3)
│   ├── <name>_analysis.json      ← LLM analysis result (step5)
│   └── <name>_report.html        ← Final HTML report (step5)
│
├── chroma_db/                    ← Persistent ChromaDB vector store (step4)
│
├── config/
│   ├── company_profile.json      ← Company info, product lines, RAG queries
│   └── analysis_prompts.json     ← LLM system prompt and scoring guidance
│
├── step1_parse.py
├── step2_clean.py
├── step3_chunk.py
├── step4_embed.py
├── step5_analyse.py
├── run_pipeline.ps1              ← Runs all 5 steps in sequence
├── requirements.txt
└── .env                          ← API keys (not committed to git)
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | 3.12 recommended |
| pip | latest | bundled with Python |
| Microsoft Word *(optional)* | any | only needed to convert legacy `.doc` files |
| LibreOffice *(optional)* | any | fallback `.doc` converter if Word is not installed |

API keys required:

| Key | Used by | Required? |
|---|---|---|
| `MISTRAL_API_KEY` | Step 1 — diagram OCR | Optional (diagrams kept as placeholders if missing) |
| `GROQ_API_KEY` | Step 5 — LLM analysis | **Required** |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/rfp-pipeline.git
cd rfp-pipeline
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The first run of Step 1 will download Docling's AI models (~1 GB). This is a one-time download; all subsequent runs are fully offline.

---

## Configuration

### .env file

Create a `.env` file in the project root:

```env
MISTRAL_API_KEY=your_mistral_key_here
GROQ_API_KEY=your_groq_key_here
```

- Get a free Groq API key at [console.groq.com](https://console.groq.com)
- Get a Mistral API key at [console.mistral.ai](https://console.mistral.ai) (optional)

### Add your documents

Copy your PDF, DOCX, or DOC procurement files into the `input/` folder.

---

## Running the Pipeline

### Option A — Run all steps at once (recommended)

```powershell
.\run_pipeline.ps1
```

This runs steps 1 through 5 in sequence and stops immediately if any step fails.

### Option B — Run steps individually

```bash
python step1_parse.py
python step2_clean.py
python step3_chunk.py
python step4_embed.py
python step5_analyse.py
```

Each step reads from `output/` and writes back to `output/`. Always run them in order.

---

## Step-by-Step Code Explanation

### Step 1 — Parse (`step1_parse.py`)

**Purpose:** Convert every PDF / DOCX / DOC in `input/` to clean Markdown.

**How it works:**

**Pass 1 — Docling (offline)**  
Uses the [Docling](https://github.com/DS4SD/docling) library to extract text and tables from the document and export them as Markdown. Table structure recognition is enabled; OCR is disabled (assumes text-layer PDFs).

**Pass 2 — Mistral OCR (optional, API)**  
Docling replaces embedded images with `<!-- image -->` placeholders. If `MISTRAL_API_KEY` is set, Step 1 extracts those images using PyMuPDF (for PDF) or the ZIP content (for DOCX), sends each one to the `pixtral-large-latest` Mistral vision model, and replaces the placeholder with a structured Markdown description of the diagram.

**Legacy `.doc` support**  
`.doc` files are first converted to `.docx` using Microsoft Word COM automation (Windows) or LibreOffice headless as a fallback.

**Output:** `output/<name>_parsed.md` for each input file.

---

### Step 2 — Clean (`step2_clean.py`)

**Purpose:** Apply a 7-stage cleaning pipeline to the raw Markdown produced by Step 1.

**The 7 stages:**

| Stage | What it does |
|---|---|
| 1 — Fix encoding | Runs `ftfy` to fix mojibake, normalises to Unicode NFC, strips invisible characters (soft hyphens, zero-width spaces, BOM, LRM/RLM marks) |
| 2 — Detect concatenation | Warns about words that were merged during parsing (e.g. `"serveurSwitch"`) using camelCase and long-token heuristics |
| 3 — Merge split titles | Scans the first 20 lines for consecutive headings of the same level that together form one document title, and merges them |
| 4 — Merge split tables | Detects tables interrupted by page breaks (identified by blank lines and page-number artefacts) and merges them back into one table if column counts match |
| 5 — Clean diagrams | Normalises `[DIAGRAM START]...[DIAGRAM END]` blocks and replaces remaining `<!-- image -->` placeholders with a readable fallback label |
| 6 — Normalise whitespace | Collapses 3+ blank lines to 2, reduces blank lines before/after headings to 1, normalises bullet characters to `-` |
| 7 — Remove headers/footers | Removes repeated short lines (appearing 3+ times) which are page headers or footers, and strips standalone page numbers |

**Metadata extraction:**  
After cleaning, Step 2 detects the document type (`CCAP`, `CCTP`, `CDC`, or `UNKNOWN`) by searching for French and Arabic keywords in the first 2 000 characters. It also detects the language (`fr`, `ar`, or `mixed`) by comparing the ratio of Arabic to Latin characters.

**Output:** `output/<name>_cleaned.md` and `output/<name>_metadata.json`.

---

### Step 3 — Chunk (`step3_chunk.py`)

**Purpose:** Split the cleaned Markdown into discrete chunks suitable for embedding, using 5 document-aware rules.

**How it works (4 internal steps):**

**A — Parse typed blocks**  
The cleaned Markdown is parsed into a flat list of typed blocks: `heading`, `table`, `diagram`, or `text`. Diagram blocks are consumed atomically so that any headings inside them are not treated as section boundaries.

**B — Group into sections**  
The block list is split into sections at every `##` (level-2) heading. Content before the first `##` becomes the preamble.

**C — Apply 5 rules**

| Rule | Description |
|---|---|
| Rule 1 | Each section is one chunk (baseline) |
| Rule 2 | Diagram blocks are always isolated in their own chunk |
| Rule 3 | Tables are never split; oversized table-chunks trigger a warning instead |
| Rule 4 | Chunks under 50 words are merged into the previous chunk (exceptions: diagram chunks, last chunk, chunk after a diagram) |
| Rule 5 | Text-only sections over 600 words are split at paragraph boundaries, targeting ~400 words per sub-chunk |

**D — Build output objects**  
Each chunk gets a full metadata record: `chunk_id`, `source_file`, `document_type`, `detected_language`, `section_title`, `block_types`, `contains_diagram`, `contains_table`, `word_count`, `char_count`.

**Output:** `output/<name>_chunks.json` and `output/<name>_chunks_report.md` (human-readable evaluation with rule violation counts and a full chunk content listing).

---

### Step 4 — Embed (`step4_embed.py`)

**Purpose:** Generate vector embeddings for all chunks and store them in a local ChromaDB.

**How it works:**

1. Loads the `paraphrase-multilingual-mpnet-base-v2` sentence-transformer model locally (supports French and Arabic).
2. For each chunk, concatenates the `section_title` and `text` to form the embedding input.
3. Encodes all new chunks in a single batched call (`batch_size=32`).
4. Upserts embeddings into a persistent ChromaDB collection named `rfp_chunks` using cosine similarity space.
5. Skips chunks whose `chunk_id` is already in the collection (idempotent — safe to re-run).

**Output:** `chroma_db/` directory (persistent, cumulative across runs).

---

### Step 5 — Analyse (`step5_analyse.py`)

**Purpose:** Query the vector store with business-relevant questions, build a context window, call the Groq LLM, and produce a relevance analysis with an HTML report.

**How it works:**

**1 — Discover tenders**  
Groups all `*_chunks.json` files in `output/` into a single tender and derives a `tender_id` from the first file's stem.

**2 — RAG retrieval**  
For each of the 7 RAG queries defined in `config/company_profile.json`, the query is embedded using the same sentence-transformer model and the top-7 most similar chunks are retrieved from ChromaDB. Results are deduplicated by `chunk_id` and capped at 20 chunks.

**3 — Prompt construction**  
A prompt is built containing:
- Company name, sector, and product lines with keywords
- Exclusion keywords (auto-disqualify triggers)
- Scoring guidance (0–100 scale with BID / REVIEW / SKIP thresholds)
- The retrieved chunks, each trimmed to 300 words

**4 — Groq LLM call**  
The prompt is sent to `llama-3.3-70b-versatile` via the Groq API (`temperature=0`, `max_tokens=2000`). If the response is not valid JSON, a single retry is attempted with a simplified prompt.

**5 — Output**  
The JSON result is validated for required keys (`relevant`, `relevance_score`, `relevance_level`, `matched_product_lines`, `key_requirements`, `summary`, `recommendation`, `recommendation_reason`) and saved. An HTML report is generated with a colour-coded badge (green = BID, orange = REVIEW, red = SKIP), score bar, matched product line table with evidence, and extracted requirements table.

**Output:** `output/<name>_analysis.json` and `output/<name>_report.html`.

---

## Output Files

| File | Produced by | Description |
|---|---|---|
| `*_parsed.md` | Step 1 | Raw Markdown from Docling, images replaced with `<!-- image -->` or described by Mistral |
| `*_cleaned.md` | Step 2 | Fully cleaned Markdown, ready for chunking |
| `*_metadata.json` | Step 2 | Document type, language, word count, section titles, warnings |
| `*_chunks.json` | Step 3 | Array of chunk objects with full metadata |
| `*_chunks_report.md` | Step 3 | Human-readable chunking evaluation |
| `*_analysis.json` | Step 5 | LLM relevance analysis (score, recommendation, matched lines, requirements) |
| `*_report.html` | Step 5 | Visual HTML report — open in any browser |

---

## Configuration Files

### `config/company_profile.json`

Controls what the pipeline considers relevant:

- **`company_name`**, **`sector`**, **`description`** — used in the LLM prompt
- **`product_lines`** — each line has a `name`, `description`, `keywords` list, and `weight`; the LLM uses these to match and score tender content
- **`exclusion_keywords`** — domains that auto-disqualify a tender (medical, construction, vehicles, standard office supplies, etc.)
- **`scoring_rules`** — thresholds for HIGH (70+), MEDIUM (40+), LOW (20+) relevance
- **`recommendation_rules`** — BID / REVIEW / SKIP thresholds
- **`rag_queries`** — the 7 search queries used to retrieve relevant chunks from ChromaDB

### `config/analysis_prompts.json`

Controls the LLM behaviour:

- **`system_prompt`** — instructs the model to act as a bid analyst and return only valid JSON
- **`scoring_guidance`** — detailed scoring rubric sent in every user prompt
- **`output_schema_description`** — specifies the exact JSON keys the model must return
