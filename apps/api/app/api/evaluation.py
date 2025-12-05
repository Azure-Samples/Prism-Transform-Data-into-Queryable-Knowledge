"""
Evaluation API - Run and retrieve evaluation results
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from apps.api.app.services.project_service import ProjectService
from apps.api.app.services.storage_service import get_storage_service


router = APIRouter()
project_service = ProjectService()


class EvaluationResponse(BaseModel):
    """Response from evaluation"""
    project: str
    evaluated_at: str
    total_evaluated: int
    average_scores: Dict[str, float]


class QuestionEvaluationRequest(BaseModel):
    """Request to evaluate a single question"""
    section_id: str
    question_id: str


@router.post("/{project_id}/run")
async def run_evaluation(project_id: str, background_tasks: BackgroundTasks):
    """
    Run evaluation on all results for a project.
    This evaluates all answered questions using Azure AI Evaluation SDK.
    """
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        from scripts.evaluation.evaluate_results import evaluate_project_results

        # Run evaluation (this can take a while for many questions)
        result = evaluate_project_results(project_id)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation SDK not installed: {e}. Run: pip install azure-ai-evaluation"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/question")
async def evaluate_question(project_id: str, request: QuestionEvaluationRequest):
    """
    Evaluate a single question's answer.
    """
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        from scripts.evaluation.evaluate_results import evaluate_question as eval_question

        result = eval_question(project_id, request.section_id, request.question_id)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result

    except HTTPException:
        raise
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation SDK not installed: {e}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/summary")
async def get_evaluation_summary(project_id: str):
    """
    Get evaluation summary for a project (average scores across all questions).
    """
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        storage = get_storage_service()
        results = storage.read_json(project_id, "output/results.json")

        if not results:
            raise HTTPException(status_code=404, detail="No results found")

        # Calculate summary statistics
        total_scores = {"relevance": [], "coherence": [], "fluency": [], "groundedness": []}
        total_evaluated = 0

        for section_id, section_data in results.get("sections", {}).items():
            for question_id, question_data in section_data.get("questions", {}).items():
                evaluation = question_data.get("evaluation", {})
                if evaluation and "scores" in evaluation:
                    total_evaluated += 1
                    for metric, data in evaluation.get("scores", {}).items():
                        if data.get("score") is not None and metric in total_scores:
                            total_scores[metric].append(data["score"])

        summary = {
            "project": project_id,
            "total_evaluated": total_evaluated,
            "average_scores": {}
        }

        for metric, scores in total_scores.items():
            if scores:
                summary["average_scores"][metric] = round(sum(scores) / len(scores), 2)

        return summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
