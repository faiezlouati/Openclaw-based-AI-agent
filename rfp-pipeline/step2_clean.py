"""
step2_clean.py

7-stage cleaning pipeline for RFP Markdown documents produced by step1_parse.py.
Generic -- works on any French, Arabic, or mixed-language procurement document.

Stages (applied in order):
  1. Fix encoding (ftfy + Unicode normalisation)
  2. Detect word concatenation (warn only)
  3. Merge split document titles
  4. Merge tables split at page breaks
  5. Clean diagram blocks
  6. Normalise whitespace and structure
  7. Remove page headers / footers

Outputs per file:
  output/<base>_cleaned.md
  output/<base>_metadata.json

Run after step1_parse.py.
"""

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

try:
    import ftfy
except ImportError:
    print("ERROR: ftfy not installed.  Run: pip install ftfy")
    sys.exit(1)

OUTPUT_DIR = Path("output")


# ─── Table helpers ─────────────────────────────────────────────────────────────

def is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def is_separator_row(line: str) -> bool:
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return False
    cells = [c.strip() for c in s.split("|") if c.strip()]
    return bool(cells) and all(re.match(r"^:?-+:?$", c) for c in cells)


def count_table_columns(block: list) -> int:
    # Use the separator row first (always clean — no content to confuse)
    for line in block:
        if is_separator_row(line):
            return line.strip().count("|") - 1
    # Fall back: total pipe count on first row
    for line in block:
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            return s.count("|") - 1
    return 0


def _col1(row: str) -> str:
    cells = [c.strip() for c in row.split("|") if c.strip()]
    return cells[0].lower() if cells else ""


def get_data_rows(block: list) -> list:
    sep = next((i for i, l in enumerate(block) if is_separator_row(l)), -1)
    return block[sep + 1:] if sep != -1 else block


def get_merge_rows(table1: list, table2: list) -> list:
    """
    Rows from table2 to append to table1 when merging.
    - Duplicate header + separator  -> skip both, keep only data rows.
    - Continuation data + separator -> keep data row, drop separator only.
    """
    t1_col1 = ""
    for line in table1:
        if not is_separator_row(line):
            t1_col1 = _col1(line)
            break

    sep_idx = next((i for i, l in enumerate(table2) if is_separator_row(l)), -1)

    if sep_idx == -1:
        return table2
    if sep_idx == 0:
        return table2[1:]

    t2_col1 = _col1(table2[0])
    if t1_col1 and t2_col1 == t1_col1:
        return table2[sep_idx + 1:]
    else:
        return table2[:sep_idx] + table2[sep_idx + 1:]


def _parse_segments(lines: list) -> list:
    segments = []
    i = 0
    while i < len(lines):
        if is_table_line(lines[i]):
            start, block = i + 1, []
            while i < len(lines) and is_table_line(lines[i]):
                block.append(lines[i])
                i += 1
            segments.append({"type": "table", "lines": block, "lineno": start})
        else:
            start, block = i + 1, []
            while i < len(lines) and not is_table_line(lines[i]):
                block.append(lines[i])
                i += 1
            segments.append({"type": "gap", "lines": block, "lineno": start})
    return segments


# ─── Stage 1: Fix encoding ─────────────────────────────────────────────────────

def stage1_fix_encoding(text: str) -> str:
    text = ftfy.fix_text(text)
    text = unicodedata.normalize("NFC", text)
    replacements = [
        ("­", ""),   # soft hyphen
        (" ", " "),  # non-breaking space
        ("​", ""),   # zero-width space
        ("‌", ""),   # zero-width non-joiner
        ("‍", ""),   # zero-width joiner
        ("﻿", ""),   # BOM
        ("\u200E", ""),   # LRM
        ("\u200F", ""),   # RLM
    ]
    for bad, good in replacements:
        text = text.replace(bad, good)
    return text


# ─── Stage 2: Detect word concatenation ───────────────────────────────────────

