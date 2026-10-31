"""Unit tests for offline RAG retrieval, hybrid ranking, and irrelevant query handling."""

import pytest
from backend.repositories.rag_repo import RAGRepository
from backend.services.rag.embeddings import MockEmbeddingService
from backend.services.rag.retriever import RAGRetriever
from tests.fixtures import IRRELEVANT_RAG_QUERIES


@pytest.fixture
def populated_rag(db_session):
    """Seed in-memory database with test knowledge chunks."""
    repo = RAGRepository(db_session)
    embedding_svc = MockEmbeddingService(dimension=64)

    # Ingest sample docs
    doc_py = repo.create_document(
        title="Python Functions and Scope",
        source="Python Core Docs",
        language="python",
        file_path="data/knowledge_base/python_core.md",
    )
    vec_py = embedding_svc.embed_text("Functions are defined using the def keyword with local variable scope.")
    repo.create_chunk(
        document_id=doc_py.id,
        chunk_id="chunk_py_func",
        title="Defining Functions",
        source=doc_py.source,
        language="python",
        topic="functions",
        section="Functions",
        text="Functions are defined using the def keyword with local variable scope and return statements.",
        embedding=vec_py,
    )

    doc_js = repo.create_document(
        title="JavaScript Event Loop",
        source="MDN Docs",
        language="javascript",
        file_path="data/knowledge_base/javascript_core.md",
    )
    vec_js = embedding_svc.embed_text("The event loop coordinates asynchronous callbacks and promises.")
    repo.create_chunk(
        document_id=doc_js.id,
        chunk_id="chunk_js_loop",
        title="Event Loop",
        source=doc_js.source,
        language="javascript",
        topic="async",
        section="Concurrency",
        text="The event loop coordinates asynchronous callbacks, microtasks, and macrotasks in the runtime.",
        embedding=vec_js,
    )

    retriever = RAGRetriever(db_session, embedding_service=embedding_svc)
    return retriever


def test_relevant_python_retrieval(populated_rag: RAGRetriever):
    """Relevant programming queries should retrieve matched chunks with high scores."""
    res = populated_rag.retrieve(
        query="how to define a function with return in python",
        language="python",
        top_k=3,
        similarity_threshold=0.2,
    )
    assert len(res.results) >= 1
    assert res.results[0].chunk_id == "chunk_py_func"
    assert res.insufficient_context is False


def test_irrelevant_rag_queries(populated_rag: RAGRetriever):
    """Completely irrelevant non-programming queries must result in low relevance or insufficient context."""
    for query in IRRELEVANT_RAG_QUERIES:
        res = populated_rag.retrieve(
            query=query,
            language="python",
            top_k=3,
            similarity_threshold=0.75,  # High threshold for relevance gating
        )
        assert res.insufficient_context is True
        assert len(res.results) == 0


def test_context_budget_control(populated_rag: RAGRetriever):
    """Retrieved formatted context must respect maximum character budget."""
    res = populated_rag.retrieve(
        query="functions event loop",
        top_k=2,
        similarity_threshold=0.1,
        max_context_chars=120,
    )
    assert len(res.formatted_context) <= 150  # Allows slight margin for headers
