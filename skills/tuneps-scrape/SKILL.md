---
name: tuneps-scrape
trigger: "scan tuneps"
description: Fetch tenders from Tuneps API, filter relevant ICT ones, display results
user-invocable: true
tools:
  - exec
---

# Tuneps Tender Scanner

## Trigger
User says "scan tuneps" optionally followed by filters.

## Script Argument Structure

The script takes up to 5 arguments:
```
node scripts/tuneps.js DATE_FROM DATE_TO BUYER_FILTER DEADLINE_DAYS
```

| Arg | Description | Default |
|-----|-------------|---------|
| DATE_FROM | Start of publication date range (YYYY-MM-DD) | today |
| DATE_TO | End of publication date range (YYYY-MM-DD) | today |
| BUYER_FILTER | Authority name filter (empty = no filter) | "" |
| DEADLINE_DAYS | Filter by submission deadline window (0 = no filter) | 0 |

## User Input Parsing

### Date Range → DATE_FROM + DATE_TO

| User says | DATE_FROM | DATE_TO |
|-----------|-----------|---------|
| nothing / today | today | today |
| last 7 days | today minus 7 | today |
| this week | today minus 7 | today |
| last month | first day of **previous calendar month** | last day of **previous calendar month** |
| this month | first day of **current calendar month** | today |
| this year | 2026-01-01 | today |
| from X to Y | X | Y |
| single date e.g. 2026-05-01 | that date | that date |

### Deadline Filter → DEADLINE_DAYS

| User says | DEADLINE_DAYS | Logic |
|-----------|---------------|-------|
| "before June" | days until June 1 | tenders opening within next N days |
| "opening this week" | 7 | deadline between now and +7 days |
| "opening this month" | 30 | deadline between now and +30 days |
| "opening before [date]" | compute days from now to [date] | tenders opening before [date] |

**How DEADLINE_DAYS works:**
- `DEADLINE_DAYS > 0` → tenders whose `bdRecvEndDt` falls between now and now+N days
- `DEADLINE_DAYS < 0` → tenders that expired in the last N days
- `DEADLINE_DAYS = 0` → no deadline filter (show all in date range)

### Ministry Nicknames → BUYER_FILTER

**Always map to official names before setting BUYER_FILTER:**
- `défense` → **Ministère de la Défense Nationale**
- `présidence` → **Présidence du Gouvernement**
- _(add more as you discover them)_

If user references a specific ministry, set BUYER_FILTER to the official name.

## Workflow

### Step 1 - Parse the user message

1. Extract DATE_FROM / DATE_TO from date expressions
2. Extract DEADLINE_DAYS from deadline/-opening expressions
3. Map any ministry nickname to official name → BUYER_FILTER

### Step 2 - Fast one-pass scan (default)

Use the script's strict profile filter by default. It fetches candidates, applies the Huawei-scope relevance rules, fetches details only for relevant refs, and renders the final report in one run.

```
cd ~/.openclaw/workspace/skills/tuneps-scrape && node scripts/tuneps.js DATE_FROM DATE_TO BUYER_FILTER DEADLINE_DAYS --profile-filter --output /tmp/tuneps_output.txt
```

### Step 3 - Context review safety net

Run this review if the fast output looks suspicious, returns 0 results, or the user challenges relevance:

```
cd ~/.openclaw/workspace/skills/tuneps-scrape && node scripts/tuneps.js DATE_FROM DATE_TO BUYER_FILTER DEADLINE_DAYS --raw-json /tmp/tuneps_candidates.json
```

Read `/tmp/tuneps_candidates.json`. Classify titles with the current OpenClaw model using title context and ICT/Huawei/telecom business scope, not keyword matching only. If a title logically describes telecom/ICT infrastructure, include it even if the exact keyword rule missed it. Then render corrected refs:

```
cd ~/.openclaw/workspace/skills/tuneps-scrape && node scripts/tuneps.js DATE_FROM DATE_TO BUYER_FILTER DEADLINE_DAYS --include-refs REF1,REF2,REF3 --output /tmp/tuneps_output.txt
```

Do not use Groq for title classification unless explicitly reverting/debugging.

### Step 4 - Read and display the output

After the script completes, read the file at `/tmp/tuneps_output.txt` and display its contents **exactly as-is** in your message (as the first message, not as a tool result).

### Step 6 - Done

## Authority Abbreviations

When tenders reference abbreviated authority names, resolve them using:
`~/.openclaw/workspace/skills/tuneps-scrape/references/abbreviations.md`

Known abbreviations include CCK (Centre de Calcul El-Khawarizmi), ONP (Office National des Postes), DGDD (Direction Générale de la Douane), CRDA, OTAM, OMM, INS, CNI, CNR, and more.

## Unified RFP Storage

Tender/RFP data must use the single storage root:

- Documents: `~/.tuneps_data/documents/<ref>/`
- Analyses: `~/.tuneps_data/analyses/<ref>/`
- Database: `~/.tuneps_data/db/tenders.db`
- RFP pipeline data/state: `~/.tuneps_data/rfp-pipeline/`
- RFP pipeline code: `~/.openclaw/workspace/rfp-pipeline/`

Do not create active tender data under `~/.openclaw/workspace/offres`; its data folders are compatibility symlinks only.

## Rules
- Always parse before running — never pass raw user input to the script
- BUYER_FILTER supports partial match (e.g. "STEG" matches "Société Tunisienne d'Electricité et de Gaz")
- For "before June" type queries: DATE_FROM/DATE_TO = publication range, DEADLINE_DAYS = days until cutoff
- Default DEADLINE_DAYS to 0 (no filter) unless user explicitly mentions opening/deadline constraints
- Display the complete script output without truncation
## Tuneps Login-Based RFP Download Helpers

Credential capture and RFP document download are available, but only when the user explicitly asks for them.

Scripts:
- `scripts/capture_tuneps_credentials.py` — after the user manually logs in to Tuneps in Chrome with the Tuneps key/account, captures the `cookiesession1` cookie and JWT/token into `~/.tuneps_data/credentials.json`.
- `scripts/download_tuneps_rfp_documents.py` — downloads RFP attachments only for explicitly provided tender IDs into `~/.tuneps_data/documents/<ref>/`.

Rules:
- Do not capture credentials unless the user asks.
- Do not download RFP documents unless the user asks and provides/identifies the tender ID.
- Never use a default tender list for downloads.
- Store all downloaded RFP documents under `~/.tuneps_data/documents/<ref>/`.
- If credentials are missing or expired, ask the user to log in to Tuneps in Chrome, then run the capture script.

Commands:
```bash
cd ~/.openclaw/workspace/skills/tuneps-scrape
python3 -m pip install -r requirements.txt
python3 scripts/capture_tuneps_credentials.py
python3 scripts/download_tuneps_rfp_documents.py 20260600248
```
