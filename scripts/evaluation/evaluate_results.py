"""
Evaluation Service for Prism Results

Uses Azure AI Evaluation SDK to assess the quality of workflow answers.
Evaluates: Groundedness, Relevance, Coherence, Fluency

No ground truth required - all evaluations are based on:
- query (the question)
- response (the answer)
- context (the raw_response which includes citations/source info)
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from scripts.logging_config import get_logger
from apps.api.app.services.storage_service import get_storage_service

logger = get_logger(__name__)

# Load environment
load_dotenv()

# Azure OpenAI config for evaluators
# Support both AZURE_OPENAI_API_KEY and AZURE_OPENAI_KEY (azd uses the latter)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-4.1")


def get_model_config() -> Dict[str, str]:
    """Get model configuration for evaluators"""
    return {
        "azure_endpoint": AZURE_OPENAI_ENDPOINT,
        "api_key": AZURE_OPENAI_API_KEY,
        "azure_deployment": AZURE_OPENAI_CHAT_DEPLOYMENT,
        "api_version": AZURE_OPENAI_API_VERSION,
    }


def evaluate_single_answer(
    query: str,
    response: str,
    context: Optional[str] = None,
    comments: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate a single answer using Azure AI Evaluation SDK.

    Args:
        query: The question that was asked
        response: The answer that was generated (includes comments if provided)
        context: The raw response including citations (optional, for groundedness)
        comments: Additional comments to include in the evaluation

    Returns:
        Dictionary with evaluation scores and reasons
    """
    # Combine answer and comments for evaluation
    if comments and comments.strip():
        response = f"{response}\n\nComments: {comments}"
    try:
        from azure.ai.evaluation import (
            GroundednessEvaluator,
            RelevanceEvaluator,
            CoherenceEvaluator,
            FluencyEvaluator,
        )
    except ImportError:
        logger.error("azure-ai-evaluation not installed. Run: pip install azure-ai-evaluation")
        return {"error": "Evaluation SDK not installed"}

    model_config = get_model_config()

    if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT]):
        logger.error("Azure OpenAI credentials not configured")
        return {"error": "Azure OpenAI not configured"}

    evaluation_results = {
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "scores": {}
    }

    try:
        # Relevance: Does the answer address the question?
        relevance_eval = RelevanceEvaluator(model_config)
        relevance_result = relevance_eval(query=query, response=response)
        evaluation_results["scores"]["relevance"] = {
            "score": relevance_result.get("relevance", 0),
            "reason": relevance_result.get("relevance_reason", "")
        }
        logger.debug(f"Relevance score: {relevance_result.get('relevance')}")
    except Exception as e:
        logger.warning(f"Relevance evaluation failed: {e}")
        evaluation_results["scores"]["relevance"] = {"score": None, "reason": str(e)}

    try:
        # Coherence: Is the answer logically consistent?
        coherence_eval = CoherenceEvaluator(model_config)
        coherence_result = coherence_eval(query=query, response=response)
        evaluation_results["scores"]["coherence"] = {
            "score": coherence_result.get("coherence", 0),
            "reason": coherence_result.get("coherence_reason", "")
        }
        logger.debug(f"Coherence score: {coherence_result.get('coherence')}")
    except Exception as e:
        logger.warning(f"Coherence evaluation failed: {e}")
        evaluation_results["scores"]["coherence"] = {"score": None, "reason": str(e)}

    try:
        # Fluency: Is the language natural and readable?
        fluency_eval = FluencyEvaluator(model_config)
        fluency_result = fluency_eval(response=response)
        evaluation_results["scores"]["fluency"] = {
            "score": fluency_result.get("fluency", 0),
            "reason": fluency_result.get("fluency_reason", "")
        }
        logger.debug(f"Fluency score: {fluency_result.get('fluency')}")
    except Exception as e:
        logger.warning(f"Fluency evaluation failed: {e}")
        evaluation_results["scores"]["fluency"] = {"score": None, "reason": str(e)}

    # Groundedness: Is the answer supported by the context?
    if context:
        try:
            groundedness_eval = GroundednessEvaluator(model_config)
            groundedness_result = groundedness_eval(
                query=query,
                context=context,
                response=response
            )
            evaluation_results["scores"]["groundedness"] = {
                "score": groundedness_result.get("groundedness", 0),
                "reason": groundedness_result.get("groundedness_reason", "")
            }
            logger.debug(f"Groundedness score: {groundedness_result.get('groundedness')}")
        except Exception as e:
            logger.warning(f"Groundedness evaluation failed: {e}")
            evaluation_results["scores"]["groundedness"] = {"score": None, "reason": str(e)}

    # Calculate average score
    valid_scores = [
        s["score"] for s in evaluation_results["scores"].values()
        if s.get("score") is not None
    ]
    if valid_scores:
        evaluation_results["average_score"] = round(sum(valid_scores) / len(valid_scores), 2)
    else:
        evaluation_results["average_score"] = None

    return evaluation_results


