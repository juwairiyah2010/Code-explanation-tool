"""Pydantic schemas for RAG knowledge base, chunks, retrieval, and source citations."""

from pydantic import BaseModel, Field


class RAGSourceCitation(BaseModel):
    """Citation metadata for retrieved reference documentation."""

    source: str = Field(..., description="Origin of documentation (e.g. Python Official Docs, MDN Web Docs)")
    title: str = Field(..., description="Section or article title")
    chunk_id: str = Field(..., description="Unique chunk identifier")
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    snippet: str = Field(..., description="Concise text excerpt supporting the citation")
    language: str = Field(..., description="Associated language ('python', 'javascript', 'general')")
    topic: str = Field(..., description="Subject domain topic")


class RAGRetrievalRequest(BaseModel):
    """Request payload for semantic knowledge search."""

    query: str = Field(..., min_length=1, max_length=2000, description="Search query or code signature")
    language: str = Field("auto", description="Target programming language")
    top_k: int = Field(3, ge=1, le=10, description="Maximum number of relevant chunks to retrieve")
    similarity_threshold: float = Field(0.35, ge=0.0, le=1.0, description="Minimum cosine similarity threshold")


class RAGRetrievalResponse(BaseModel):
    """Response payload returning retrieved citations and relevance context status."""

    query: str
    results: list[RAGSourceCitation] = Field(default_factory=list)
    insufficient_context: bool = Field(False, description="True if no retrieved documentation met threshold")
    total_candidates: int = Field(0, description="Total candidate chunks searched")


class RAGIngestResponse(BaseModel):
    """Status report from knowledge ingestion pipeline."""

    documents_ingested: int
    chunks_created: int
    duration_seconds: float
    message: str
