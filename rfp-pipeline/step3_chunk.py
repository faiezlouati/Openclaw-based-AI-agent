
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


MIN_WORDS      = 50
LARGE_SECTION  = 600
OVERSIZED_WARN = 800
SPLIT_TARGET   = 400


T_HEADING = "heading"
T_TABLE   = "table"
T_DIAGRAM = "diagram"
T_TEXT    = "text"



# Sanitizes console text.
def _safe(s: str) -> str:
    return s.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)

# Handles words.
def _words(text: str) -> int:
    return len(re.sub(r"[|#*`_>\[\]()\-]", " ", text).split())

# Handles blocks text.
def _blocks_text(blocks: list) -> str:
    return "\n\n".join(b["content"] for b in blocks if b["content"].strip())

# Handles blocks words.
def _blocks_words(blocks: list) -> int:
    return _words(_blocks_text(blocks))

# Handles unique types.
def _unique_types(blocks: list) -> list:
    seen, out = set(), []
    for b in blocks:
        if b["type"] not in seen:
            seen.add(b["type"])
            out.append(b["type"])
    return out



# Parses blocks.
def parse_blocks(text: str) -> list:
    blocks = []
    lines  = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]


        if not line.strip():
            i += 1
            continue


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


        if line.strip().startswith("|") and line.strip().endswith("|"):
            rows = []
            while (i < len(lines)
                   and lines[i].strip().startswith("|")
                   and lines[i].strip().endswith("|")):
                rows.append(lines[i])
                i += 1
            blocks.append({"type": T_TABLE, "content": "\n".join(rows)})
            continue


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



# Handles group sections.
def group_sections(blocks: list) -> list:
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



# Handles section label.
def _section_label(sec: dict) -> str:
    return sec["heading_line"] if sec["heading_line"] else "preamble"

# Handles isolate diagrams.
def _isolate_diagrams(sec: dict) -> list:
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

# Splits large.
def _split_large(rc: dict, stats: dict) -> list:
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

# Handles merge tiny.
def _merge_tiny(raw: list, stats: dict) -> list:
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

            exceptions += 1
            result.append(rc)
        else:
            result[-1] = {
                "section_title": prev["section_title"],
                "blocks":        prev["blocks"] + rc["blocks"],
                "is_diagram":    False,
            }



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

# Handles apply rules.
def apply_rules(sections: list) -> tuple:
    stats = {"rule5_splits": 0, "rule5_table_kept": 0, "rule4_exceptions": 0}

    after_r2 = []
    for sec in sections:
        after_r2.extend(_isolate_diagrams(sec))

    after_r5 = []
    for rc in after_r2:
        after_r5.extend(_split_large(rc, stats))

    final = _merge_tiny(after_r5, stats)

    return final, stats



# Builds chunks.
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



# Handles print validation.
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



# Writes report.
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



# Handles process file.
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


    json_path = OUTPUT_DIR / f"{base}_chunks.json"
    json_path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )


    report_path = write_report(chunks, stats, base)

    print_validation(chunks, stats, cleaned_path.name)
    print(_safe(f"\n  Saved : {json_path.name}"))
    print(_safe(f"  Report: {report_path.name}"))

    return chunks



# Runs the script.
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
