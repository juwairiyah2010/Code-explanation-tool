"""Endpoints for RAG knowledge search, statistics, and ingestion."""

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.repositories.rag_repo import RAGRepository
from backend.schemas.rag import (
    RAGIngestResponse,
    RAGRetrievalRequest,
    RAGRetrievalResponse,
)
from backend.services.rag.ingestion import KnowledgeIngestionPipeline
from backend.services.rag.retriever import RAGRetriever

router = APIRouter()


@router.post(
    "/retrieve",
    response_model=RAGRetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Knowledge Search",
    description="Retrieve most relevant knowledge chunks and citations for a given query.",
)
def retrieve_knowledge(
    request: RAGRetrievalRequest,
    db: Session = Depends(get_db),
):
    retriever = RAGRetriever(db)
    return retriever.retrieve(
        query=request.query,
        language=request.language,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
    )


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Knowledge Base Statistics",
    description="Get count of ingested documents and vector chunks.",
)
def get_rag_stats(db: Session = Depends(get_db)):
    repo = RAGRepository(db)
    return repo.get_stats()


@router.post(
    "/ingest",
    response_model=RAGIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Knowledge Ingestion",
    description="Re-index and embed documentation from the data/knowledge_base directory.",
)
def trigger_ingestion(db: Session = Depends(get_db)):
    try:
        pipeline = KnowledgeIngestionPipeline(db)
        kb_path = Path("data/knowledge_base")
        if not kb_path.exists():
            kb_path = Path(__file__).resolve().parents[4] / "data" / "knowledge_base"
        return pipeline.ingest_directory(kb_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest knowledge base: {str(e)}",
        )