def stage2_detect_concatenation(lines: list) -> list:
    warnings = []
    seen = set()

    for lineno, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue

        content = (
            " ".join(c.strip() for c in s.split("|") if c.strip())
            if s.startswith("|")
            else s
        )

        tokens = re.split(r"[^A-Za-zÀ-ɏ؀-ۿ]+", content)

        for token in tokens:
            if len(token) < 10:
                continue
            key = f"{lineno}:{token}"
            if key in seen:
                continue

            # Pattern A: 3+ lowercase letters followed by uppercase mid-word
            if re.search(r"[a-zà-ɏ]{3}[A-ZÀ-Þ]", token):
                seen.add(key)
                warnings.append(
                    f"Word concatenation detected at line {lineno}: {token}"
                )
                continue

            # Pattern B: very long token (>= 25 chars) with substantial lowercase content
            if len(token) >= 25:
                lower_count = sum(1 for c in token if c.islower())
                if lower_count >= 5:
                    seen.add(key)
                    warnings.append(
                        f"Word concatenation detected at line {lineno}: {token}"
                    )

    return warnings


# ─── Stage 3: Merge split document titles ──────────────────────────────────────

def stage3_merge_split_titles(lines: list) -> tuple:
    changes = []
    SCAN = min(20, len(lines))
    result = list(lines)

    def parse_heading(line):
        m = re.match(r"^(#{1,3}) (.+)$", line.strip())
        return (m.group(1), m.group(2).strip()) if m else None

    def is_continuation(title):
        if len(title.split()) >= 8:
            return False
        # Exclude numbered sections and French/Arabic article keywords
        return not re.match(r"^\d+[.)]\s|^Article\s|^الفصل\s|^المادة\s|^الباب\s|^:", title)

    def next_heading_idx(res, after, limit):
        j = after
        while j < limit and j < len(res) and res[j].strip() == "":
            j += 1
        return j if j < limit and j < len(res) else -1

    i = 0
    while i < SCAN and i < len(result):
        h = parse_heading(result[i])
        if not h:
            i += 1
            continue
        level, title = h

        j = next_heading_idx(result, i + 1, SCAN)
        if j == -1:
            break

        h2 = parse_heading(result[j])
        if not h2 or h2[0] != level or not is_continuation(h2[1]):
            i += 1
            continue

        merged = f"{level} {title} {h2[1]}"

        # Check for 3-part title
        k = next_heading_idx(result, j + 1, SCAN)
        if k != -1:
            h3 = parse_heading(result[k])
            if h3 and h3[0] == level and is_continuation(h3[1]):
                orig = (
                    f"'{result[i].strip()}' + '{result[j].strip()}'"
                    f" + '{result[k].strip()}'"
                )
                merged = f"{level} {title} {h2[1]} {h3[1]}"
                changes.append(f"Merged 3-part title: {orig} -> '{merged}'")
                result[i] = merged
                del result[i + 1 : k + 1]
                SCAN -= k - i
                i += 1
                continue

        orig = f"'{result[i].strip()}' + '{result[j].strip()}'"
        changes.append(f"Merged title: {orig} -> '{merged}'")
        result[i] = merged
        del result[i + 1 : j + 1]
        SCAN -= j - i
        i += 1

    return result, changes


# ─── Stage 4: Merge tables split at page breaks ────────────────────────────────

