"""
Document extraction agents and utilities.

Core extractors (generic, domain-agnostic):
- pdf_extraction_agents: Agent-based PDF extraction with vision and validation
- excel_extraction_agents: Excel extraction with agent enhancement
- email_extraction_agents: Email (.msg) extraction with agent enhancement

Domain-specific plugins are available in scripts/extraction/plugins/:
- sld_extractor: Specialized extraction for electrical Single-Line Diagrams
"""
from .pdf_extraction_agents import process_pdf_with_agents_sync
from .excel_extraction_agents import process_excel_with_agents_sync
from .email_extraction_agents import process_email_with_agents_sync

__all__ = [
    'process_pdf_with_agents_sync',
    'process_excel_with_agents_sync',
    'process_email_with_agents_sync',
]
