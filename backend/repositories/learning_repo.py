"""Repository for deterministic learner progress tracking and learning session persistence."""

import json
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models.persistence import LearnerProgress, LearningSession
from backend.schemas.learning import (
    ConceptMasteryItem,
    LearningEvaluationResponse,
    QuestionEvaluationResult,
)


class LearningRepository:
    """Manages persistence of learning sessions and updates the deterministic learner progress model."""

    def __init__(self, db: Session):
        self.db = db

    def evaluate_and_record_attempt(
        self,
        questions: list[dict[str, Any]],
        answers: dict[str, str],
        language: str = "python",
        user_id: int | None = None,
        submission_id: int | None = None,
        attempts: int = 1,
    ) -> LearningEvaluationResponse:
        """Deterministically grade answers, update concept mastery, and store session record."""
        total_questions = len(questions)
        correct_count = 0
        incorrect_concepts_set: set[str] = set()
        question_results: list[QuestionEvaluationResult] = []

        # Track concept tally in this attempt: {concept: (attempted, correct)}
        concept_deltas: dict[str, list[int]] = {}

        for q in questions:
            qid = str(q.get("id", ""))
            correct_ans = str(q.get("correct_answer") or q.get("correct_option_id") or "")
            user_ans = answers.get(qid)
            concept = str(q.get("concept") or "General")

            if concept not in concept_deltas:
                concept_deltas[concept] = [0, 0]
            concept_deltas[concept][0] += 1

            is_correct = (
                user_ans is not None
                and user_ans.strip().upper() == correct_ans.strip().upper()
            )

            if is_correct:
                correct_count += 1
                concept_deltas[concept][1] += 1
            else:
                incorrect_concepts_set.add(concept)

            raw_lines = q.get("referenced_lines", [])
            if isinstance(raw_lines, str):
                import re
                raw_lines = [int(n) for n in re.findall(r"\d+", raw_lines)]

            question_results.append(
                QuestionEvaluationResult(
                    question_id=qid,
                    question=str(q.get("question") or q.get("text") or ""),
                    question_type=str(q.get("question_type") or "comprehension"),
                    concept=concept,
                    referenced_lines=raw_lines,
                    user_answer=user_ans,
                    correct_answer=correct_ans,
                    is_correct=is_correct,
                    explanation=str(q.get("explanation") or ""),
                )
            )

        score_pct = round((correct_count / max(1, total_questions)) * 100.0, 1)

        # ── Update Learner Progress Model Deterministically ───────────
        for concept_name, (attempted_cnt, correct_cnt) in concept_deltas.items():
            stmt = select(LearnerProgress).where(
                LearnerProgress.concept == concept_name,
                LearnerProgress.user_id == user_id,
            )
            prog = self.db.execute(stmt).scalars().first()
            if not prog:
                prog = LearnerProgress(
                    user_id=user_id,
                    concept=concept_name,
                    total_attempted=attempted_cnt,
                    total_correct=correct_cnt,
                    mastery=round((correct_cnt / max(1, attempted_cnt)) * 100.0, 1),
                )
                self.db.add(prog)
            else:
                prog.total_attempted += attempted_cnt
                prog.total_correct += correct_cnt
                prog.mastery = round(
                    (prog.total_correct / max(1, prog.total_attempted)) * 100.0, 1
                )

        # ── Record Session ────────────────────────────────────────────
        session_rec = LearningSession(
            user_id=user_id,
            submission_id=submission_id,
            language=language,
            total_questions=total_questions,
            correct_count=correct_count,
            score=score_pct,
            attempts=attempts,
            completion_status="completed",
            incorrect_concepts=json.dumps(sorted(incorrect_concepts_set)),
            questions_data=json.dumps(questions),
            answers_data=json.dumps(answers),
        )
        self.db.add(session_rec)
        self.db.commit()

        # ── Load Updated Concept Mastery ──────────────────────────────
        all_mastery = self.get_learner_progress(user_id=user_id)

        return LearningEvaluationResponse(
            attempts=attempts,
            score=score_pct,
            correct_count=correct_count,
            total_questions=total_questions,
            incorrect_concepts=sorted(incorrect_concepts_set),
            completion_status="completed",
            question_results=question_results,
            concept_mastery=all_mastery,
        )

    def get_learner_progress(self, user_id: int | None = None) -> list[ConceptMasteryItem]:
        """Fetch current mastery percentages for all tracked concepts."""
        stmt = select(LearnerProgress).where(LearnerProgress.user_id == user_id).order_by(LearnerProgress.concept.asc())
        records = self.db.execute(stmt).scalars().all()
        return [
            ConceptMasteryItem(
                concept=r.concept,
                mastery=r.mastery,
                total_attempted=r.total_attempted,
                total_correct=r.total_correct,
            )
            for r in records
        ]