def stage4_merge_split_tables(lines: list) -> tuple:
    changes = []
    warned_pairs: set = set()   # track (t1.lineno, t2.lineno) to avoid duplicate warnings
    segments = _parse_segments(lines)

    changed = True
    while changed:
        changed = False
        new_segs = []
        j = 0
        while j < len(segments):
            if (
                j + 2 < len(segments)
                and segments[j]["type"] == "table"
                and segments[j + 1]["type"] == "gap"
                and segments[j + 2]["type"] == "table"
            ):
                t1, gap, t2 = segments[j], segments[j + 1], segments[j + 2]
                blank_count = sum(1 for l in gap["lines"] if not l.strip())

                # A gap is "clean" if it contains only blank lines and isolated
                # page-number artefacts (single digits, "Page X de Y", etc.)
                def is_page_artefact(s: str) -> bool:
                    s = s.strip()
                    return (
                        re.fullmatch(r"\d{1,3}", s) is not None
                        or bool(re.match(r"(?i)^page\s+\d+", s))
                        or bool(re.match(r"^صفحة\s+\d+", s))
                    )

                non_structural = [l for l in gap["lines"]
                                  if l.strip() and not is_page_artefact(l)]
                if not non_structural and blank_count <= 5:
                    cols1 = count_table_columns(t1["lines"])
                    cols2 = count_table_columns(t2["lines"])

                    if cols1 > 0 and cols1 == cols2:
                        merge_rows = get_merge_rows(t1["lines"], t2["lines"])
                        r1 = len(get_data_rows(t1["lines"]))
                        r2 = len(merge_rows)
                        msg = (
                            f"Merged table at line {t1['lineno']} "
                            f"({cols1} columns, {r1}+{r2} rows -> {r1 + r2} rows)"
                        )
                        changes.append(msg)
                        new_segs.append({
                            "type": "table",
                            "lines": t1["lines"] + merge_rows,
                            "lineno": t1["lineno"],
                        })
                        j += 3
                        changed = True
                        continue
                    elif cols1 != cols2:
                        pair = (t1["lineno"], t2["lineno"])
                        if pair not in warned_pairs:
                            warned_pairs.add(pair)
                            changes.append(
                                f"WARNING: skipped table merge at line {t2['lineno']} "
                                f"-- column count mismatch ({cols1} vs {cols2})"
                            )
            new_segs.append(segments[j])
            j += 1
        segments = new_segs

    result = []
    for seg in segments:
        result.extend(seg["lines"])
    return result, changes


# ─── Stage 5: Clean diagram blocks ────────────────────────────────────────────

def stage5_clean_diagrams(text: str) -> str:
    def normalize_diagram(m):
        inner = re.sub(r"\n{3,}", "\n\n", m.group(1)).strip()
        return f"[DIAGRAM START]\n{inner}\n[DIAGRAM END]"

    text = re.sub(
        r"\[DIAGRAM START\](.*?)\[DIAGRAM END\]",
        normalize_diagram,
        text,
        flags=re.DOTALL,
    )
    text = text.replace("<!-- image -->", "[DIAGRAM: image could not be processed]")
    return text


# ─── Stage 6: Normalise whitespace and structure ───────────────────────────────

def stage6_normalize_whitespace(lines: list) -> list:
    def normalize_bullets(line):
        if is_table_line(line) or line.strip().startswith("#"):
            return line.rstrip()
        return re.sub(r"^(\s*)[*+](\s+)", r"\1-\2", line).rstrip()

    lines = [normalize_bullets(l) for l in lines]

    # Collapse 3+ blank lines to 2
    result = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                result.append("")
        else:
            blank_run = 0
            result.append(line)

    # Reduce 2+ blank lines before a heading to 1
    result2 = []
    for line in result:
        if line.strip().startswith("#"):
            while len(result2) > 1 and result2[-1] == "" and result2[-2] == "":
                result2.pop()
        result2.append(line)

    # Reduce 2+ blank lines after a heading to 1
    result3 = []
    i = 0
    while i < len(result2):
        result3.append(result2[i])
        if result2[i].strip().startswith("#"):
            j = i + 1
            while j < len(result2) and result2[j].strip() == "":
                j += 1
            if j > i + 2:           # more than one blank after heading
                result3.append("")  # keep exactly one blank
                i = j
                continue
        i += 1

    return result3


# ─── Post-stage blank recompression ──────────────────────────────────────────

def _recompress_blanks(lines: list) -> list:
    """Collapse blank sequences that stage7 line-removal may have created.

    Stage6 normalises blanks, then stage7 removes page numbers/headers.
    Removing a line between two blank lines creates an accidental double-blank.
    This pass restores the invariants: max 2 blanks anywhere, max 1 before a heading.
    """
    out, run = [], 0
    for line in lines:
        if line.strip() == "":
            run += 1
            if run <= 2:
                out.append("")
        else:
            run = 0
            out.append(line)

    result = []
    for line in out:
        if line.strip().startswith("#"):
            while len(result) > 1 and result[-1] == "" and result[-2] == "":
                result.pop()
        result.append(line)
    return result


