"""Endpoints for RAG knowledge search, statistics, and ingestion."""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.api.deps import get_rag_service
from backend.schemas.rag import (
    RAGIngestResponse,
    RAGRetrievalRequest,
    RAGRetrievalResponse,
)
from backend.core.security import sanitize_internal_error
from backend.services.rag.rag_service import RAGService

router = APIRouter()


import asyncio

@router.post(
    "/retrieve",
    response_model=RAGRetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Knowledge Search",
    description="Retrieve most relevant knowledge chunks and citations for a given query.",
)
async def retrieve_knowledge(
    request: RAGRetrievalRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> RAGRetrievalResponse:
    """Perform vector similarity search over documentation chunks."""
    return await asyncio.to_thread(rag_service.retrieve, request)


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Knowledge Base Statistics",
    description="Get count of ingested documents and vector chunks.",
)
async def get_rag_stats(rag_service: RAGService = Depends(get_rag_service)) -> dict[str, int]:
    """Retrieve document count and chunk count from knowledge base."""
    return await asyncio.to_thread(rag_service.get_stats)


@router.post(
    "/ingest",
    response_model=RAGIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Knowledge Ingestion",
    description="Re-index and embed documentation from the data/knowledge_base directory.",
)
def trigger_ingestion(
    rag_service: RAGService = Depends(get_rag_service),
) -> RAGIngestResponse:
    """Re-parse and re-embed reference documents into SQLite vectors."""
    try:
        return rag_service.ingest_directory()
    except Exception as e:
        detail = sanitize_internal_error(e, context_msg="Failed to ingest knowledge base")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
