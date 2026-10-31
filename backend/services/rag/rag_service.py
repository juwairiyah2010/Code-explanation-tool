"""Service coordinating RAG knowledge retrieval, vector statistics, and ingestion pipelines."""

from pathlib import Path
from sqlalchemy.orm import Session
from backend.repositories.rag_repo import RAGRepository
from backend.schemas.rag import (
    RAGIngestResponse,
    RAGRetrievalRequest,
    RAGRetrievalResponse,
)
from backend.services.rag.ingestion import KnowledgeIngestionPipeline
from backend.services.rag.retriever import RAGRetriever


class RAGService:
    """Service facade encapsulating RAG operations for clean API routing."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = RAGRepository(db)
        self.retriever = RAGRetriever(db)
        self.pipeline = KnowledgeIngestionPipeline(db)

    def retrieve(self, request: RAGRetrievalRequest) -> RAGRetrievalResponse:
        """Search knowledge base for chunks most relevant to query using hybrid scoring."""
        return self.retriever.retrieve(
            query=request.query,
            language=request.language,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            min_relevance_threshold=request.min_relevance_threshold,
            hybrid=request.hybrid,
            alpha=request.alpha,
            max_context_chars=request.max_context_chars,
        )

    def get_stats(self) -> dict[str, int]:
        """Get count of ingested documents and vector chunks."""
        return self.repo.get_stats()

    def ingest_directory(self, target_path: Path | None = None) -> RAGIngestResponse:
        """Parse, embed, and index markdown knowledge base files."""
        if target_path is None:
            target_path = Path("data/knowledge_base")
            if not target_path.exists():
                target_path = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"

        return self.pipeline.ingest_directory(target_path)
