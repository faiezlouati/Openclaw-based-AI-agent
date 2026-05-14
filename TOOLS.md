# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your specifics — the stuff that's unique to your setup.

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
- `présidence` → **Présidence du Gouvernement**
- `CCK` → **Centre de Calcul El-Khawarizmi**
- _(add more as you discover them)_

### Tuneps Scan Workflow (Strict Rule)

**Your job is only 3 steps:**
1. **Parse input** → convert user request to script arguments
2. **Run script** → execute `node scripts/tuneps.js ...` exactly as built
3. **Display result** → show script output as-is, no modification

**Never:**
- Re-run script to verify or debug
- Run additional ad-hoc queries to check results
- Second-guess the output or dig deeper

If the result is 0 tenders, that's the result. Move on.

### Skills / Workflows

- **scan tuneps** → When user says "scan tuneps", execute the skill at `~/.openclaw/workspace/skills/tuneps-scrape/`:
  1. Parse date range, deadline filter, and ministry nicknames from user message
  2. Map ministry nicknames to official names (see mapping above)
  3. Run `cd ~/.openclaw/workspace/skills/tuneps-scrape && node scripts/tuneps.js FROM_DATE DATE_TO BUYER_FILTER DEADLINE_DAYS`
  4. Display the output exactly as printed — no summary, no modification

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)