"""API v1 router aggregator."""

from fastapi import APIRouter
from backend.api.v1.endpoints import health, ast_analysis, explanation, trace, quiz, history, concepts

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(ast_analysis.router)
api_router.include_router(explanation.router)
api_router.include_router(trace.router, prefix="/trace", tags=["trace"])
api_router.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
