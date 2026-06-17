"""Resolution workflow — generates proposals and executes approved repairs.

Workflow:
    extract_claims → analyze_contradiction → generate_resolution → save → return
    (no LangGraph interrupt — human review is managed via API endpoints)
"""

import uuid
from datetime import datetime

from app.resolution.state import ResolutionState
from app.resolution.generator import (
    extract_claims as _llm_extract_claims,
    analyze_contradiction as _llm_analyze_contradiction,
    generate_resolution as _llm_generate_resolution,
)
from app.resolution.repair import apply_repair as _execute_repair
from app.database.sqlite import get_db


# ============================================================
# Synchronous helper: run full generation pipeline
# ============================================================

async def run_resolution(state: ResolutionState) -> str:
    """Run the resolution generation pipeline.

    Extracts claims, analyzes contradiction, generates a resolution
    proposal, saves it to the database, and returns the resolution_id.

    Returns:
        resolution_id string.
    """
    db = get_db()

    # 1. Extract claims
    result = await _llm_extract_claims(
        state["chunk_a"]["content"],
        state["chunk_b"]["content"],
    )
    claims_a = result.get("claims_a", [])
    claims_b = result.get("claims_b", [])
    state["chunk_a"]["claim"] = "; ".join(claims_a) if claims_a else state["chunk_a"]["claim"]
    state["chunk_b"]["claim"] = "; ".join(claims_b) if claims_b else state["chunk_b"]["claim"]

    # 2. Analyze contradiction
    analysis_result = await _llm_analyze_contradiction(claims_a, claims_b)
    analysis = analysis_result.get("analysis", "")

    # 3. Generate resolution
    gen_result = await _llm_generate_resolution(
        conflict_type=state["conflict_type"],
        doc_title_a=state["chunk_a"]["document_title"],
        doc_title_b=state["chunk_b"]["document_title"],
        text_a=state["chunk_a"]["content"],
        text_b=state["chunk_b"]["content"],
        analysis=analysis,
    )

    proposed_action = gen_result.get("proposed_action", "manual_rewrite")
    proposed_content = gen_result.get("proposed_content")
    reasoning = gen_result.get("reasoning", "LLM 未提供推理")

    # If manual_rewrite was chosen but no content provided, fallback to keep_a_remove_b
    if proposed_action == "manual_rewrite" and not proposed_content:
        proposed_action = "keep_a_remove_b"
        reasoning = (reasoning or "") + "\n（注意：LLM 无法自动确定内容，默认采用保留A删除B策略）"

    # 4. Save to database
    resolution_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    db.execute(
        """INSERT INTO resolutions (id, conflict_id,
           proposed_action, proposed_content, reasoning, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'pending_review', ?)""",
        (resolution_id, state["conflict_id"], proposed_action, proposed_content, reasoning, now),
    )

    # Update conflict status
    db.execute(
        "UPDATE conflicts SET status = 'in_review' WHERE id = ?",
        (state["conflict_id"],),
    )
    db.commit()

    return resolution_id


# ============================================================
# Re-generate after human modification
# ============================================================

async def regenerate_resolution(
    conflict_id: str,
    conflict_type: str,
    doc_title_a: str,
    doc_title_b: str,
    text_a: str,
    text_b: str,
    analysis: str,
    human_notes: str,
) -> dict:
    """Re-generate a resolution with human feedback."""
    extra_context = analysis
    if human_notes:
        extra_context = f"{analysis}\n\n人工审核意见：{human_notes}"

    gen_result = await _llm_generate_resolution(
        conflict_type=conflict_type,
        doc_title_a=doc_title_a,
        doc_title_b=doc_title_b,
        text_a=text_a,
        text_b=text_b,
        analysis=extra_context,
    )
    return gen_result


# ============================================================
# Execute human decision
# ============================================================

async def execute_decision(
    resolution_id: str,
    decision: str,  # 'approved', 'rejected', or 'modified'
    conflict_id: str,
    chunk_a_id: str,
    chunk_b_id: str,
    proposed_action: str,
    proposed_content: str | None,
    human_notes: str = "",
    human_modified_content: str = "",
    modified_action: str = "",
) -> dict:
    """Execute the human decision on a resolution.

    For 'approved': runs repair actions, updates statuses.
    For 'rejected': updates resolution and conflict status.
    For 'modified': updates resolution with new content/action, sets back to pending_review.

    Returns a dict with status info.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()

    if decision == "approved":
        # Use modified_action if provided, else proposed_action
        effective_action = modified_action or proposed_action
        effective_content = human_modified_content or proposed_content

        # For actions that require content but have none, reject the approval
        if effective_action in ("replace_both", "merge", "manual_rewrite") and not effective_content:
            raise ValueError(
                f"Action '{effective_action}' requires content but none was provided. "
                "Please use '修改' to provide content first."
            )

        # Execute repair
        results = await _execute_repair(
            resolution_id=resolution_id,
            proposed_action=effective_action,
            proposed_content=effective_content,
            human_modified_content=human_modified_content,
            chunk_a_id=chunk_a_id,
            chunk_b_id=chunk_b_id,
        )

        # Update resolution
        db.execute(
            "UPDATE resolutions SET status = 'applied', applied_at = ?, human_decision = ?, human_notes = ?, human_modified_content = ? WHERE id = ?",
            (now, decision, human_notes, human_modified_content, resolution_id),
        )

        # Update conflict — only if repairs were actually done
        if results:
            db.execute(
                "UPDATE conflicts SET status = 'resolved', resolved_at = ? WHERE id = ?",
                (now, conflict_id),
            )
        db.commit()

        return {"status": "applied", "repair_count": len([r for r in results if r.get("success")])}

    elif decision == "rejected":
        db.execute(
            "UPDATE resolutions SET status = 'rejected', reviewed_at = ?, human_decision = ?, human_notes = ? WHERE id = ?",
            (now, decision, human_notes, resolution_id),
        )
        db.execute(
            "UPDATE conflicts SET status = 'dismissed', resolved_at = ? WHERE id = ?",
            (now, conflict_id),
        )
        db.commit()
        return {"status": "dismissed"}

    elif decision == "modified":
        # Update the existing resolution record with modified content
        new_action = modified_action or proposed_action
        new_content = human_modified_content or proposed_content

        db.execute(
            """UPDATE resolutions
               SET status = 'modified', reviewed_at = ?, human_decision = ?,
                   human_notes = ?, human_modified_content = ?,
                   proposed_action = ?, proposed_content = ?
               WHERE id = ?""",
            (now, decision, human_notes, human_modified_content, new_action, new_content, resolution_id),
        )
        db.commit()

        return {"status": "modified"}

    else:
        raise ValueError(f"Unknown decision: {decision}")
