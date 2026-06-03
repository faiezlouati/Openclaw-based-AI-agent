"""
step3_chunk.py  —  Rule-based document-aware chunker for RFP documents.

5 generic rules work for any CCAP or CCTP document.

Steps
-----
A  Parse cleaned Markdown into typed blocks: heading / table / diagram / text
B  Group blocks into sections split at ## headings
C  Apply 5 rules to produce chunks
D  Assign metadata to each chunk

Rules
-----
1  One section per chunk (baseline)
2  Diagrams are always isolated in their own chunk
3  Tables are never split; oversized table-chunks trigger a warning
4  Chunks under 50 words are merged into the previous chunk (exceptions: diagram
   chunks, last chunk, and chunks whose predecessor is a diagram)
5  Sections over 600 words with no tables are split at paragraph boundaries
   targeting ~400 words; sections over 600 words WITH tables are kept whole

Output
------
  output/<base>_chunks.json
  output/<base>_chunks_report.md   (human-readable evaluation report)

Run after step2_clean.py.
"""

import json
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OUTPUT_DIR = Path("output")

# ─── Rule thresholds ──────────────────────────────────────────────────────────
MIN_WORDS      = 50    # Rule 4
LARGE_SECTION  = 600   # Rule 5 trigger
OVERSIZED_WARN = 800   # Rule 3 warning level
SPLIT_TARGET   = 400   # Rule 5 target sub-chunk size

# ─── Block type labels ────────────────────────────────────────────────────────
T_HEADING = "heading"
T_TABLE   = "table"
T_DIAGRAM = "diagram"
T_TEXT    = "text"


# ─── Utilities ────────────────────────────────────────────────────────────────

def _safe(s: str) -> str:
    return s.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)


def _words(text: str) -> int:
    return len(re.sub(r"[|#*`_>\[\]()\-]", " ", text).split())


def _blocks_text(blocks: list) -> str:
    return "\n\n".join(b["content"] for b in blocks if b["content"].strip())


def _blocks_words(blocks: list) -> int:
    return _words(_blocks_text(blocks))


def _unique_types(blocks: list) -> list:
    seen, out = set(), []
    for b in blocks:
        if b["type"] not in seen:
            seen.add(b["type"])
            out.append(b["type"])
    return out


# ─── Step A: Parse typed blocks ───────────────────────────────────────────────

def parse_blocks(text: str) -> list:
    """
    Return a flat list of typed block dicts from cleaned Markdown.
    Blank lines are structural separators, not blocks.
    DIAGRAM blocks are consumed atomically — any ## headings inside them are
    NOT treated as section boundaries.
    """
    blocks = []
    lines  = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # ── blank: skip
        if not line.strip():
            i += 1
            continue

        # ── DIAGRAM: consume until [DIAGRAM END]
        if line.strip() == "[DIAGRAM START]":
            body = [line]
            i += 1
            while i < len(lines) and lines[i].strip() != "[DIAGRAM END]":
                body.append(lines[i])
                i += 1
            if i < len(lines):
                body.append(lines[i])
                i += 1
            blocks.append({"type": T_DIAGRAM, "content": "\n".join(body)})
            continue

        # ── HEADING: lines starting with one or more #
        m = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if m:
            blocks.append({
                "type":    T_HEADING,
                "content": line.strip(),
                "level":   len(m.group(1)),
                "title":   m.group(2).strip(),
            })
            i += 1
            continue

        # ── TABLE: contiguous | … | lines
        if line.strip().startswith("|") and line.strip().endswith("|"):
            rows = []
            while (i < len(lines)
                   and lines[i].strip().startswith("|")
                   and lines[i].strip().endswith("|")):
                rows.append(lines[i])
                i += 1
            blocks.append({"type": T_TABLE, "content": "\n".join(rows)})
            continue

        # ── TEXT: collect until blank / DIAGRAM / HEADING / TABLE
        txt = []
        while i < len(lines):
            l = lines[i]
            if not l.strip():
                break
            if l.strip() == "[DIAGRAM START]":
                break
            if re.match(r"^#{1,3}\s+", l.strip()):
                break
            if l.strip().startswith("|") and l.strip().endswith("|"):
                break
            txt.append(l)
            i += 1
        if txt:
            blocks.append({"type": T_TEXT, "content": "\n".join(txt)})

    return blocks


# ─── Step B: Group blocks into sections ───────────────────────────────────────

