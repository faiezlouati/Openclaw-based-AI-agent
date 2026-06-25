

import json
import os
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT        = Path(__file__).parent
OUTPUT_DIR  = Path(os.environ.get("RFP_OUTPUT_DIR", ROOT / "output"))
CHROMA_DIR  = Path(os.environ.get("RFP_CHROMA_DIR", ROOT / "chroma_db"))
CONFIG_DIR  = Path(os.environ.get("RFP_CONFIG_DIR", ROOT / "config"))

MODEL_NAME      = "paraphrase-multilingual-mpnet-base-v2"
COLLECTION_NAME = "rfp_chunks"
GROQ_MODEL      = "llama-3.3-70b-versatile"
MAX_CHUNKS      = 20
TOP_K_PER_QUERY = 7


def load_config() -> tuple[dict, dict]:
    with open(CONFIG_DIR / "company_profile.json", encoding="utf-8") as f:
        profile = json.load(f)
    with open(CONFIG_DIR / "analysis_prompts.json", encoding="utf-8") as f:
        prompts = json.load(f)
    return profile, prompts



def discover_tenders() -> dict[str, list[str]]:
    """Return {tender_id: [source_file, ...]} — all documents grouped as one offer."""
    tenders: dict[str, list[str]] = {}
    for path in sorted(OUTPUT_DIR.glob("*_chunks.json")):
        with open(path, encoding="utf-8") as f:
            chunks = json.load(f)
        if not chunks:
            continue
        source = chunks[0].get("source_file", path.name)
        stem = Path(source).stem
        for suffix in ("_cleaned", "_parsed"):
            stem = stem.replace(suffix, "")
        if stem not in tenders:
            tenders[stem] = []
        tenders[stem].append(source)
    return tenders



def load_query_embeddings() -> dict:
    path = OUTPUT_DIR / "_rag_query_embeddings.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("model") == MODEL_NAME and data.get("queries") and data.get("embeddings"):
            print(f"Using cached query embeddings: {path.name}")
            return dict(zip(data["queries"], data["embeddings"]))
    except Exception as exc:
        print(f"  [WARN] Could not load cached query embeddings: {exc}")
    return {}


