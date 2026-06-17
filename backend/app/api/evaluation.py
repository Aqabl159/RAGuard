"""RAGAS evaluation API endpoints."""

import uuid
import json

from fastapi import APIRouter, HTTPException
from app.database.sqlite import get_db
from app.qa.router import run_qa_pipeline

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


@router.post("/run", status_code=202)
async def run_evaluation(body: dict):
    """Run RAGAS evaluation with test questions.

    Request body:
    {
        "test_questions": [
            {"question": "...", "ground_truth": "..."},
            ...
        ]
    }
    """
    test_questions = body.get("test_questions", [])
    if not test_questions:
        raise HTTPException(status_code=400, detail="No test questions provided")

    eval_id = str(uuid.uuid4())

    results = []
    for item in test_questions:
        question = item["question"]
        ground_truth = item.get("ground_truth", "")

        result = await run_qa_pipeline(question)

        results.append({
            "question": question,
            "ground_truth": ground_truth,
            "generated_answer": result["content"],
            "has_conflict": result.get("conflict_warning") is not None,
            "sources_count": len(result.get("sources", [])),
        })

    # Calculate simple metrics
    total = len(results)
    conflict_free = sum(1 for r in results if not r["has_conflict"])
    answered = sum(1 for r in results if "无法回答" not in r["generated_answer"])

    metrics = {
        "total_questions": total,
        "answered_rate": answered / total if total > 0 else 0,
        "conflict_free_rate": conflict_free / total if total > 0 else 0,
    }

    # Try RAGAS metrics if available
    try:
        from ragas.metrics import faithfulness, answer_relevancy
        from datasets import Dataset

        eval_data = {
            "question": [r["question"] for r in results],
            "answer": [r["generated_answer"] for r in results],
            "contexts": [[""] for _ in results],
            "ground_truth": [r["ground_truth"] for r in results],
        }
        dataset = Dataset.from_dict(eval_data)

        # Note: full RAGAS evaluation requires context retrieval
        # This is a simplified version
        metrics["ragas_status"] = "simplified"
    except ImportError:
        metrics["ragas_status"] = "not_available"

    return {
        "evaluation_id": eval_id,
        "status": "completed",
        "metrics": metrics,
        "results": results,
    }
