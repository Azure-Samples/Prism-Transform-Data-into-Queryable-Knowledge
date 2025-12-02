"""
Pydantic models for API request/response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectInfo(BaseModel):
    """Project information"""
    name: str
    document_count: int
    has_extraction_results: bool
    has_chunked_documents: bool
    has_embedded_documents: bool
    has_results_csv: bool
    last_modified: Optional[str] = None


class WorkflowSection(BaseModel):
    """Workflow section information"""
    section_id: str
    section_name: str
    question_count: int
    completed_count: int
    completion_percentage: float


class WorkflowRunRequest(BaseModel):
    """Request to run a workflow section"""
    project_id: str = Field(..., description="Project identifier")


class WorkflowRunResponse(BaseModel):
    """Response after starting a workflow"""
    task_id: str
    status: TaskStatus
    section_id: str
    project_id: str
    message: str


class WorkflowStatusResponse(BaseModel):
    """Workflow execution status"""
    task_id: str
    status: TaskStatus
    section_id: str
    project_id: str
    questions_completed: int
    questions_total: int
    current_question: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class QuestionResult(BaseModel):
    """Single question result"""
    section_id: str
    section_name: str
    question_id: str
    question_name: str
    answer: Optional[str] = None
    reference: Optional[str] = None
    comments: Optional[str] = None


class ProjectResults(BaseModel):
    """All results for a project"""
    project_id: str
    total_questions: int
    answered_questions: int
    sections: List[Dict[str, Any]]


class QueryRequest(BaseModel):
    """Query request"""
    query: str = Field(..., description="Question to ask about documents")
    project_id: Optional[str] = Field(None, description="Project ID to query (reads index from project config)")
    index_name: Optional[str] = Field(None, description="Optional index name override (deprecated, use project_id)")


class QueryResponse(BaseModel):
    """Query response"""
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    query_plan: Optional[str] = None


class IndexInfo(BaseModel):
    """Search index information"""
    name: str
    is_active: bool
    exists: bool


class SetActiveIndexRequest(BaseModel):
    """Request to set active index"""
    index_name: str = Field(..., description="Index name to activate")


class SetActiveIndexResponse(BaseModel):
    """Response after setting active index"""
    success: bool
    previous_index: str
    new_index: str
    message: str
