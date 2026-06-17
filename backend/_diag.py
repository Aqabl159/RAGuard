"""Diagnostic: check chunks and candidate pairs for financial docs."""
from app.database.sqlite import get_db
from app.database.chroma_client import get_collection
from app.conflict.candidate_generator import (
    get_all_embeddings, compute_cosine_similarity_matrix
)
import numpy as np

db = get_db()

# Find the two financial docs
v1 = db.execute(
    "SELECT id, filename FROM documents WHERE filename LIKE '03_%' AND status = 'indexed' ORDER BY created_at"
).fetchall()

print("=== Indexed financial docs ===")
for r in v1:
    chunks = db.execute(
        "SELECT chunk_index, token_count, section_path, content FROM chunks WHERE document_id = ? AND is_active = TRUE ORDER BY chunk_index",
        (r["id"],)
    ).fetchall()
    print(f"Doc: {r['filename']} ({r['id'][:8]}) — {len(chunks)} chunks")
    for c in chunks:
        content_preview = c["content"][:80].replace("\n", " ")
        print(f"  idx={c['chunk_index']} tokens={c['token_count']} path={c['section_path'][:50]}")
        print(f"    content: {content_preview}...")

print()

# Check Chroma count and cross-document similarity
collection = get_collection()
total = collection.count()
print(f"Total Chroma vectors: {total}")

# Get all embeddings
ids, embeddings, metadatas = get_all_embeddings()
print(f"Fetched {len(ids)} embeddings")

# Map which ids belong to which doc
doc_chunk_map = {}
for doc_row in v1:
    doc_id = doc_row["id"]
    doc_chunks = db.execute(
        "SELECT chroma_id, chunk_index FROM chunks WHERE document_id = ? AND is_active = TRUE",
        (doc_id,)
    ).fetchall()
    doc_chunk_map[doc_id] = set(r["chroma_id"] for r in doc_chunks)

# Find indices for each doc
if len(v1) >= 2:
    id_to_idx = {id_: i for i, id_ in enumerate(ids)}
    doc1_ids = doc_chunk_map[v1[0]["id"]]
    doc2_ids = doc_chunk_map[v1[1]["id"]]
    doc1_indices = [id_to_idx[cid] for cid in doc1_ids if cid in id_to_idx]
    doc2_indices = [id_to_idx[cid] for cid in doc2_ids if cid in id_to_idx]

    print(f"\nDoc V1 indices: {doc1_indices}")
    print(f"Doc V2 indices: {doc2_indices}")

    # Compute cross-doc similarities
    if embeddings and doc1_indices and doc2_indices:
        embs = np.array(embeddings, dtype=np.float32)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        embs_norm = embs / norms

        print(f"\n=== Cross-document cosine similarities ===")
        for i in doc1_indices:
            for j in doc2_indices:
                sim = float(np.dot(embs_norm[i], embs_norm[j]))
                status = "ABOVE" if sim >= 0.85 else "below"
                if sim > 0.7:
                    print(f"  V1[{i}] <-> V2[{j}]: sim={sim:.4f} {status}")

        # Check same-document similarity within V1
        print(f"\n=== Same-document (V1) similarities ===")
        for i in range(len(doc1_indices)):
            for j in range(i+1, len(doc1_indices)):
                ii, jj = doc1_indices[i], doc1_indices[j]
                sim = float(np.dot(embs_norm[ii], embs_norm[jj]))
                if sim > 0.7:
                    print(f"  V1[{ii}] <-> V1[{jj}]: sim={sim:.4f}")

print("\n=== Last scan jobs ===")
jobs = db.execute("SELECT id, status, total_pairs, conflicts_found, created_at FROM scan_jobs ORDER BY created_at DESC LIMIT 5").fetchall()
for j in jobs:
    print(f"  {j['created_at']} | {j['status']} | pairs={j['total_pairs']} conflicts={j['conflicts_found']}")
