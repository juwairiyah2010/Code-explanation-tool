import pytest
from backend.core.database import Base, get_db
from backend.models.persistence import Submission, Explanation, Block, Concept, QuizItem
from backend.repositories.submission_repo import SubmissionRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_submission_crud_and_relationships(db_session):
    repo = SubmissionRepository(db_session)
    
    class MockLLMResult:
        def __init__(self):
            self.summary = "Test Summary"
            self.algorithm_steps = ["Step 1"]
            class Comp:
                def model_dump(self):
                    return {"time": "O(1)"}
            self.complexity = Comp()
            self.hints = ["Hint"]
            
            class Blk:
                def __init__(self):
                    self.title = "B1"
                    self.explanation = "E1"
                    self.line_start = 1
                    self.line_end = 2
            self.blocks = [Blk()]
            
            class Con:
                def __init__(self):
                    self.concept = "C1"
                    self.definition = "D1"
            self.concepts = [Con()]
            
    class MockQuizResponse:
        def __init__(self):
            class Opt:
                def model_dump(self):
                    return {"id": "1", "text": "A"}
            class Q:
                def __init__(self):
                    self.text = "Q1"
                    self.options = [Opt()]
                    self.correct_option_id = "1"
                    self.explanation = "Ans1"
                    self.line_reference = "1"
            self.questions = [Q()]
            
    # Save
    sub = repo.save_full_submission(
        code="print(1)",
        language="python",
        level="Beginner",
        ast_summary="{}",
        llm_result=MockLLMResult(),
        quiz_response=MockQuizResponse()
    )
    
    assert sub.id is not None
    assert sub.explanation is not None
    assert sub.explanation.summary == "Test Summary"
    assert len(sub.blocks) == 1
    assert sub.blocks[0].title == "B1"
    assert len(sub.concepts) == 1
    assert sub.concepts[0].name == "C1"
    assert len(sub.quiz_items) == 1
    assert sub.quiz_items[0].question == "Q1"
    
    # Retrieve history
    history = repo.get_history()
    assert len(history) == 1
    
    # Retrieve concept
    concepts = repo.get_concept_by_name("C1")
    assert len(concepts) == 1
    assert concepts[0].definition == "D1"
    
    # Delete
    assert repo.delete_submission(sub.id) is True
    assert repo.get_submission_by_id(sub.id) is None
    
    # Check cascade
    assert len(db_session.query(Explanation).all()) == 0
    assert len(db_session.query(Block).all()) == 0
    assert len(db_session.query(Concept).all()) == 0
    assert len(db_session.query(QuizItem).all()) == 0