# ─── Stage 7: Remove page headers / footers ───────────────────────────────────

def stage7_remove_headers_footers(lines: list) -> list:
    counts = Counter()
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("|") or s.startswith("#") or s.startswith("[DIAGRAM"):
            continue
        if len(s.split()) < 10:
            counts[s] += 1

    to_remove = {s for s, c in counts.items() if c >= 3}

    result = []
    for line in lines:
        s = line.strip()
        if not s:
            result.append(line)
            continue
        if s.startswith("|") or s.startswith("#") or s.startswith("[DIAGRAM"):
            result.append(line)
            continue
        if s in to_remove:
            continue
        if re.fullmatch(r"\d{1,3}", s):
            continue
        if re.match(r"(?i)^page\s+\d+\s*(de|of|/)\s*\d+$", s):
            continue
        # Arabic page indicator: صفحة X من Y
        if re.match(r"^صفحة\s+\d+\s*(من|/)\s*\d+$", s):
            continue
        result.append(line)
    return result


# ─── Metadata extraction ──────────────────────────────────────────────────────

def detect_document_type(text: str) -> str:
    for region in (text[:2000], text):
        upper = region.upper()
        # French keywords
        if "CLAUSES ADMINISTRATIVES" in upper or "CCAP" in upper:
            return "CCAP"
        if "CLAUSES TECHNIQUES" in upper or "CCTP" in upper:
            return "CCTP"
        if "CAHIER DES CHARGES" in upper:
            return "CDC"
        # Arabic keywords — match core phrase; كراس may render as كر ّ اس
        if "الشروط الإدارية" in region:
            return "CCAP"
        if "الشروط التقنية" in region or "الشروط الفنية" in region:
            return "CCTP"
        if "كراس الشروط" in region:
            return "CDC"
    return "UNKNOWN"


def detect_language(text: str) -> str:
    arabic = len(re.findall(r"[؀-ۿ]", text))
    latin  = len(re.findall(r"[a-zA-ZÀ-ɏ]", text))
    total  = arabic + latin
    if total == 0:
        return "unknown"
    ratio = arabic / total
    if ratio > 0.60:
        return "ar"
    if ratio > 0.20:
        return "mixed"
    return "fr"


def extract_metadata(cleaned: str, source_file: str, warnings: list) -> dict:
    lines = cleaned.splitlines()

    table_count, in_table = 0, False
    for line in lines:
        if is_table_line(line) and not in_table:
            table_count += 1
            in_table = True
        elif not is_table_line(line):
            in_table = False

    diagram_count = cleaned.count("[DIAGRAM START]")
    sections = [l.strip() for l in lines if re.match(r"^#{1,3} \S", l)]
    word_count = len(re.sub(r"[|#*`_>~\[\]()\-]", " ", cleaned).split())

    return {
        "source_file":       source_file,
        "document_type":     detect_document_type(cleaned),
        "detected_language": detect_language(cleaned),
        "word_count":        word_count,
        "char_count":        len(cleaned),
        "section_count":     len(sections),
        "table_count":       table_count,
        "diagram_count":     diagram_count,
        "section_titles":    sections,
        "warnings":          warnings,
    }


# ─── Visualisation helpers ────────────────────────────────────────────────────

def _safe(s: str) -> str:
    return s.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)


