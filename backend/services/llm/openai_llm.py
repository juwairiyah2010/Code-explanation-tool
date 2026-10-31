"""OpenAI LLM provider implementation conforming to BaseLLMService."""

import json
from typing import Any
import httpx
from backend.config import get_settings
from backend.schemas.explanation import AlgorithmComplexity, BlockExplanation, ConceptTag

from backend.schemas.quiz import QuizQuestion, QuizResponse
from backend.services.llm.base import BaseLLMService, LLMExplanationResult


class OpenAILLMService(BaseLLMService):
    """OpenAI API provider for structured code explanations and quizzes."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL or "gpt-4o-mini"
        self.base_url = "https://api.openai.com/v1"

    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_mode: bool = True,
    ) -> str:
        """Call OpenAI chat completions API using httpx."""
        if not self.api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in environment or .env.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_explanation(
        self,
        code: str,
        language: str,
        level: str,
        ast_context: str | None = None,
        required_blocks: list | None = None,
        rag_context: str | None = None,
        rag_citations: list | None = None,
        **kwargs: Any,
    ) -> LLMExplanationResult:
        """Legacy explanation adapter for backward compatibility."""
        from backend.services.llm.prompts import build_explanation_prompt, SYSTEM_PROMPT
        prompt = build_explanation_prompt(code, language, level, ast_context=ast_context, rag_context=rag_context)
        raw_json = await self.generate_chat_completion(SYSTEM_PROMPT, prompt, json_mode=True)
        data = json.loads(raw_json)

        blocks = [
            BlockExplanation(
                title=b.get("title", f"Block {i+1}"),
                explanation=b.get("explanation", ""),
                line_start=b.get("line_start", 1),
                line_end=b.get("line_end", len(code.splitlines())),
            )
            for i, b in enumerate(data.get("blocks", []))
        ]
        concepts = [
            ConceptTag(concept=c.get("concept", ""), definition=c.get("definition", ""))
            for c in data.get("concepts", [])
        ]
        complexity_data = data.get("complexity", {})
        complexity = AlgorithmComplexity(
            time_complexity=complexity_data.get("time_complexity", "O(1)"),
            space_complexity=complexity_data.get("space_complexity", "O(1)"),
            explanation=complexity_data.get("explanation", "Standard complexity"),
        )
        return LLMExplanationResult(
            summary=data.get("summary", ""),
            blocks=blocks,
            concepts=concepts,
            algorithm_steps=data.get("algorithm_steps", []),
            complexity=complexity,
            hints=data.get("hints", []),
        )

    async def generate_quiz(
        self,
        code: str,
        language: str,
        explanation_context: str | None = None,
        locale: str = "en",
    ) -> QuizResponse:
        """Generate quiz using OpenAI chat completions."""
        sys_prompt = "You are a CS educator generating a 3-question multiple choice quiz on the given code. Return JSON matching: {\"questions\": [{\"id\": 1, \"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct_answer\": \"...\", \"explanation\": \"...\"}]}"
        user_prompt = f"Code ({language}):\n{code}\nContext: {explanation_context or ''}"
        raw = await self.generate_chat_completion(sys_prompt, user_prompt, json_mode=True)
        data = json.loads(raw)
        questions = [
            QuizQuestion(
                id=q.get("id", i + 1),
                question=q.get("question", ""),
                options=q.get("options", []),
                correct_answer=q.get("correct_answer", ""),
                explanation=q.get("explanation", ""),
            )
            for i, q in enumerate(data.get("questions", []))
        ]
        return QuizResponse(language=language, questions=questions, locale=locale)
