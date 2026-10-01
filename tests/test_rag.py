"""Tests for RAG pipeline: ingestion, vector retrieval, resilience, citations, and grounding."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.core.database import SessionLocal
from backend.repositories.rag_repo import RAGRepository
from backend.services.rag.embeddings import MockEmbeddingService, FastEmbedService
from backend.services.rag.ingestion import KnowledgeIngestionPipeline
from backend.services.rag.retriever import RAGRetriever


@pytest.fixture(scope="module")
def populated_db():
    """Ensure knowledge base is ingested and available for standalone tests."""
    db = SessionLocal()
    try:
        repo = RAGRepository(db)
        stats = repo.get_stats()
        if stats["chunks"] == 0:
            pipeline = KnowledgeIngestionPipeline(db)
            kb_path = Path("data/knowledge_base")
            pipeline.ingest_directory(kb_path)
        yield db
    finally:
        db.close()


@pytest.fixture
def populated_test_db(db_session):
    """Populate the isolated in-memory test db for TestClient requests."""
    pipeline = KnowledgeIngestionPipeline(db_session, embedding_service=FastEmbedService())
    kb_path = Path("data/knowledge_base")
    pipeline.ingest_directory(kb_path)
    return db_session




def test_document_ingestion_and_chunking(populated_db):
    """Test parsing markdown documents, extracting headers, metadata, and chunking."""
    pipeline = KnowledgeIngestionPipeline(populated_db, embedding_service=MockEmbeddingService())
    
    # Test parsing single markdown document
    py_doc_path = Path("data/knowledge_base/python_core.md")
    assert py_doc_path.exists()
    doc_data = pipeline.parse_markdown_document(py_doc_path)
    
    assert doc_data["doc_id"] == "python_core"
    assert doc_data["language"] == "python"
    assert "Python" in doc_data["title"]
    assert len(doc_data["sections"]) >= 3

    # Test chunking helper
    sample_section = {"title": "Long section", "content": "word " * 400}
    chunks = pipeline.chunk_section(sample_section, max_words=100, overlap=20)
    assert len(chunks) > 1


def test_retrieval_relevance_python(populated_db):
    """Test semantic retrieval relevance for Python specific queries."""
    retriever = RAGRetriever(populated_db)
    response = retriever.retrieve(
        query="How do Python generators and the yield statement work with memory?",
        language="python",
        top_k=3,
        similarity_threshold=0.4,
    )

    assert not response.insufficient_context
    assert len(response.results) >= 1
    top_result = response.results[0]
    assert "Generators" in top_result.title or "Python" in top_result.source
    assert top_result.similarity_score > 0.4
    assert len(top_result.snippet) > 10


def test_retrieval_relevance_javascript(populated_db):
    """Test semantic retrieval relevance for JavaScript specific queries."""
    retriever = RAGRetriever(populated_db)
    response = retriever.retrieve(
        query="What is a closure and lexical scoping in JavaScript?",
        language="javascript",
        top_k=3,
        similarity_threshold=0.4,
    )

    assert not response.insufficient_context
    assert len(response.results) >= 1
    titles = [r.title for r in response.results]
    assert any("Closures" in t for t in titles)


def test_insufficient_context_handling(populated_db):
    """Test that unrelated queries or empty content cleanly indicate insufficient context."""
    retriever = RAGRetriever(populated_db)
    
    # Very high threshold or unrelated nonsense
    response = retriever.retrieve(
        query="zxyq9877239 nonsensical gibberish ungrounded term",
        language="python",
        similarity_threshold=0.99,
    )

    assert response.insufficient_context is True
    assert len(response.results) == 0

    # Empty query
    empty_res = retriever.retrieve(query="   ")
    assert empty_res.insufficient_context is True
    assert len(empty_res.results) == 0


def test_embedding_failure_resilience(populated_db):
    """Test that embedding service failures are caught gracefully without crashing retrieval."""
    class BrokenEmbeddingService(MockEmbeddingService):
        def embed_texts(self, texts):
            raise ConnectionError("Simulated remote embedding API failure.")

    failing_retriever = RAGRetriever(populated_db, embedding_service=BrokenEmbeddingService())
    res = failing_retriever.retrieve(query="def foo(): pass")
    
    # Should safely return insufficient context instead of 500 unhandled exception
    assert res.insufficient_context is True
    assert len(res.results) == 0


def test_source_attribution_non_fabrication(populated_db):
    """Verify that citations contain genuine sources and no fabricated references."""
    retriever = RAGRetriever(populated_db)
    response = retriever.retrieve(
        query="Big-O asymptotic analysis and time complexity",
        language="general",
        top_k=2,
    )

    assert len(response.results) > 0
    valid_known_sources = [
        "Python Official Documentation (docs.python.org)",
        "MDN Web Docs (developer.mozilla.org)",
        "MIT OpenCourseWare & CS Curricula Reference",
        "Introduction to Algorithms & Algorithm Design Manual",
        "Software Engineering Debugging Standards & Language References",
    ]

    for cite in response.results:
        assert cite.source in valid_known_sources
        assert cite.chunk_id is not None and len(cite.chunk_id) > 0
        assert 0.0 <= cite.similarity_score <= 1.0


def test_end_to_end_explanation_with_and_without_rag(client: TestClient, populated_test_db):
    """Compare explanation results with RAG enabled versus RAG disabled."""
    code = """def generate_squares(n):
    for i in range(n):
        yield i ** 2
"""
    # 1. With RAG
    res_rag = client.post(
        "/api/v1/explain",
        json={
            "code": code,
            "language": "python",
            "level": "Beginner",
            "enable_rag": True,
            "save_history": False,
        },
    )
    assert res_rag.status_code == 200
    data_rag = res_rag.json()
    assert data_rag["rag_context_used"] is True
    assert len(data_rag["rag_sources"]) >= 1
    assert any("Generators" in s["title"] or "Python" in s["title"] for s in data_rag["rag_sources"])

    # 2. Without RAG
    res_no_rag = client.post(
        "/api/v1/explain",
        json={
            "code": code,
            "language": "python",
            "level": "Beginner",
            "enable_rag": False,
            "save_history": False,
        },
    )
    assert res_no_rag.status_code == 200
    data_no_rag = res_no_rag.json()
    assert data_no_rag["rag_context_used"] is False
    assert len(data_no_rag["rag_sources"]) == 0


def test_rag_api_endpoints(client: TestClient, populated_test_db):
    """Test dedicated RAG endpoints: stats and retrieve."""
    # Stats
    stats_res = client.get("/api/v1/rag/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["documents"] >= 5
    assert stats["chunks"] >= 15

    # Retrieve
    retrieve_res = client.post(
        "/api/v1/rag/retrieve",
        json={
            "query": "JavaScript event loop and microtask queue",
            "language": "javascript",
            "top_k": 2,
        },
    )
    assert retrieve_res.status_code == 200
    data = retrieve_res.json()
    assert len(data["results"]) >= 1
    assert any("Event Loop" in r["title"] or "Asynchronous" in r["title"] for r in data["results"])

