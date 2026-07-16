# TOOLS.md - Local Notes

## RED LINES (STRICT — NEVER CROSS)

- **NEVER send any message (WhatsApp, email, Telegram, Signal, etc.) unless the user explicitly asks for it**
- **NEVER configure cron/automation to send WhatsApp messages without explicit approval first**
- If you sent something unprompted → apologize and update this rule immediately

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

### Tuneps Ministry Mapping (Critical Rule)

**Tuneps does NOT recognize raw nicknames or abbreviations.** Always map user-provided ministry nicknames and abbreviations to their official full names before searching or filtering.

- `défense` → **Ministère de la Défense Nationale**
- `mod` → **Ministère de la Défense Nationale**
- `présidence` → **Présidence du Gouvernement**
- `CCK` → **Centre de Calcul El-Khawarizmi**
- _(add more as you discover them)_

### WhatsApp Bot Number

- **Bot number:** +21658777344 (used as WhatsApp account for the bot)
- **Allowlist:** +21656771913, +8619941343428

### Tuneps RFP Uploaded Document Analysis Rule

When the user uploads CCTP and CCAP documents and says to analyze the offer, produce the two analyses directly:

1. **CCTP RELEVANCE ANALYSIS** — use the English CCTP format/template, including Huawei in “Relevance by vendor profile” and explicitly stating when the offer is top relevant for Huawei.
2. **CCAP ANALYSIS** — use the English administrative CCAP format/template.

For RFP documents related to the **Ministry of Defense / Mutuelle de l’Armée Nationale datacenter offer**, automatically return these two analyses in the established Word-example style. Do not ask for confirmation.

Do not ask whether to analyze. Ask only if a required document is missing, unreadable, or ambiguous.

**Decision-support wording rule:** Never state or label the recommendation as “BID”, “NO-BID”, “bid/no-bid”, or equivalent. The final participation decision is human/management-owned. Analyses should only support decision-making by showing relevance, fit, risks, constraints, validation points, and decision-support notes.

**Huawei portfolio reference:** For every CCTP technical relevance analysis, use `/Users/albus/.openclaw/workspace/reference/huawei_portfolio_tunisia.json` as the Huawei product/certification/reference baseline. If that file contains internal scoring labels such as BID/REVIEW/SKIP, treat them only as internal matching levels and convert them in final analysis wording to decision-support language such as “strong relevance”, “requires validation”, or “low relevance”.

### Tuneps RFP Document Access Rule (STRICT)

When the user asks about RFP documents (CCAP, CCTP, BPU, DQE, RC, annexes), clearly state that I do **not** have access to the full RFP documents because there is no Tuneps login key/account available. I can only access public listing metadata unless the user provides the documents or enables login/download access.

### Tuneps CCTP/CCAP Document Reply Rule (STRICT)

When the user asks for CCTP and/or CCAP documents that are available locally, respond only by attaching/sending the requested documents. Do not add locations, explanations, summaries, or extra info unless the user explicitly asks.

If the user says “analyse/analyze” for a tender, send the existing analysis DOCX file(s), not the original CCTP/CCAP source documents, unless they explicitly ask for source documents. For multiple attachments, send one file per message when possible to avoid WhatsApp duplicate-render issues.

### Tuneps Data Storage Rule (STRICT)

**Use exactly one storage root for tender/RFP data:** `~/.tuneps_data/`

- Documents: `~/.tuneps_data/documents/<ref>/`
- Analyses: `~/.tuneps_data/analyses/<ref>/`
- Database: `~/.tuneps_data/db/tenders.db`
- RFP pipeline data/state: `~/.tuneps_data/rfp-pipeline/`
- RFP pipeline code: `~/.openclaw/workspace/rfp-pipeline/`
- Exports: `~/.tuneps_data/exports/`

`~/.openclaw/workspace` is for code, skills, prompts, and templates only. Do not create new active tender data folders under workspace. Existing `workspace/offres/documents` and `workspace/offres/analyses` are symlinks into `~/.tuneps_data` for compatibility.

### Tuneps Classification Rule

Generic computer equipment / basic "équipement informatique" tenders are **NOT relevant** unless the title clearly indicates Huawei-scope infrastructure such as servers, networking, storage, datacenter, cybersecurity, telecom, radio-communication, VoIP, cloud, software platforms, or similar ICT systems. Do not include a tender only because it says "computer equipment".

Microsoft licenses, messaging licenses, software assurance, office productivity renewals, and similar basic software/equipment procurement are **NOT relevant** to the company profile unless the title clearly indicates Huawei-scope infrastructure, cybersecurity, network, datacenter, telecom, cloud, or server platform work.

