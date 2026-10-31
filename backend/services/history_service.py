"""Service handling historical submission retrieval, serialization, and concept lookups."""

import json
from backend.repositories.submission_repo import SubmissionRepository
from backend.schemas.history import (
    HistorySummaryItem,
    HistoryDetailResponse,
    HistoryBlockItem,
    HistoryConceptItem,
    HistoryExplanationDetail,
    ConceptLookupResponse,
    ConceptLookupItem,
)


class HistoryService:
    """Encapsulates history and concept queries and transforms ORM records into schemas."""

    def __init__(self, submission_repo: SubmissionRepository):
        self.repo = submission_repo

    def list_history(
        self, limit: int = 10, offset: int = 0, user_id: int | None = None
    ) -> list[HistorySummaryItem]:
        """Fetch and serialize recent submission summaries for a user."""
        submissions = self.repo.get_history(limit=limit, offset=offset, user_id=user_id)
        result = []
        for sub in submissions:
            result.append(
                HistorySummaryItem(
                    id=sub.id,
                    code=sub.code,
                    language=sub.language,
                    level=sub.level,
                    summary=sub.explanation.summary if sub.explanation else "",
                    created_at=sub.created_at.isoformat(),
                )
            )
        return result

    def get_history_detail(
        self, record_id: int, user_id: int | None = None
    ) -> HistoryDetailResponse | None:
        """Fetch full historical submission details by record ID for a user."""
        record = self.repo.get_submission_by_id(record_id, user_id=user_id)
        if not record:
            return None

        explanation_detail = None
        if record.explanation:
            explanation_detail = HistoryExplanationDetail(
                summary=record.explanation.summary,
                algorithm_steps=json.loads(record.explanation.algorithm_steps)
                if record.explanation.algorithm_steps
                else [],
                complexity=json.loads(record.explanation.complexity)
                if record.explanation.complexity
                else {},
                hints=json.loads(record.explanation.hints) if record.explanation.hints else [],
            )

        blocks_data = [
            HistoryBlockItem(
                id=b.id,
                title=b.title,
                explanation=b.explanation,
                line_start=b.line_start,
                line_end=b.line_end,
            )
            for b in record.blocks
        ]

        concepts_data = [
            HistoryConceptItem(
                id=c.id,
                concept=c.name,
                definition=c.definition,
            )
            for c in record.concepts
        ]

        return HistoryDetailResponse(
            id=record.id,
            code=record.code,
            language=record.language,
            level=record.level,
            created_at=record.created_at.isoformat(),
            summary=record.explanation.summary if record.explanation else "",
            explanation=explanation_detail,
            blocks=blocks_data,
            concepts=concepts_data,
        )

    def lookup_concepts(
        self, name: str, limit: int = 10, offset: int = 0
    ) -> ConceptLookupResponse:
        """Query stored concept definitions matching a name."""
        concepts = self.repo.get_concept_by_name(name=name, limit=limit, offset=offset)
        items = [
            ConceptLookupItem(
                id=c.id,
                submission_id=c.submission_id,
                name=c.name,
                definition=c.definition,
            )
            for c in concepts
        ]
        return ConceptLookupResponse(items=items, limit=limit, offset=offset)
