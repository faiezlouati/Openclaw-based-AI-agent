

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

ROOT       = Path(__file__).parent
OUTPUT_DIR = Path(os.environ.get("RFP_OUTPUT_DIR", ROOT / "output"))
CHROMA_DIR = Path(os.environ.get("RFP_CHROMA_DIR", ROOT / "chroma_db"))
CONFIG_DIR = Path(os.environ.get("RFP_CONFIG_DIR", ROOT / "config"))
CACHE_DIR  = Path(os.environ.get("RFP_CACHE_DIR", Path.home() / ".tuneps_data" / "rfp-pipeline" / "cache"))

COLLECTION_NAME = "rfp_chunks"
MODEL_NAME      = "paraphrase-multilingual-mpnet-base-v2"



def load_chunks(json_path: Path) -> list[dict]:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("chunks", [])


def embed_text(chunk: dict) -> str:
    title = chunk.get("section_title") or ""
    text  = chunk.get("text") or ""
    if title:
        return f"{title}\n\n{text}"
    return text


def chunk_to_metadata(chunk: dict) -> dict:
    """Extract scalar fields only — ChromaDB metadata values must be str/int/float/bool."""
    return {
        "chunk_index":      int(chunk.get("chunk_index", 0)),
        "source_file":      str(chunk.get("source_file", "")),
        "document_type":    str(chunk.get("document_type", "")),
        "detected_language":str(chunk.get("detected_language", "")),
        "section_title":    str(chunk.get("section_title") or ""),
        "contains_diagram": bool(chunk.get("contains_diagram", False)),
        "contains_table":   bool(chunk.get("contains_table", False)),
        "word_count":       int(chunk.get("word_count", 0)),
    }


def query_embedding_cache_path() -> Path:
    profile_path = CONFIG_DIR / "company_profile.json"
    if not profile_path.exists():
        return CACHE_DIR / "query_embeddings" / MODEL_NAME / "missing-profile.json"
    digest = hashlib.sha256(profile_path.read_bytes()).hexdigest()[:16]
    safe_model = MODEL_NAME.replace("/", "_")
    return CACHE_DIR / "query_embeddings" / safe_model / f"{digest}.json"


def restore_query_embeddings() -> bool:
    src = query_embedding_cache_path()
    if not src.exists():
        return False
    dst = OUTPUT_DIR / "_rag_query_embeddings.json"
    shutil.copy2(src, dst)
    print(f"Restored cached query embeddings: {dst.name}")
    return True


def save_query_embeddings(model: SentenceTransformer) -> None:
    """Precompute RAG query embeddings so step5 can avoid loading the model again."""
    profile_path = CONFIG_DIR / "company_profile.json"
    if not profile_path.exists():
        return
    try:
        with open(profile_path, encoding="utf-8") as f:
            profile = json.load(f)
        queries = profile.get("rag_queries", [])
        if not queries:
            return
        out_path = OUTPUT_DIR / "_rag_query_embeddings.json"
        embeddings = model.encode(queries, show_progress_bar=False, batch_size=32).tolist()
        payload = {"model": MODEL_NAME, "queries": queries, "embeddings": embeddings}
        out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cache_path = query_embedding_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(f"Saved query embeddings: {out_path.name}")
    except Exception as exc:
        print(f"[WARN] Could not save query embeddings: {exc}")



def main():
    chunk_files = sorted(OUTPUT_DIR.glob("*_chunks.json"))
    if not chunk_files:
        print("No *_chunks.json files found in output/. Run step3 first.")
        sys.exit(1)

    print(f"Opening ChromaDB at: {CHROMA_DIR}")
    CHROMA_DIR.mkdir(exist_ok=True)
    client     = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    existing_ids: set[str] = set(collection.get(include=[])["ids"])
    print(f"  Collection '{COLLECTION_NAME}' — {len(existing_ids)} existing vectors\n")

    planned = []
    total_chunks = 0
    for json_path in chunk_files:
        chunks = load_chunks(json_path)
        if not chunks:
            print(f"[SKIP] {json_path.name} — empty or unreadable")
            continue
        new_chunks = [c for c in chunks if str(c.get("chunk_id", "")) not in existing_ids]
        planned.append((json_path, chunks, new_chunks))
        total_chunks += len(chunks)

    if planned and not any(new_chunks for _, _, new_chunks in planned):
        for json_path, chunks, _ in planned:
            print(f"[{json_path.name}]  {len(chunks)} chunks")
            print(f"  All {len(chunks)} chunks already in DB — skipping\n")
        if restore_query_embeddings():
            print("No new chunks and query embeddings cached — skipping embedding model load")
            print("─" * 60)
            print(f"Done.  Added: 0  |  Already existed: {total_chunks}")
            print(f"Collection total: {collection.count()} vectors")
            print(f"ChromaDB path: {CHROMA_DIR.resolve()}")
            return

    print(f"Loading model: {MODEL_NAME} …")
    t0 = time.time()
    model = SentenceTransformer(MODEL_NAME)
    print(f"  Model loaded in {time.time() - t0:.1f}s\n")

    total_added = total_skipped = 0

    for json_path, chunks, new_chunks in planned:
        print(f"[{json_path.name}]  {len(chunks)} chunks")

        if not new_chunks:
            print(f"  All {len(chunks)} chunks already in DB — skipping\n")
            total_skipped += len(chunks)
            continue

        texts    = [embed_text(c) for c in new_chunks]
        ids      = [str(c["chunk_id"]) for c in new_chunks]
        metadatas = [chunk_to_metadata(c) for c in new_chunks]

        print(f"  Embedding {len(new_chunks)} chunks …", end=" ", flush=True)
        t1 = time.time()
        embeddings = model.encode(texts, show_progress_bar=False, batch_size=32).tolist()
        print(f"done ({time.time() - t1:.1f}s)")

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        total_added   += len(new_chunks)
        total_skipped += len(chunks) - len(new_chunks)
        print(f"  Stored {len(new_chunks)} vectors\n")

    save_query_embeddings(model)

    print("─" * 60)
    print(f"Done.  Added: {total_added}  |  Already existed: {total_skipped}")
    print(f"Collection total: {collection.count()} vectors")
    print(f"ChromaDB path: {CHROMA_DIR.resolve()}")


if __name__ == "__main__":
    main()