Fleet geolocation systems, biometric/fingerprint attendance systems, basic municipal video-surveillance equipment, renewal of licenses/support for already-installed firewalls or access points, and pure expert/consulting appointments for information-system security are **NOT relevant** unless the title clearly includes Huawei-scope infrastructure delivery such as datacenter, servers, storage, core network, telecom infrastructure, enterprise cybersecurity platform deployment, cloud, or similar integrated ICT systems.

**Cloud infrastructure query rule:** When the user asks “find tenders related to cloud infrastructure this year” or similar wording, interpret it strictly as IaaS/private cloud/cloud infrastructure offers, not generic datacenter, hosting/accommodation, servers, or datacenter maintenance. For the 2026 year scan, show only `20260302986` unless a newer clearly cloud-infrastructure/IaaS tender is found.

**Context rule — critical:** Do not classify Tuneps offers only by keyword presence. Always interpret the title in business context. If an offer logically belongs to telecom / ICT infrastructure even without exact keywords, treat it as relevant or trigger review. Example: radio-communication equipment is telecom infrastructure and must be relevant.

### Tuneps Language Reply Rule

If the user asks in Chinese, reply in Chinese. For `scan tuneps` reports, preserve the script output verbatim unless the user explicitly asks for translation.

### Tuneps Output Rule (STRICT — NON-NEGOTIABLE)

**This rule is FOREVER. No exceptions. No interpretation.**

When running `scan tuneps`:

0. If a tender’s *Submission Deadline* has already passed, clearly mention that it is expired/passed in the displayed result.
1. **Copy-paste the script output VERBATIM** — do NOT reformat, do NOT translate, do NOT add headers, do NOT add bullet points, do NOT add your own labels
2. **Never wrap the output in your own formatting** — no headers like "Tuneps Scan — Today", no bullet lists, no emojis as headers, no French/English translation of field labels
3. **If the script outputs French** → display French. **If the script outputs English** → display English. Do NOT convert.
4. **If there is no relevant offer**, send two simple explanation sentences first, then list excluded ICT-looking raw candidates in this concise style:
   `These offers mention IT, but they are basic supplies or generic maintenance.`
   `They do not match your company profile.`
   `20260600648 — IT consumables — Buyer: Example Authority → excluded, basic consumables`
   Offer titles/categories in this explanation must be in English. Always include the buyer/authority for each excluded ICT-looking candidate. Keep it short: ref, short English title/category, buyer, arrow, exclusion reason. Use simple sentences only; no headers, no long analysis.

### Tuneps Scan Workflow (Strict Rule)

**Cache rule:** If the user asks the exact same `scan tuneps` request twice with the same parsed parameters (`FROM_DATE`, `DATE_TO`, `BUYER_FILTER`, `DEADLINE_DAYS`) and the previous scan result is already available, reuse the cached previous result instead of querying Tuneps again. Display the cached script output exactly as-is.

**Default fast path:**
1. **Parse input** → convert user request to script arguments
2. **Check cache** → if identical parsed scan parameters were already run and output exists, reuse the cached output
3. **Run one-pass profile scan** → execute `node scripts/tuneps.js FROM_DATE DATE_TO BUYER_FILTER DEADLINE_DAYS --profile-filter --output /tmp/tuneps_output.txt`
4. **Display result** → show script output EXACTLY as-is — no modification

**Review path when output looks suspicious, has 0 results, or user challenges relevance:**
1. Fetch raw candidates → `node scripts/tuneps.js FROM_DATE DATE_TO BUYER_FILTER DEADLINE_DAYS --raw-json /tmp/tuneps_candidates.json`
2. Classify titles with the current OpenClaw model using title context and Huawei/telecom/ICT business scope — not keyword matching only
3. Render corrected report → `node scripts/tuneps.js FROM_DATE DATE_TO BUYER_FILTER DEADLINE_DAYS --include-refs REF1,REF2 --output /tmp/tuneps_output.txt`
4. Display result exactly as-is

Do not use Groq for scan Tuneps title classification unless explicitly reverting/debugging.

### Skills / Workflows

- **scan tuneps** → When user says "scan tuneps", execute the skill at `~/.openclaw/workspace/skills/tuneps-scrape/`:
  1. Parse date range, deadline filter, and ministry nicknames from user message
  2. Map ministry nicknames to official names (see mapping above)
  3. Run fast profile scan: `cd ~/.openclaw/workspace/skills/tuneps-scrape && node scripts/tuneps.js FROM_DATE DATE_TO BUYER_FILTER DEADLINE_DAYS --profile-filter --output /tmp/tuneps_output.txt`
  4. Display the output EXACTLY as printed — no summary, no modification
  5. If relevance is questionable, use the raw-json + current-model review path and rerender corrected refs

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)