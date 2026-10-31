"""Pydantic schemas for submission history and concept definitions."""

from pydantic import BaseModel
from typing import Any


class HistorySummaryItem(BaseModel):
    id: int
    code: str
    language: str
    level: str
    summary: str
    created_at: str


class HistoryBlockItem(BaseModel):
    id: int
    title: str
    explanation: str
    line_start: int
    line_end: int


class HistoryConceptItem(BaseModel):
    id: int
    concept: str
    definition: str


class HistoryExplanationDetail(BaseModel):
    summary: str
    algorithm_steps: list[str] = []
    complexity: dict[str, Any] = {}
    hints: list[str] = []


class HistoryDetailResponse(BaseModel):
    id: int
    code: str
    language: str
    level: str
    created_at: str
    summary: str
    explanation: HistoryExplanationDetail | None = None
    blocks: list[HistoryBlockItem] = []
    concepts: list[HistoryConceptItem] = []


class ConceptLookupItem(BaseModel):
    id: int
    submission_id: int
    name: str
    definition: str


class ConceptLookupResponse(BaseModel):
    items: list[ConceptLookupItem]
    limit: int
    offset: int
