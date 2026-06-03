# TOOLS.md - Local Notes

## RED LINES (STRICT — NEVER CROSS)

- **NEVER send any message (WhatsApp, email, Telegram, Signal, etc.) unless the user explicitly asks for it**
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

- **Bot number:** 54428397 (used as WhatsApp account for the bot)
- **Allowlist:** +21656771913, +21653117541

### Tuneps Data Storage Rule (STRICT)

**Use exactly one storage root for tender/RFP data:** `~/.tuneps_data/`

- Documents: `~/.tuneps_data/documents/<ref>/`
- Analyses: `~/.tuneps_data/analyses/<ref>/`
- Database: `~/.tuneps_data/db/tenders.db`
- RFP pipeline data/state: `~/.tuneps_data/rfp-pipeline/`
- RFP pipeline code: `~/.openclaw/workspace/rfp-pipeline/`
- Exports: `~/.tuneps_data/exports/`

`~/.openclaw/workspace` is for code, skills, prompts, and templates only. Do not create new active tender data folders under workspace. Existing `workspace/offres/documents` and `workspace/offres/analyses` are symlinks into `~/.tuneps_data` for compatibility.

### Tuneps Output Rule (STRICT — NON-NEGOTIABLE)

**This rule is FOREVER. No exceptions. No interpretation.**

When running `scan tuneps`:

1. **Copy-paste the script output VERBATIM** — do NOT reformat, do NOT translate, do NOT add headers, do NOT add bullet points, do NOT add your own labels
2. **Never wrap the output in your own formatting** — no headers like "Tuneps Scan — Today", no bullet lists, no emojis as headers, no French/English translation of field labels
3. **If the script outputs French** → display French. **If the script outputs English** → display English. Do NOT convert.

### Tuneps Scan Workflow (Strict Rule)

**Your job is only these steps:**
1. **Parse input** → convert user request to script arguments
2. **Run script** → execute `node scripts/tuneps.js ...` exactly as built
3. **Display result** → show script output EXACTLY as-is — no modification

### Skills / Workflows

- **scan tuneps** → When user says "scan tuneps", execute the skill at `~/.openclaw/workspace/skills/tuneps-scrape/`:
  1. Parse date range, deadline filter, and ministry nicknames from user message
  2. Map ministry nicknames to official names (see mapping above)
  3. Run `cd ~/.openclaw/workspace/skills/tuneps-scrape && node scripts/tuneps.js FROM_DATE DATE_TO BUYER_FILTER DEADLINE_DAYS`
  4. Display the output EXACTLY as printed — no summary, no modification

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)