def retrieve_chunks(
    collection,
    embed_model,
    query_embeddings: dict,
    queries: list,
    tender_files: list,
) -> list:
    seen_ids = set()
    retrieved = []

    for query in queries:
        embedding = query_embeddings.get(query)
        if embedding is None:
            if embed_model is None:
                print(f"  [WARN] No embedding available for query: {query}")
                continue
            embedding = embed_model.encode([query])[0].tolist()
        try:
            where = {"source_file": {"$in": tender_files}} if len(tender_files) < collection.count() else None
            kwargs: dict = dict(
                query_embeddings=[embedding],
                n_results=min(TOP_K_PER_QUERY, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
            if where:
                kwargs["where"] = where
            results = collection.query(**kwargs)
        except Exception as e:
            print(f"  [WARN] Query failed: {e}")
            continue

        ids       = results.get("ids", [[]])[0]
        docs      = results.get("documents", [[]])[0]
        metas     = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for cid, doc, meta, dist in zip(ids, docs, metas, distances):
            if cid not in seen_ids:
                seen_ids.add(cid)
                retrieved.append({
                    "chunk_id":      cid,
                    "section_title": meta.get("section_title", ""),
                    "document_type": meta.get("document_type", ""),
                    "text":          doc,
                    "distance":      dist,
                })

    retrieved.sort(key=lambda x: x.get("section_title", ""))
    return retrieved[:MAX_CHUNKS]



def build_user_prompt(
    profile: dict,
    prompts: dict,
    tender_id: str,
    doc_types: list[str],
    chunks: list[dict],
) -> str:
    lines_text = "\n".join(
        f"  - {pl['name']}: {', '.join(pl['keywords'][:8])} ..."
        for pl in profile["product_lines"]
    )

    def _trim(text: str, max_words: int = 300) -> str:
        words = text.split()
        return " ".join(words[:max_words]) + (" …" if len(words) > max_words else "")

    chunks_text = "\n".join(
        f"[SECTION: {c['section_title']} | {c['document_type']}]\n{_trim(c['text'])}\n---"
        for c in chunks
    )

    return f"""Company: {profile["company_name"]}
Sector: {profile["sector"]}

Product lines we bid on:
{lines_text}

Exclusion keywords (auto-disqualify if dominant):
{", ".join(profile["exclusion_keywords"][:20])}

Scoring guidance:
{prompts["scoring_guidance"]}

Tender documents to analyze:
- Reference: {tender_id}
- Documents: {", ".join(sorted(set(doc_types)))}

Extracted content ({len(chunks)} sections):
---
{chunks_text}
---

{prompts["output_schema_description"]}"""



def call_groq(client: Groq, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return response.choices[0].message.content.strip()


def parse_llm_response(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text.strip())
    return json.loads(text.strip())


REQUIRED_KEYS = {
    "relevant", "relevance_score", "relevance_level",
    "matched_product_lines", "key_requirements",
    "summary", "recommendation", "recommendation_reason",
}

def validate_analysis(data: dict) -> bool:
    return REQUIRED_KEYS.issubset(data.keys())


def analyse_tender(
    client: Groq,
    profile: dict,
    prompts: dict,
    collection,
    embed_model,
    query_embeddings: dict,
    tender_id: str,
    tender_files: list,
) -> dict:
    print(f"  Retrieving chunks from ChromaDB …")
    chunks = retrieve_chunks(collection, embed_model, query_embeddings, profile["rag_queries"], tender_files)
    print(f"  Retrieved {len(chunks)} chunks (deduped, max {MAX_CHUNKS})")

    doc_types = [c["document_type"] for c in chunks]
    user_msg  = build_user_prompt(profile, prompts, tender_id, doc_types, chunks)

    print(f"  Calling Groq ({GROQ_MODEL}) …")
    raw = call_groq(client, prompts["system_prompt"], user_msg)

    try:
        analysis = parse_llm_response(raw)
        if not validate_analysis(analysis):
            raise ValueError(f"Missing keys: {REQUIRED_KEYS - set(analysis.keys())}")
    except Exception as e:
        print(f"  [WARN] Parse failed ({e}), retrying with simplified prompt …")
        retry_msg = (
            "The previous response was not valid JSON. "
            "Return ONLY a JSON object with keys: "
            "relevant, relevance_score, relevance_level, matched_product_lines, "
            "key_requirements, summary, recommendation, recommendation_reason.\n\n"
            + user_msg
        )
        raw2 = call_groq(client, prompts["system_prompt"], retry_msg)
        try:
            analysis = parse_llm_response(raw2)
            if not validate_analysis(analysis):
                raise ValueError(f"Missing keys after retry: {REQUIRED_KEYS - set(analysis.keys())}")
        except Exception as e2:
            print(f"  [ERROR] Both LLM attempts failed: {e2}")
            analysis = {"error": str(e2), "raw_response": raw2}

    return {
        "tender_id":           tender_id,
        "bid_no":              tender_id,
        "documents_analysed":  sorted(set(doc_types)),
        "chunks_retrieved":    len(chunks),
        "analysis":            analysis,
        "analysed_at":         datetime.now(timezone.utc).isoformat(),
    }



_COLOR_BID    = "#2E7D32"
_COLOR_REVIEW = "#F57C00"
_COLOR_SKIP   = "#C62828"
_COLOR_BLUE   = "#1565C0"

def _rec_color(rec: str) -> str:
    return {
        "BID":    _COLOR_BID,
        "REVIEW": _COLOR_REVIEW,
        "SKIP":   _COLOR_SKIP,
    }.get(rec.upper(), _COLOR_BLUE)


def _score_color(score: int) -> str:
    if score >= 70:   return _COLOR_BID
    if score >= 40:   return _COLOR_REVIEW
    return _COLOR_SKIP


def _score_bar(score: int) -> str:
    color = _score_color(score)
    return (
        f'<div style="background:#e0e0e0;border-radius:4px;height:12px;width:200px;display:inline-block;vertical-align:middle;">'
        f'<div style="background:{color};width:{score}%;height:100%;border-radius:4px;"></div>'
        f'</div> <span style="color:{color};font-weight:bold;">{score}/100</span>'
    )


def _fmt_product_lines(matched: list) -> str:
    if not matched:
        return "<p style='color:#777;'>None matched.</p>"
    rows = []
    for item in matched:
        if isinstance(item, dict):
            name  = item.get("name", str(item))
            score = int(item.get("score", item.get("relevance_score", 0)))
            evidence = item.get("evidence", item.get("reason", ""))
        else:
            name, score, evidence = str(item), 0, ""
        rows.append(
            f"<tr><td style='padding:8px;font-weight:bold;'>{name}</td>"
            f"<td style='padding:8px;'>{_score_bar(score)}</td>"
            f"<td style='padding:8px;color:#555;font-size:0.9em;'>{evidence}</td></tr>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;'>"
        "<thead><tr style='background:#f5f5f5;'>"
        "<th style='padding:8px;text-align:left;'>Product Line</th>"
        "<th style='padding:8px;text-align:left;'>Score</th>"
        "<th style='padding:8px;text-align:left;'>Evidence</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _fmt_requirements(reqs: list) -> str:
    if not reqs:
        return "<p style='color:#777;'>None extracted.</p>"
    rows = []
    for req in reqs:
        if isinstance(req, dict):
            cat   = req.get("category", req.get("type", ""))
            name  = req.get("requirement", req.get("name", str(req)))
            qty   = req.get("quantity", req.get("qty", ""))
            spec  = req.get("technical_spec", req.get("spec", req.get("details", "")))
        else:
            cat, name, qty, spec = "", str(req), "", ""
        rows.append(
            f"<tr>"
            f"<td style='padding:8px;color:#1565C0;font-size:0.85em;font-weight:bold;'>{cat}</td>"
            f"<td style='padding:8px;'>{name}</td>"
            f"<td style='padding:8px;text-align:center;'>{qty}</td>"
            f"<td style='padding:8px;color:#555;font-size:0.9em;'>{spec}</td>"
            f"</tr>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;'>"
        "<thead><tr style='background:#f5f5f5;'>"
        "<th style='padding:8px;text-align:left;'>Category</th>"
        "<th style='padding:8px;text-align:left;'>Requirement</th>"
        "<th style='padding:8px;text-align:center;'>Qty</th>"
        "<th style='padding:8px;text-align:left;'>Technical Spec</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def generate_html(result: dict, profile: dict) -> str:
    a         = result["analysis"]
    tender_id = result["tender_id"]
    rec       = str(a.get("recommendation", "SKIP")).upper()
    score     = int(a.get("relevance_score", 0))
    level     = str(a.get("relevance_level", ""))
    summary   = str(a.get("summary", ""))
    rec_reason= str(a.get("recommendation_reason", ""))
    matched   = a.get("matched_product_lines", [])
    reqs      = a.get("key_requirements", [])
    rec_color = _rec_color(rec)
    sc_color  = _score_color(score)
    date_str  = result.get("analysed_at", "")[:10]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RFP Analysis — {tender_id}</title>
<style>
  body {{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:0;background:#fafafa;color:#212121;}}
  .header {{background:{_COLOR_BLUE};color:white;padding:24px 40px;}}
  .header h1 {{margin:0 0 4px 0;font-size:1.4em;}}
  .header p  {{margin:0;opacity:0.85;font-size:0.9em;}}
  .badge {{display:inline-block;padding:8px 20px;border-radius:4px;font-size:1.2em;
           font-weight:bold;color:white;background:{rec_color};margin-top:12px;}}
  .score-block {{display:inline-block;margin-left:24px;vertical-align:middle;}}
  .score-num {{font-size:3em;font-weight:bold;color:{sc_color};line-height:1;}}
  .score-label {{font-size:0.85em;color:#555;}}
  .section {{background:white;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,.1);
             margin:20px 40px;padding:20px 24px;}}
  .section h2 {{margin:0 0 12px 0;font-size:1.1em;color:{_COLOR_BLUE};
                border-bottom:2px solid {_COLOR_BLUE};padding-bottom:6px;}}
  .summary-text {{font-size:1em;line-height:1.6;color:#333;}}
  .reason {{background:#fff8e1;border-left:4px solid {_COLOR_REVIEW};
            padding:10px 14px;border-radius:0 4px 4px 0;
            font-size:0.95em;color:#555;margin-top:8px;}}
  table tr:nth-child(even) {{background:#fafafa;}}
  table tr:hover {{background:#e3f2fd;}}
  td,th {{border-bottom:1px solid #eee;}}
  .footer {{text-align:center;padding:20px;color:#aaa;font-size:0.8em;}}
</style>
</head>
<body>

<div class="header">
  <div style="max-width:1100px;margin:0 auto;">
    <p style="margin:0 0 4px 0;font-size:0.85em;opacity:0.7;">{profile["company_name"]} — Bid Analysis</p>
    <h1>Tender: {tender_id}</h1>
    <p>Documents: {", ".join(result.get("documents_analysed", []))} &nbsp;|&nbsp;
       Chunks analysed: {result.get("chunks_retrieved", 0)} &nbsp;|&nbsp;
       Date: {date_str}</p>
    <div>
      <span class="badge">{rec}</span>
      <span class="score-block">
        <div class="score-num">{score}</div>
        <div class="score-label">/ 100 &nbsp;·&nbsp; {level}</div>
      </span>
    </div>
  </div>
</div>

<div class="section">
  <h2>Summary</h2>
  <p class="summary-text">{summary}</p>
  <div class="reason"><strong>Recommendation reason:</strong> {rec_reason}</div>
</div>

<div class="section">
  <h2>Matched Product Lines</h2>
  {_fmt_product_lines(matched)}
</div>

<div class="section">
  <h2>Key Requirements Extracted</h2>
  {_fmt_requirements(reqs)}
</div>

<div class="footer">
  Generated by RFP Pipeline &nbsp;·&nbsp; {date_str}
</div>

</body>
</html>"""



ANSI = {
    "BID":    "\033[92m",  
    "REVIEW": "\033[93m",  
    "SKIP":   "\033[91m",  
    "RESET":  "\033[0m",
}

def print_summary(result: dict):
    a      = result["analysis"]
    rec    = str(a.get("recommendation", "SKIP")).upper()
    score  = a.get("relevance_score", 0)
    level  = a.get("relevance_level", "")
    matched= a.get("matched_product_lines", [])
    reqs   = a.get("key_requirements", [])

    matched_str = ", ".join(
        f"{m.get('name', m) if isinstance(m, dict) else m}"
        + (f" ({m.get('score', m.get('relevance_score', ''))})" if isinstance(m, dict) else "")
        for m in matched
    ) or "None"

    color = ANSI.get(rec, "")
    reset = ANSI["RESET"]

    print(f"\n{'='*60}")
    print(f"  Analysis Complete: {result['tender_id']}")
    print(f"{'='*60}")
    print(f"  Recommendation  : {color}{rec}{reset}")
    print(f"  Relevance Score : {score}/100")
    print(f"  Relevance Level : {level}")
    print(f"  Matched Lines   : {matched_str}")
    print(f"  Key Requirements: {len(reqs)} items extracted")
    print(f"  JSON saved to  : output/{result['tender_id']}_analysis.json")
    print(f"{'='*60}\n")



def main():
    load_dotenv(Path(os.environ.get("RFP_ENV_FILE", Path.home() / ".tuneps_data" / "rfp-pipeline" / ".env")))

    profile, prompts = load_config()
    print(f"Loaded profile: {profile['company_name']}")
    print(f"Product lines : {len(profile['product_lines'])}")
    print(f"RAG queries   : {len(profile['rag_queries'])}\n")

    query_embeddings = load_query_embeddings()
    embed_model = None
    if not query_embeddings:
        print(f"Loading embedding model: {MODEL_NAME} …")
        embed_model = SentenceTransformer(MODEL_NAME)
        print("  Model ready\n")
    else:
        print("Skipping embedding model load in step5; using query embeddings from step4.\n")

    print(f"Opening ChromaDB at: {CHROMA_DIR}")
    client_db  = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client_db.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"  {collection.count()} vectors in collection\n")

    tenders = discover_tenders()
    if not tenders:
        print("No tenders found in output/. Run step3 first.")
        sys.exit(1)
    print(f"Found {len(tenders)} tender(s): {list(tenders.keys())}\n")

    groq_client = Groq()

    for tender_id, tender_files in tenders.items():
        print(f"── Analysing: {tender_id}")
        try:
            result    = analyse_tender(
                groq_client, profile, prompts, collection, embed_model, query_embeddings,
                tender_id, tender_files,
            )
            json_path = OUTPUT_DIR / f"{tender_id}_analysis.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print_summary(result)

        except Exception as e:
            print(f"  [ERROR] {tender_id}: {e}\n")
            continue

    print("All tenders processed.")


if __name__ == "__main__":
    main()