def evaluate_project_results(project_name: str) -> Dict[str, Any]:
    """
    Evaluate all results for a project.

    Args:
        project_name: Name of the project

    Returns:
        Dictionary with evaluation results for all questions
    """
    storage = get_storage_service()
    results = storage.read_json(project_name, "output/results.json")

    if not results:
        logger.error(f"Results file not found for project: {project_name}")
        return {"error": "Results file not found"}

    total_evaluated = 0
    total_scores = {"relevance": [], "coherence": [], "fluency": [], "groundedness": []}

    sections = results.get("sections", {})

    for section_id, section_data in sections.items():
        questions = section_data.get("questions", {})

        for question_id, question_data in questions.items():
            answer = question_data.get("answer", "")
            question_text = question_data.get("question", "")
            raw_response = question_data.get("raw_response", "")
            comments = question_data.get("comments", "")

            # Skip if no answer
            if not answer or not answer.strip():
                continue

            logger.info(f"Evaluating {section_id}/{question_id}...")

            # Run evaluation (includes comments in the response)
            eval_result = evaluate_single_answer(
                query=question_text,
                response=answer,
                context=raw_response,
                comments=comments
            )

            # Store evaluation in question data
            question_data["evaluation"] = eval_result
            total_evaluated += 1

            # Collect scores for summary
            for metric, data in eval_result.get("scores", {}).items():
                if data.get("score") is not None:
                    total_scores[metric].append(data["score"])

    # Save updated results with evaluations to blob storage
    storage.write_json(project_name, "output/results.json", results)

    # Calculate summary statistics
    summary = {
        "project": project_name,
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "total_evaluated": total_evaluated,
        "average_scores": {}
    }

    for metric, scores in total_scores.items():
        if scores:
            summary["average_scores"][metric] = round(sum(scores) / len(scores), 2)

    logger.info(f"Evaluation complete: {total_evaluated} answers evaluated")
    logger.info(f"Average scores: {summary['average_scores']}")

    return summary


def evaluate_question(
    project_name: str,
    section_id: str,
    question_id: str
) -> Dict[str, Any]:
    """
    Evaluate a single question's answer and save the result.

    Args:
        project_name: Name of the project
        section_id: Section ID
        question_id: Question ID

    Returns:
        Evaluation result dictionary
    """
    storage = get_storage_service()
    results = storage.read_json(project_name, "output/results.json")

    if not results:
        return {"error": "Results file not found"}

    # Find the question
    section = results.get("sections", {}).get(section_id, {})
    question_data = section.get("questions", {}).get(question_id, {})

    if not question_data:
        return {"error": "Question not found"}

    answer = question_data.get("answer", "")
    question_text = question_data.get("question", "")
    raw_response = question_data.get("raw_response", "")
    comments = question_data.get("comments", "")

    if not answer or not answer.strip():
        return {"error": "No answer to evaluate"}

    # Run evaluation (includes comments in the response)
    eval_result = evaluate_single_answer(
        query=question_text,
        response=answer,
        context=raw_response,
        comments=comments
    )

    # Save evaluation to blob storage
    question_data["evaluation"] = eval_result
    storage.write_json(project_name, "output/results.json", results)

    return eval_result
