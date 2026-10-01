import json
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.persistence import Submission, Explanation, Block, Concept, QuizItem

class SubmissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_full_submission(
        self,
        code: str,
        language: str,
        level: str,
        ast_summary: str | None,
        llm_result,  # LLMExplanationResult
        quiz_response=None # QuizResponse (optional)
    ) -> Submission:
        
        # We start a transaction natively within SQLAlchemy flush/commit
        # LLMExplanationResult fields: summary, blocks, concepts, algorithm_steps, complexity, hints
        
        submission = Submission(
            code=code,
            language=language,
            level=level,
            ast_summary=ast_summary,
        )
        self.db.add(submission)
        self.db.flush() # get submission.id

        explanation = Explanation(
            submission_id=submission.id,
            summary=llm_result.summary,
            algorithm_steps=json.dumps(llm_result.algorithm_steps),
            complexity=json.dumps(llm_result.complexity.model_dump()) if llm_result.complexity else "{}",
            hints=json.dumps(llm_result.hints)
        )
        self.db.add(explanation)

        for b in llm_result.blocks:
            block = Block(
                submission_id=submission.id,
                title=b.title,
                explanation=b.explanation,
                line_start=b.line_start,
                line_end=b.line_end
            )
            self.db.add(block)

        for c in llm_result.concepts:
            concept = Concept(
                submission_id=submission.id,
                name=c.concept,
                definition=c.definition
            )
            self.db.add(concept)

        if quiz_response:
            for q in quiz_response.questions:
                quiz_item = QuizItem(
                    submission_id=submission.id,
                    question=q.text,
                    options=json.dumps([opt.model_dump() for opt in q.options]),
                    correct_option_id=q.correct_option_id,
                    explanation=q.explanation,
                    line_reference=q.line_reference
                )
                self.db.add(quiz_item)

        self.db.commit()
        self.db.refresh(submission)
        return submission

    def get_history(self, limit: int = 10, offset: int = 0):
        stmt = select(Submission).order_by(Submission.created_at.desc()).offset(offset).limit(limit)
        results = self.db.execute(stmt).scalars().all()
        return results
        
    def get_concept_by_name(self, name: str, limit: int = 10, offset: int = 0):
        stmt = select(Concept).where(Concept.name == name).order_by(Concept.id.desc()).offset(offset).limit(limit)
        return self.db.execute(stmt).scalars().all()
    
    def get_submission_by_id(self, submission_id: int):
        stmt = select(Submission).where(Submission.id == submission_id)
        return self.db.execute(stmt).scalars().first()
        
    def delete_submission(self, submission_id: int) -> bool:
        stmt = select(Submission).where(Submission.id == submission_id)
        sub = self.db.execute(stmt).scalars().first()
        if sub:
            self.db.delete(sub)
            self.db.commit()
            return True
        return False