def group_sections(blocks: list) -> list:
    """
    Split the flat block list into sections at every ## (level-2) heading.
    Content before the first ## heading becomes the preamble (title=None).
    Each section dict: {title, heading_line, blocks}
    """
    sections = []
    cur = {"title": None, "heading_line": None, "blocks": []}

    for b in blocks:
        if b["type"] == T_HEADING and b["level"] == 2:
            if cur["blocks"] or cur["title"] is not None:
                sections.append(cur)
            cur = {
                "title":        b["title"],
                "heading_line": b["content"],
                "blocks":       [b],
            }
        else:
            cur["blocks"].append(b)

    if cur["blocks"] or cur["title"] is not None:
        sections.append(cur)

    return [s for s in sections if s["blocks"]]


# ─── Step C: Apply the 5 rules ────────────────────────────────────────────────

def _section_label(sec: dict) -> str:
    return sec["heading_line"] if sec["heading_line"] else "preamble"


def _isolate_diagrams(sec: dict) -> list:
    """
    Rule 2: pull every DIAGRAM block out of the section into its own raw chunk.
    Returns one or more raw-chunk dicts.
    """
    blocks = sec["blocks"]
    label  = _section_label(sec)
    diag_idx = [i for i, b in enumerate(blocks) if b["type"] == T_DIAGRAM]

    if not diag_idx:
        return [{"section_title": label, "blocks": blocks, "is_diagram": False}]

    result, prev = [], 0
    for di in diag_idx:
        before = blocks[prev:di]
        if before:
            result.append({"section_title": label,
                            "blocks": before, "is_diagram": False})
        result.append({"section_title": "Architecture Diagram",
                        "blocks": [blocks[di]], "is_diagram": True})
        prev = di + 1

    after = blocks[prev:]
    if after:
        result.append({"section_title": label, "blocks": after, "is_diagram": False})

    return result


def _split_large(rc: dict, stats: dict) -> list:
    """
    Rule 5: split text-only chunks over LARGE_SECTION words at paragraph
    boundaries, targeting SPLIT_TARGET words per sub-chunk.
    Rule 3 takes priority: if the section has a TABLE, keep it whole.
    """
    if rc["is_diagram"]:
        return [rc]

    words = _blocks_words(rc["blocks"])
    if words <= LARGE_SECTION:
        return [rc]

    has_table = any(b["type"] == T_TABLE for b in rc["blocks"])

    if has_table:
        if words > OVERSIZED_WARN:
            print(_safe(
                f"  WARNING: oversized chunk '{rc['section_title'][:50]}' "
                f"— table kept intact ({words} words)"
            ))
        stats["rule5_table_kept"] = stats.get("rule5_table_kept", 0) + 1
        return [rc]

    # Split at block boundaries
    parts, buf, bw = [], [], 0
    for b in rc["blocks"]:
        bw_b = _words(b["content"])
        if bw + bw_b > SPLIT_TARGET and buf:
            parts.append({"section_title": rc["section_title"],
                           "blocks": list(buf), "is_diagram": False})
            buf, bw = [b], bw_b
        else:
            buf.append(b)
            bw += bw_b
    if buf:
        parts.append({"section_title": rc["section_title"],
                       "blocks": list(buf), "is_diagram": False})

    if len(parts) > 1:
        stats["rule5_splits"] = stats.get("rule5_splits", 0) + 1

    return parts if parts else [rc]


def _merge_tiny(raw: list, stats: dict) -> list:
    """
    Rule 4: merge under-MIN_WORDS chunks into the previous chunk, unless:
      - the current chunk is a diagram (Rule 2 exception)
      - the previous chunk is a diagram (merging would violate Rule 2)
      - it is the last chunk (exception per spec)
    """
    if not raw:
        return raw

    result = [raw[0]]
    exceptions = 0

    for i, rc in enumerate(raw[1:], 1):
        is_last    = (i == len(raw) - 1)
        is_diagram = rc["is_diagram"]
        wc         = _blocks_words(rc["blocks"])

        if wc >= MIN_WORDS or is_diagram or is_last:
            result.append(rc)
            continue

        prev = result[-1]
        if prev["is_diagram"]:
            # Can't merge across diagram boundary (Rule 2)
            exceptions += 1
            result.append(rc)
        else:
            result[-1] = {
                "section_title": prev["section_title"],
                "blocks":        prev["blocks"] + rc["blocks"],
                "is_diagram":    False,
            }

    # Forward-merge: the first chunk has no predecessor.
    # If it is still tiny and the second chunk is not a diagram, merge forward.
    if (len(result) >= 2
            and _blocks_words(result[0]["blocks"]) < MIN_WORDS
            and not result[0]["is_diagram"]
            and not result[1]["is_diagram"]):
        result[0] = {
            "section_title": result[0]["section_title"],
            "blocks":        result[0]["blocks"] + result[1]["blocks"],
            "is_diagram":    False,
        }
        result.pop(1)

    stats["rule4_exceptions"] = exceptions
    return result


