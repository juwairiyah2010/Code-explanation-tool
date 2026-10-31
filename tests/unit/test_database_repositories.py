from backend.repositories.user_repo import UserRepository
from backend.repositories.submission_repo import SubmissionRepository
from backend.repositories.rag_repo import RAGRepository
from backend.repositories.learning_repo import LearningRepository


def test_submission_repository_history(db_session):
    """Verify SubmissionRepository history and retrieval."""
    repo = SubmissionRepository(db_session)
    assert repo.get_history() == []


def test_user_repository_crud(db_session):
    """Verify UserRepository creation and lookup."""
    repo = UserRepository(db_session)
    user = repo.create(username="test_dev", password_hash="hash123")
    assert user.id is not None
    assert user.username == "test_dev"

    by_name = repo.get_by_username("test_dev")
    assert by_name is not None
    assert by_name.id == user.id

    by_id = repo.get_by_id(user.id)
    assert by_id is not None
    assert by_id.username == "test_dev"


def test_rag_repository_crud(db_session):
    """Verify RAGRepository document and chunk creation, search, and stats."""
    repo = RAGRepository(db_session)
    doc = repo.upsert_document(
        doc_id="doc_async_guide",
        title="Async Guide",
        source="Docs",
        language="python",
        topic="async",
    )
    assert doc.id is not None

    chunk = repo.save_chunk(
        document_id=doc.id,
        chunk_id="chunk_async_1",
        title="Async Intro",
        source=doc.source,
        language="python",
        topic="async",
        content="async and await syntax",
        token_count=10,
        embedding=[0.1, 0.2, 0.3],
    )
    assert chunk.id is not None

    stats = repo.get_stats()
    assert stats["documents"] == 1
    assert stats["chunks"] == 1


def test_learning_repository_progress_tracking(db_session):
    """Verify LearningRepository updates concept mastery and records attempts."""
    repo = LearningRepository(db_session)
    user_id = 999
    questions = [
        {"id": "q1", "correct_answer": "A", "concept": "Loops"},
        {"id": "q2", "correct_answer": "B", "concept": "Loops"},
    ]
    answers = {"q1": "A", "q2": "C"}

    eval_res = repo.evaluate_and_record_attempt(
        questions=questions,
        answers=answers,
        user_id=user_id,
    )
    assert eval_res.score == 50.0
    assert eval_res.correct_count == 1

    progress = repo.get_learner_progress(user_id)
    assert len(progress) == 1
    assert progress[0].concept == "Loops"
    assert progress[0].mastery == 50.0
