"""
Progress Tracker - Global progress tracking for pipeline stages

Scripts can import and use this to report progress back to the API.
Supports nested progress: document-level + page-level.
"""

import os
from typing import Callable, Optional

# Global callback storage
_progress_callback: Optional[Callable[[int, int, str], None]] = None
_current_task_id: Optional[str] = None

# Document context for nested progress
_doc_context: dict = {"current": 0, "total": 0, "name": ""}


def set_progress_callback(task_id: str, callback: Callable[[int, int, str], None]) -> None:
    """Set the progress callback for the current task"""
    global _progress_callback, _current_task_id
    _progress_callback = callback
    _current_task_id = task_id


def clear_progress_callback() -> None:
    """Clear the progress callback"""
    global _progress_callback, _current_task_id, _doc_context
    _progress_callback = None
    _current_task_id = None
    _doc_context = {"current": 0, "total": 0, "name": ""}


def set_document_context(doc_num: int, total_docs: int, doc_name: str = "") -> None:
    """
    Set the current document context for nested page progress.

    Args:
        doc_num: Current document number (1-indexed)
        total_docs: Total number of documents
        doc_name: Name of current document
    """
    global _doc_context
    _doc_context = {"current": doc_num, "total": total_docs, "name": doc_name}


def report_progress(current: int, total: int, message: str = "") -> None:
    """
    Report progress for the current task.

    Can be called from any script during pipeline execution.

    Args:
        current: Current item number (1-indexed)
        total: Total number of items
        message: Optional message describing current operation
    """
    if _progress_callback:
        _progress_callback(current, total, message)


def report_page_progress(page_num: int, total_pages: int, page_message: str = "") -> None:
    """
    Report page-level progress within a document.

    Automatically includes document context if set.

    Args:
        page_num: Current page number (1-indexed)
        total_pages: Total pages in document
        page_message: Optional message about page processing
    """
    if _progress_callback:
        # Build nested progress message
        if _doc_context["total"] > 0:
            doc_info = f"Doc {_doc_context['current']}/{_doc_context['total']}"
            if _doc_context["name"]:
                doc_info = f"{_doc_context['name']} ({_doc_context['current']}/{_doc_context['total']})"
            message = f"{doc_info} - Page {page_num}/{total_pages}"
            if page_message:
                message += f" - {page_message}"
        else:
            message = f"Page {page_num}/{total_pages}"
            if page_message:
                message += f" - {page_message}"

        # Report with page as current item (for progress bar calculation)
        _progress_callback(page_num, total_pages, message)


def get_current_task_id() -> Optional[str]:
    """Get the current task ID if one is set"""
    return _current_task_id
