"""
Query API - Search documents using knowledge agent
"""
from fastapi import APIRouter, HTTPException
from apps.api.app.models import QueryRequest, QueryResponse
from apps.api.app.services.query_service import QueryService


router = APIRouter()
query_service = QueryService()


@router.post("", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query documents using the knowledge agent

    The knowledge agent will:
    - Search relevant documents using hybrid search
    - Synthesize an answer with strict grounding rules
    - Provide citations from source documents
    """
    try:
        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        result = await query_service.search_documents(request.query, request.project_id, request.index_name)

        return QueryResponse(
            query=result['query'],
            answer=result['answer'],
            citations=result['citations'],
            query_plan=result.get('query_plan')
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
