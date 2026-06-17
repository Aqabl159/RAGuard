"""Offline conflict scanning orchestrator."""

import asyncio
import uuid
from datetime import datetime

from app.database.sqlite import get_db
from app.conflict.candidate_generator import generate_candidate_pairs
from app.conflict.reranker import rerank_pairs
from app.conflict.fact_checker import check_contradiction
from app.conflict.aggregator import aggregate_conflicts


async def run_scan(scan_job_id: str, threshold: float = 0.85) -> int:
    """Run a full offline conflict scan.

    Steps:
    1. Generate candidate pairs via embedding similarity
    2. Rerank candidate pairs with Jina Reranker
    3. Check each surviving pair with DeepSeek LLM
    4. Aggregate and deduplicate conflicts
    5. Write results to SQLite

    Args:
        scan_job_id: ID of the scan_jobs record.
        threshold: Minimum cosine similarity for candidate pairs.

    Returns:
        Number of conflicts found.
    """
    db = get_db()

    # Mark as running
    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE scan_jobs SET status = 'running', started_at = ? WHERE id = ?",
        (now, scan_job_id),
    )
    db.commit()

    try:
        # Step 1: Generate candidates
        pairs = generate_candidate_pairs(threshold=threshold)
        total_pairs = len(pairs)

        db.execute(
            "UPDATE scan_jobs SET total_pairs = ? WHERE id = ?",
            (total_pairs, scan_job_id),
        )
        db.commit()

        # Step 2: Rerank
        ranked_pairs = await rerank_pairs(pairs)
        conflict_pairs_count = len(ranked_pairs)

        db.execute(
            "UPDATE scan_jobs SET conflict_pairs = ? WHERE id = ?",
            (conflict_pairs_count, scan_job_id),
        )
        db.commit()

        # Step 3: LLM fact-checking (with rate limiting)
        raw_contradictions = []
        sem = asyncio.Semaphore(5)  # Max 5 concurrent LLM calls

        async def check_one(pair: dict):
            async with sem:
                result = await check_contradiction(pair["content_a"], pair["content_b"])
                if result:
                    raw_contradictions.append({"pair": pair, "result": result})

        tasks = [check_one(p) for p in ranked_pairs]
        await asyncio.gather(*tasks)

        # Step 4: Aggregate
        conflicts = aggregate_conflicts(raw_contradictions)
        conflicts_found = len(conflicts)

        # Step 5: Write to SQLite
        now2 = datetime.utcnow().isoformat()
        for conflict in conflicts:
            db.execute(
                """INSERT INTO conflicts (id, scan_job_id, conflict_type, summary, description,
                   status, severity, detection_method, detected_at)
                   VALUES (?, ?, ?, ?, ?, 'open', ?, 'llm', ?)""",
                (
                    conflict["id"], scan_job_id,
                    conflict["conflict_type"], conflict["summary"],
                    conflict["description"], conflict["severity"], now2,
                ),
            )

            for chunk in conflict["chunks"]:
                db.execute(
                    """INSERT INTO conflict_chunks (conflict_id, chunk_id, claim, role, similarity_score)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        conflict["id"], chunk["chunk_id"],
                        chunk["claim"], chunk["role"],
                        chunk["similarity_score"],
                    ),
                )

        # Mark scan as completed
        db.execute(
            """UPDATE scan_jobs
               SET status = 'completed', conflicts_found = ?, completed_at = ?
               WHERE id = ?""",
            (conflicts_found, now2, scan_job_id),
        )
        db.commit()

        return conflicts_found

    except Exception as e:
        db.execute(
            "UPDATE scan_jobs SET status = 'failed', error_message = ? WHERE id = ?",
            (str(e), scan_job_id),
        )
        db.commit()
        raise


def create_scan_job(threshold: float = 0.85) -> str:
    """Create a new scan job record and return its ID."""
    db = get_db()
    scan_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO scan_jobs (id, status, threshold, created_at) VALUES (?, 'pending', ?, ?)",
        (scan_id, threshold, now),
    )
    db.commit()
    return scan_id