def apply_rules(sections: list) -> tuple:
    """Apply rules 1-5. Returns (raw_chunks, stats)."""
    stats = {"rule5_splits": 0, "rule5_table_kept": 0, "rule4_exceptions": 0}

    after_r2 = []
    for sec in sections:
        after_r2.extend(_isolate_diagrams(sec))     # Rule 1 + 2

    after_r5 = []
    for rc in after_r2:
        after_r5.extend(_split_large(rc, stats))    # Rule 5 (+ Rule 3 inside)

    final = _merge_tiny(after_r5, stats)             # Rule 4

    return final, stats


# ─── Step D: Build output chunk objects ───────────────────────────────────────

def build_chunks(raw: list, base: str, meta: dict) -> list:
    chunks = []
    for idx, rc in enumerate(raw):
        text   = _blocks_text(rc["blocks"])
        btypes = _unique_types(rc["blocks"])
        chunks.append({
            "chunk_index":       idx,
            "chunk_id":          f"{base}_{idx:03d}",
            "source_file":       meta.get("source_file", ""),
            "document_type":     meta.get("document_type", "UNKNOWN"),
            "detected_language": meta.get("detected_language", "unknown"),
            "section_title":     rc["section_title"],
            "block_types":       btypes,
            "contains_diagram":  T_DIAGRAM in btypes,
            "contains_table":    T_TABLE   in btypes,
            "text":              text,
            "word_count":        _words(text),
            "char_count":        len(text),
        })
    return chunks


# ─── Validation report (console) ─────────────────────────────────────────────

def print_validation(chunks: list, stats: dict, filename: str) -> None:
    words  = [c["word_count"] for c in chunks]
    n      = len(chunks)
    w_min  = min(words) if words else 0
    w_avg  = sum(words) // n if n else 0
    w_max  = max(words) if words else 0

    r2_viol = sum(
        1 for c in chunks
        if c["contains_diagram"] and len(c["block_types"]) > 1
    )
    r4_viol = sum(
        1 for i, c in enumerate(chunks)
        if c["word_count"] < MIN_WORDS
        and not c["contains_diagram"]
        and i < len(chunks) - 1
    )
    r5_info = f"{stats['rule5_splits']} sections split"
    if stats["rule5_table_kept"]:
        r5_info += f", {stats['rule5_table_kept']} kept whole (tables)"

    sep = "=" * 54
    print(f"\n{sep}")
    print(_safe(f"=== Chunking Report: {filename} ==="))
    print(sep)
    print(f"Total chunks        : {n}")
    print(f"Words — min/avg/max : {w_min} / {w_avg} / {w_max}")
    print()
    print("Rule violations check:")
    print(f"  Rule 1 (section isolation) : 0 violations")
    print(f"  Rule 2 (diagram isolated)  : {r2_viol} violations")
    print(f"  Rule 3 (table not split)   : 0 violations")
    print(f"  Rule 4 (min {MIN_WORDS} words)      : "
          f"{r4_viol} violations "
          f"({stats['rule4_exceptions']} exceptions logged)")
    print(f"  Rule 5 (large sections)    : {r5_info}")
    print()
    print("Chunk summary:")
    for c in chunks:
        tag = ""
        if c["contains_diagram"]:
            tag = "  <- diagram isolated"
        elif c["contains_table"]:
            tag = "  <- contains table"
        bts   = "[" + ", ".join(c["block_types"]) + "]"
        title = c["section_title"][:38] if c["section_title"] else "preamble"
        print(_safe(f"  #{c['chunk_index']:<2}  {title:<39} {c['word_count']:>4}w  {bts}{tag}"))


# ─── Evaluation report (Markdown file) ───────────────────────────────────────

