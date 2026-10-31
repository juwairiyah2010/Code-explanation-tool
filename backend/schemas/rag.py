"""Pydantic schemas for RAG knowledge base, chunks, retrieval, and source citations."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RAGSourceCitation(BaseModel):
    """Citation metadata for retrieved reference documentation."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    chunk_id: str = Field(..., description="Unique chunk identifier")
    score: float = Field(0.0, description="Hybrid or cosine similarity score (0.0 to 1.0)")
    source: str = Field(..., description="Origin of documentation (e.g. Python Official Docs, MDN Web Docs)")
    title: str = Field(..., description="Section or article title")
    text: str = Field("", description="Text content of the retrieved chunk")
    section: str = Field("", description="Specific section heading within article")
    language: str = Field("general", description="Associated language ('python', 'javascript', 'general')")
    topic: str = Field("programming", description="Subject domain topic")

    # Backward-compatibility aliases
    similarity_score: float = Field(0.0, description="Cosine similarity score for legacy clients")
    snippet: str = Field("", description="Concise text excerpt for legacy clients")

    @model_validator(mode="before")
    @classmethod
    def sync_score_and_text(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync score <-> similarity_score
            if "score" in data and "similarity_score" not in data:
                data["similarity_score"] = data["score"]
            elif "similarity_score" in data and "score" not in data:
                data["score"] = data["similarity_score"]

            # Sync text <-> snippet / content
            if "content" in data and "text" not in data:
                data["text"] = data["content"]
            if "text" in data and "snippet" not in data:
                data["snippet"] = data["text"][:280] + ("..." if len(data["text"]) > 280 else "")
            elif "snippet" in data and "text" not in data:
                data["text"] = data["snippet"]
        return data


# Structured retrieval result alias
StructuredRetrievalResult = RAGSourceCitation


class RAGRetrievalRequest(BaseModel):
    """Request payload for semantic and hybrid knowledge search."""

    query: str = Field(..., min_length=1, max_length=2000, description="Search query or code signature")
    language: str = Field("auto", description="Target programming language")
    top_k: int = Field(3, ge=1, le=10, description="Maximum number of relevant chunks to retrieve")
    similarity_threshold: float = Field(0.35, ge=0.0, le=1.0, description="Minimum cosine similarity threshold")
    min_relevance_threshold: float | None = Field(None, ge=0.0, le=1.0, description="Explicit minimum hybrid relevance threshold")
    hybrid: bool = Field(True, description="Whether to use hybrid (semantic + keyword) retrieval")
    alpha: float = Field(0.65, ge=0.0, le=1.0, description="Weight for semantic dense score (1-alpha is keyword BM25 weight)")
    max_context_chars: int = Field(3500, ge=500, le=20000, description="Maximum total character budget for retrieved context")


class RAGRetrievalResponse(BaseModel):
    """Response payload returning retrieved citations and relevance context status."""

    query: str
    results: list[RAGSourceCitation] = Field(default_factory=list)
    insufficient_context: bool = Field(False, description="True if no retrieved documentation met threshold")
    total_candidates: int = Field(0, description="Total candidate chunks searched")
    formatted_context: str = Field("", description="Pre-formatted context block for LLM prompt construction")


class RAGIngestResponse(BaseModel):
    """Status report from knowledge ingestion pipeline."""

    documents_ingested: int
    chunks_created: int
    duration_seconds: float
    message: str
