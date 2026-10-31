"""Unit tests for enhanced offline-first RAG architecture:

Tests document cleaning, semantic chunking, metadata extraction, BM25 scoring,
hybrid ranking, context deduplication, context size control, and evaluation.
"""

from pathlib import Path
from backend.models.persistence import KnowledgeChunk
from backend.repositories.rag_repo import RAGRepository
from backend.schemas.rag import RAGSourceCitation
from backend.services.rag.embeddings import MockEmbeddingService
from backend.services.rag.evaluation import RAGEvaluator, BENCHMARK_DATASET
from backend.services.rag.ingestion import KnowledgeIngestionPipeline
from backend.services.rag.retriever import BM25Scorer, RAGRetriever


def test_document_cleaning(db_session):
    pipeline = KnowledgeIngestionPipeline(db_session, embedding_service=MockEmbeddingService())
    raw = "Header\r\n\r\n\r\n\r\n“Smart quotes” and ‘single’   \n\n\nBody text\u200b with spaces."
    cleaned = pipeline.clean_document_text(raw)
    assert "\r" not in cleaned
    assert '“' not in cleaned and '"Smart quotes"' in cleaned
    assert "‘" not in cleaned and "'single'" in cleaned
    assert "\n\n\n" not in cleaned
    assert "\u200b" not in cleaned


def test_semantic_chunking_preserves_code_blocks(db_session):
    pipeline = KnowledgeIngestionPipeline(db_session, embedding_service=MockEmbeddingService())
    section = {
        "title": "Functions",
        "content": (
            "Paragraph one introduces Python functions.\n\n"
            "```python\n"
            "def add(a, b):\n"
            "    # This is a sample function\n"
            "    return a + b\n"
            "```\n\n"
            "Paragraph two explains the return value and behavior."
        ),
    }
    chunks = pipeline.chunk_section(section, max_words=30)
    assert len(chunks) >= 1
    # Ensure code fence was not split in half
    for c in chunks:
        if "```python" in c:
            assert "def add" in c
            assert "```" in c


def test_metadata_extraction_and_chunk_fields(db_session):
    pipeline = KnowledgeIngestionPipeline(db_session, embedding_service=MockEmbeddingService())
    kb_path = Path("data/knowledge_base")
    res = pipeline.ingest_directory(kb_path)
    assert res.documents_ingested >= 5
    assert res.chunks_created >= 15

    repo = RAGRepository(db_session)
    chunks: list[KnowledgeChunk] = repo.get_candidate_chunks(language="all")
    assert len(chunks) >= 15

    sample = chunks[0]
    # Check all required metadata fields
    assert sample.document_id > 0
    assert sample.title
    assert sample.source
    assert sample.language in ("python", "javascript", "general")
    assert sample.topic
    assert sample.section
    assert sample.chunk_id
    assert sample.text
    assert sample.content
    assert sample.embedding
    assert sample.token_count > 0


def test_bm25_keyword_scoring():
    corpus = [
        "Python functions and generators yield values lazily.",
        "JavaScript event loop and microtask queue handling.",
        "Algorithm time complexity and Big O notation sorting.",
    ]
    scorer = BM25Scorer(corpus)
    scores = scorer.score("generators yield")
    assert len(scores) == 3
    # First document should have highest BM25 score for 'generators yield'
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]
    assert scores[0] == 1.0  # normalized max score


def test_hybrid_retrieval_and_structured_results(db_session):
    pipeline = KnowledgeIngestionPipeline(db_session, embedding_service=MockEmbeddingService())
    pipeline.ingest_directory(Path("data/knowledge_base"))

    retriever = RAGRetriever(db_session, embedding_service=MockEmbeddingService())
    res = retriever.retrieve(
        query="What is the time complexity of dictionary lookup?",
        language="python",
        top_k=2,
        hybrid=True,
        alpha=0.6,
        similarity_threshold=0.1,
    )

    assert not res.insufficient_context
    assert len(res.results) >= 1

    first = res.results[0]
    # Verify structured result format
    assert first.chunk_id
    assert isinstance(first.score, float)
    assert first.source
    assert first.title
    assert first.text
    assert first.section


def test_context_deduplication(db_session):
    retriever = RAGRetriever(db_session)
    duplicate_items = [
        {
            "chunk_id": "c1",
            "score": 0.95,
            "source": "Python Docs",
            "title": "Generators",
            "section": "Generators",
            "text": "Generators provide lazy evaluation using yield statement with O(1) memory.",
            "language": "python",
            "topic": "syntax",
        },
        {
            "chunk_id": "c2",
            "score": 0.91,
            "source": "Python Docs",
            "title": "Generators",
            "section": "Generators",
            "text": "Generators provide lazy evaluation using yield statement with O(1) memory and iteration.",
            "language": "python",
            "topic": "syntax",
        },
        {
            "chunk_id": "c3",
            "score": 0.80,
            "source": "Python Docs",
            "title": "Decorators",
            "section": "Decorators",
            "text": "Decorators are functions that take another function as an argument and extend its behavior.",
            "language": "python",
            "topic": "syntax",
        },
    ]

    deduped = retriever._deduplicate_chunks(duplicate_items, similarity_threshold=0.75)
    # c2 is a near-duplicate of c1 and should be dropped; c3 is distinct and kept
    assert len(deduped) == 2
    assert deduped[0]["chunk_id"] == "c1"
    assert deduped[1]["chunk_id"] == "c3"


def test_context_size_control(db_session):
    retriever = RAGRetriever(db_session)
    citations = [
        RAGSourceCitation(
            chunk_id=f"chunk_{i}",
            score=0.9 - (i * 0.1),
            source="Source",
            title=f"Doc {i}",
            section="Section",
            text="A" * 500,
        )
        for i in range(5)
    ]

    # Budget of 1200 chars should only allow first 2 chunks (500 + 500 = 1000 <= 1200)
    budgeted = retriever._apply_context_size_control(citations, max_chars=1200)
    assert len(budgeted) == 2
    assert budgeted[0].chunk_id == "chunk_0"
    assert budgeted[1].chunk_id == "chunk_1"


def test_llm_prompt_construction(db_session):
    retriever = RAGRetriever(db_session)
    citations = [
        RAGSourceCitation(
            chunk_id="chunk_1",
            score=0.88,
            source="Python Documentation",
            title="Python Functions",
            section="Parameters",
            text="All arguments in Python are passed by assignment.",
        )
    ]
    prompt_context = retriever.build_llm_prompt_context(citations)
    assert "=== RETRIEVED GROUND TRUTH DOCUMENTATION" in prompt_context
    assert "Source: Python Documentation" in prompt_context
    assert "Title: Python Functions" in prompt_context
    assert "Section: Parameters" in prompt_context
    assert "All arguments in Python are passed by assignment." in prompt_context


def test_rag_evaluation_benchmark(db_session):
    mock_emb = MockEmbeddingService()
    pipeline = KnowledgeIngestionPipeline(db_session, embedding_service=mock_emb)
    pipeline.ingest_directory(Path("data/knowledge_base"))

    evaluator = RAGEvaluator(db_session, embedding_service=mock_emb)
    results = evaluator.evaluate(top_k=3, hybrid=True)

    assert results["total_queries"] == len(BENCHMARK_DATASET)
    assert results["hit_at_k"] >= 0.85
    assert results["mrr"] >= 0.70
    assert results["avg_latency_ms"] >= 0.0
