"""
Indexes API - Manage search indexes
"""
from fastapi import APIRouter, HTTPException
from typing import List
import os
from apps.api.app.models import IndexInfo, SetActiveIndexRequest, SetActiveIndexResponse
from dotenv import load_dotenv


router = APIRouter()

# Load environment variables
load_dotenv()


@router.get("", response_model=List[IndexInfo])
async def list_indexes():
    """
    List all available search indexes

    Note: Currently returns a static list of known indexes.
    In production, this could query Azure AI Search to list actual indexes.
    """
    try:
        current_index = os.getenv('AZURE_SEARCH_INDEX_NAME', 'prism-default-index')

        # Known indexes (could be made dynamic by querying Azure Search)
        known_indexes = [
            'prism-default-index'
        ]

        indexes = [
            IndexInfo(
                name=index_name,
                is_active=(index_name == current_index),
                exists=True  # In production, check if index actually exists
            )
            for index_name in known_indexes
        ]

        return indexes

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active", response_model=IndexInfo)
async def get_active_index():
    """Get the currently active search index"""
    try:
        current_index = os.getenv('AZURE_SEARCH_INDEX_NAME', 'prism-default-index')

        return IndexInfo(
            name=current_index,
            is_active=True,
            exists=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/active", response_model=SetActiveIndexResponse)
async def set_active_index(request: SetActiveIndexRequest):
    """
    Set the active search index

    Note: This only changes the environment variable for the current process.
    To persist changes, update the .env file.
    """
    try:
        previous_index = os.getenv('AZURE_SEARCH_INDEX_NAME', 'prism-default-index')

        # Set new index
        os.environ['AZURE_SEARCH_INDEX_NAME'] = request.index_name

        return SetActiveIndexResponse(
            success=True,
            previous_index=previous_index,
            new_index=request.index_name,
            message=f"Active index changed from '{previous_index}' to '{request.index_name}'"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
