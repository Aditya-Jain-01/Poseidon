"""Local passage index for source-backed Brain answers."""
from __future__ import annotations

import hashlib
import math
import re
import struct
from pathlib import Path

from app.embeddings import LocalEmbedder
from app.storage.connection import connection

CHUNK_CHARS = 700
CHUNK_WORDS = 100
OVERLAP_WORDS = 18
MAX_EXCERPTS = 8
MIN_SEMANTIC_SIMILARITY = 0.28
STOP_WORDS = {
    "a", "an", "and", "are", "can", "could", "did", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "our", "should", "the",
    "this", "to", "was", "were", "what", "when", "where", "which", "who", "will",
}


def chunk_text(text: str) -> list[str]:
    """Make bounded, overlapping passages while preserving word order."""
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start
        length = 0
        while end < len(words) and end - start < CHUNK_WORDS and (
            length + len(words[end]) + 1 <= CHUNK_CHARS or end == start
        ):
            length += len(words[end]) + 1
            end += 1
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + 1, end - OVERLAP_WORDS)
    return chunks


def replace_source_chunks(conn, source_id: str, chunks: list[str], vectors: list[list[float]], embedder: LocalEmbedder) -> None:
    if len(chunks) != len(vectors):
        raise ValueError("Every Brain passage needs an embedding")
    conn.execute("DELETE FROM brain_chunks WHERE source_id=?", (source_id,))
    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        if len(vector) != embedder.dimension or not all(math.isfinite(value) for value in vector):
            raise ValueError("Invalid Brain passage embedding")
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            raise ValueError("Zero Brain passage embedding")
        packed = struct.pack(f"<{embedder.dimension}f", *(value / norm for value in vector))
        chunk_id = conn.execute(
            "INSERT INTO brain_chunks(source_id,chunk_index,content) VALUES (?,?,?)",
            (source_id, index, chunk),
        ).lastrowid
        conn.execute(
            "INSERT INTO brain_chunk_embeddings(chunk_id,model_id,dimension,vector) VALUES (?,?,?,?)",
            (chunk_id, embedder.model_id, embedder.dimension, packed),
        )


def search_passages(db_path: Path, vault: Path, owner_id: str, question: str, embedder: LocalEmbedder) -> list[dict]:
    """Fuse local embedding similarity and FTS5 ranks over fresh passages."""
    with connection(db_path) as conn:
        indexed = conn.execute(
            "SELECT 1 FROM brain_chunk_embeddings e JOIN brain_chunks c ON c.id=e.chunk_id "
            "JOIN brain_sources s ON s.id=c.source_id "
            "WHERE s.owner_id=? AND e.model_id=? AND e.dimension=? LIMIT 1",
            (owner_id, embedder.model_id, embedder.dimension),
        ).fetchone()
    if not indexed:
        return []
    question_vector = embedder.encode([question])[0]
    if len(question_vector) != embedder.dimension:
        raise ValueError("Invalid Brain question embedding dimension")
    norm = math.sqrt(sum(value * value for value in question_vector))
    if norm == 0:
        raise ValueError("Zero Brain question embedding")
    question_vector = [value / norm for value in question_vector]
    terms = list(dict.fromkeys(
        word for word in re.findall(r"[^\W_]+", question.casefold())
        if len(word) > 2 and word not in STOP_WORDS
    ))[:12]
    with connection(db_path) as conn:
        rows = conn.execute(
            "SELECT c.id,c.chunk_index,c.content,s.path,s.content_hash,e.vector "
            "FROM brain_chunks c JOIN brain_sources s ON s.id=c.source_id "
            "JOIN brain_chunk_embeddings e ON e.chunk_id=c.id "
            "WHERE s.owner_id=? AND e.model_id=? AND e.dimension=?",
            (owner_id, embedder.model_id, embedder.dimension),
        ).fetchall()
        lexical_ids = []
        if terms:
            query = " OR ".join(f'"{word}"' for word in terms)
            lexical_ids = [row["id"] for row in conn.execute(
                "SELECT c.id FROM brain_chunks_fts "
                "JOIN brain_chunks c ON c.id=brain_chunks_fts.rowid "
                "JOIN brain_sources s ON s.id=c.source_id "
                "WHERE brain_chunks_fts MATCH ? AND s.owner_id=? "
                "ORDER BY bm25(brain_chunks_fts),c.id LIMIT 40",
                (query, owner_id),
            )]
    by_id = {row["id"]: row for row in rows}
    semantic = []
    for row in rows:
        vector = struct.unpack(f"<{embedder.dimension}f", row["vector"])
        similarity = sum(a * b for a, b in zip(question_vector, vector))
        if similarity >= MIN_SEMANTIC_SIMILARITY:
            semantic.append((row["id"], similarity))
    semantic.sort(key=lambda item: (-item[1], item[0]))
    scores: dict[int, float] = {}
    for rank, (chunk_id, _similarity) in enumerate(semantic[:40], 1):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (20 + rank)
    for rank, chunk_id in enumerate(lexical_ids, 1):
        if chunk_id in by_id:
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (20 + rank)
    ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    results = []
    seen_paths: dict[str, int] = {}
    for chunk_id in ordered:
        row = by_id[chunk_id]
        if seen_paths.get(row["path"], 0) >= 2:
            continue
        path = vault / row["path"]
        if not path.is_file() or path.is_symlink():
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["content_hash"]:
            continue
        first_line = path.read_text(encoding="utf-8-sig").splitlines()[0].strip()
        title = first_line.removeprefix("# ").strip() or path.stem.replace("-", " ").title()
        results.append({"chunk_id": row["id"], "chunk_index": row["chunk_index"],
                        "path": row["path"], "title": title, "evidence": row["content"]})
        seen_paths[row["path"]] = seen_paths.get(row["path"], 0) + 1
        if len(results) >= MAX_EXCERPTS:
            break
    return results
