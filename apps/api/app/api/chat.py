"""
Chat API - Contextual chat with search capabilities
Supports both general document search and question-specific follow-ups
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from apps.api.app.services.chat_service import ChatService


router = APIRouter()
chat_service = ChatService()


class ChatContext(BaseModel):
    """Context for a chat session - either a specific question or general search"""
    section_id: Optional[str] = None
    question_id: Optional[str] = None
    question_text: Optional[str] = None
    current_answer: Optional[str] = None
    current_reference: Optional[str] = None
    current_comments: Optional[str] = None


class ChatMessage(BaseModel):
    """A single message in the conversation"""
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    """Request to send a chat message"""
    project_id: str
    message: str
    context: Optional[ChatContext] = None
    conversation_history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    """Response from the chat agent"""
    message: str
    citations: Optional[List[Dict[str, Any]]] = []


class UpdateResultRequest(BaseModel):
    """Request to update a result with chat findings"""
    project_id: str
    section_id: str
    question_id: str
    new_answer: Optional[str] = None
    new_reference: Optional[str] = None
    new_comments: Optional[str] = None


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the chat agent

    The agent will:
    - Use any provided context (question/answer being discussed)
    - Search documents for relevant information
    - Provide a conversational response with citations
    """
    try:
        if not request.message or len(request.message.strip()) == 0:
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        result = await chat_service.chat(
            project_id=request.project_id,
            message=request.message,
            context=request.context.model_dump() if request.context else None,
            conversation_history=[m.model_dump() for m in request.conversation_history] if request.conversation_history else []
        )

        return ChatResponse(
            message=result['message'],
            citations=result.get('citations', [])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update-result")
async def update_result(request: UpdateResultRequest):
    """
    Update a result with improved answer/reference/comments from chat
    """
    try:
        success = await chat_service.update_result(
            project_id=request.project_id,
            section_id=request.section_id,
            question_id=request.question_id,
            new_answer=request.new_answer,
            new_reference=request.new_reference,
            new_comments=request.new_comments
        )

        if not success:
            raise HTTPException(status_code=404, detail="Result not found")

        return {"message": "Result updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