def _show_merge_join(cleaned: str, table_changes: list) -> None:
    """Print rows around the midpoint of the first successfully merged table."""
    first = next((c for c in table_changes if c.startswith("Merged table")), None)
    if not first:
        return

    m = re.search(r"at line (\d+)", first)
    if not m:
        return
    target = int(m.group(1))

    # Collect the table block that starts at/near target line
    lines = cleaned.splitlines()
    in_t = False
    tbl_rows = []
    tbl_start = 0

    for i, line in enumerate(lines, 1):
        if is_table_line(line):
            if not in_t:
                in_t = True
                tbl_start = i
                if abs(tbl_start - target) <= 3:
                    tbl_rows = []
            if abs(tbl_start - target) <= 3:
                tbl_rows.append(line)
        else:
            in_t = False

    if len(tbl_rows) < 6:
        return

    pivot = len(tbl_rows) // 2
    window = tbl_rows[max(0, pivot - 3) : pivot + 3]

    print("\n  -- Merged table: rows around join point --")
    for row in window:
        print(_safe(f"    {row[:120]}"))


# ─── File processing ──────────────────────────────────────────────────────────

def process_file(parsed_path: Path) -> dict:
    print(f"\n{'-' * 60}")
    print(_safe(f"File       : {parsed_path.name}"))

    raw = parsed_path.read_text(encoding="utf-8")
    all_warnings = []

    text = stage1_fix_encoding(raw)
    lines = text.splitlines()

    concat_warnings = stage2_detect_concatenation(lines)
    all_warnings.extend(concat_warnings)

    lines, title_changes = stage3_merge_split_titles(lines)
    lines, table_changes = stage4_merge_split_tables(lines)

    text = stage5_clean_diagrams("\n".join(lines))
    lines = text.splitlines()
    lines = stage6_normalize_whitespace(lines)
    lines = stage7_remove_headers_footers(lines)
    lines = _recompress_blanks(lines)

    cleaned = "\n".join(lines).strip()

    base = parsed_path.stem
    if base.endswith("_parsed"):
        base = base[:-7]

    meta = extract_metadata(cleaned, parsed_path.name, all_warnings)
    merged_count = sum(1 for c in table_changes if c.startswith("Merged table"))

    cleaned_path  = OUTPUT_DIR / f"{base}_cleaned.md"
    metadata_path = OUTPUT_DIR / f"{base}_metadata.json"
    cleaned_path.write_text(cleaned, encoding="utf-8")
    metadata_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ── Summary line
    print(_safe(f"  Type     : {meta['document_type']}"))
    print(_safe(f"  Language : {meta['detected_language']}"))
    print(_safe(f"  Words    : {meta['word_count']:,}"))
    print(_safe(f"  Sections : {meta['section_count']}"))
    print(_safe(f"  Tables   : {meta['table_count']} ({merged_count} merged from split pairs)"))
    print(_safe(f"  Diagrams : {meta['diagram_count']}"))
    print(_safe(f"  Warnings : {len(all_warnings)} (word concatenation)"))
    print(_safe(f"  Saved to : {cleaned_path.name}"))

    # ── Title merge details
    if title_changes:
        print("\n  -- Title merges --")
        for c in title_changes:
            print(_safe(f"    {c}"))

    # ── Table merge details
    if table_changes:
        print("\n  -- Table merges --")
        for c in table_changes:
            print(_safe(f"    {c}"))

    # ── Join point visualisation
    _show_merge_join(cleaned, table_changes)

    # ── Metadata JSON (without section_titles to keep output concise)
    print("\n  -- Metadata JSON --")
    preview = {k: v for k, v in meta.items() if k != "section_titles"}
    print(_safe(json.dumps(preview, ensure_ascii=False, indent=4)))

    return meta


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    if not OUTPUT_DIR.exists():
        print(f"ERROR: '{OUTPUT_DIR}' not found. Run step1_parse.py first.")
        return

    files = sorted(OUTPUT_DIR.glob("*_parsed.md"))
    if not files:
        print(f"No *_parsed.md files in {OUTPUT_DIR}/. Run step1_parse.py first.")
        return

    print("=" * 60)
    print(f"  step2_clean.py  --  {len(files)} file(s) to process")
    print("=" * 60)

    ok = failed = 0
    for path in files:
        try:
            process_file(path)
            ok += 1
        except Exception as exc:
            print(f"  ERROR: {path.name}: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  Done: {ok} succeeded, {failed} failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