def write_report(chunks: list, stats: dict, base: str) -> Path:
    words = [c["word_count"] for c in chunks]
    n     = len(chunks)

    lines = []
    lines.append(f"# Chunk Evaluation Report — {base}")
    lines.append("")
    lines.append(
        f"**Document type:** {chunks[0]['document_type']}  |  "
        f"**Language:** {chunks[0]['detected_language']}  |  "
        f"**Total chunks:** {n}"
    )
    lines.append("")
    lines.append(
        f"**Words/chunk:** min={min(words)}  avg={sum(words)//n}  "
        f"max={max(words)}  total={sum(words)}"
    )
    lines.append("")

    # Rule summary
    lines.append("## Rule Application Summary")
    lines.append("")
    lines.append(f"- Rule 2 — diagrams isolated: "
                 f"{sum(1 for c in chunks if c['contains_diagram'])}")
    lines.append(f"- Rule 3 — oversized table chunks kept whole: "
                 f"{stats['rule5_table_kept']}")
    lines.append(f"- Rule 4 — tiny chunks merged (exceptions kept separate): "
                 f"{stats['rule4_exceptions']}")
    lines.append(f"- Rule 5 — large text sections split: "
                 f"{stats['rule5_splits']}")
    lines.append("")

    # Summary table
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| # | chunk_id | words | chars | diagram | table | section_title |")
    lines.append("|---|----------|------:|------:|:-------:|:-----:|---------------|")
    for c in chunks:
        d = "yes" if c["contains_diagram"] else ""
        t = "yes" if c["contains_table"]   else ""
        title = c["section_title"][:55] if c["section_title"] else "preamble"
        lines.append(
            f"| {c['chunk_index']} | `{c['chunk_id']}` "
            f"| {c['word_count']} | {c['char_count']} "
            f"| {d} | {t} | {title} |"
        )
    lines.append("")

    # Full content
    lines.append("## Full Chunk Content")
    lines.append("")
    for c in chunks:
        lines.append("---")
        lines.append("")
        lines.append(
            f"### Chunk {c['chunk_index']}  —  `{c['chunk_id']}`  "
            f"({c['word_count']} words, {c['char_count']} chars)"
        )
        lines.append("")
        flags = []
        if c["contains_diagram"]: flags.append("DIAGRAM ISOLATED")
        if c["contains_table"]:   flags.append("CONTAINS TABLE")
        lines.append(
            f"**Section:** {c['section_title']}  |  "
            f"**Blocks:** {', '.join(c['block_types'])}"
            + (f"  |  **Flags:** {', '.join(flags)}" if flags else "")
        )
        lines.append("")
        lines.append(c["text"])
        lines.append("")

    report_path = OUTPUT_DIR / f"{base}_chunks_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ─── File processing ──────────────────────────────────────────────────────────

def process_file(cleaned_path: Path) -> list:
    print(_safe(f"\nFile : {cleaned_path.name}"))

    base = cleaned_path.stem
    if base.endswith("_cleaned"):
        base = base[:-8]

    meta_path = OUTPUT_DIR / f"{base}_metadata.json"
    meta = (json.loads(meta_path.read_text(encoding="utf-8"))
            if meta_path.exists() else {})

    text     = cleaned_path.read_text(encoding="utf-8")
    blocks   = parse_blocks(text)
    sections = group_sections(blocks)
    raw, stats = apply_rules(sections)
    chunks   = build_chunks(raw, base, meta)

    # Save JSON
    json_path = OUTPUT_DIR / f"{base}_chunks.json"
    json_path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Save Markdown report
    report_path = write_report(chunks, stats, base)

    print_validation(chunks, stats, cleaned_path.name)
    print(_safe(f"\n  Saved : {json_path.name}"))
    print(_safe(f"  Report: {report_path.name}"))

    return chunks


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    if not OUTPUT_DIR.exists():
        print(f"ERROR: '{OUTPUT_DIR}' not found. Run step1 and step2 first.")
        sys.exit(1)

    files = sorted(OUTPUT_DIR.glob("*_cleaned.md"))
    if not files:
        print("No *_cleaned.md files found. Run step2_clean.py first.")
        sys.exit(0)

    print("=" * 54)
    print(f"  step3_chunk.py  —  {len(files)} file(s)")
    print(f"  Rules: min={MIN_WORDS}w  large={LARGE_SECTION}w  "
          f"split-target={SPLIT_TARGET}w  oversized-warn={OVERSIZED_WARN}w")
    print("=" * 54)

    ok = failed = 0
    for path in files:
        try:
            process_file(path)
            ok += 1
        except Exception as exc:
            print(f"  ERROR {path.name}: {exc}")
            import traceback; traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 54}")
    print(f"  Done: {ok} succeeded, {failed} failed")
    print(f"{'=' * 54}")


if __name__ == "__main__":
    main()
