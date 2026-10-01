import pytest
from backend.services.explanation_service import ExplanationService
from backend.schemas.explanation import ExplainCodeRequest, CodeAnalysisResponse, SyntaxBlock
from backend.services.llm.base import BaseLLMService, LLMExplanationResult
from backend.schemas.explanation import AlgorithmComplexity, BlockExplanation, ConceptTag
import asyncio

class FailOnceLLM(BaseLLMService):
    def __init__(self):
        self.calls = 0

    async def generate_explanation(self, code, language, level, ast_context=None, required_blocks=None):
        self.calls += 1
        blocks = []
        if self.calls == 1 and required_blocks:
            # Drop the last block to simulate failure
            for rb in required_blocks[:-1]:
                blocks.append(BlockExplanation(title=rb.title, explanation="Expl", line_start=rb.line_start, line_end=rb.line_end))
        elif required_blocks:
            # On retry, return what was asked
            for rb in required_blocks:
                blocks.append(BlockExplanation(title=rb.title, explanation="Expl Retry", line_start=rb.line_start, line_end=rb.line_end))
                
        # Simulate an invalid line reference in the returned blocks if calls == 1
        if self.calls == 1 and blocks:
            blocks[0].line_start = -1
            blocks[0].line_end = 999
            
        return LLMExplanationResult(
            summary="Test",
            blocks=blocks,
            concepts=[],
            algorithm_steps=[],
            complexity=AlgorithmComplexity(time_complexity="O(1)", space_complexity="O(1)", explanation=""),
            hints=[]
        )
    
    async def generate_quiz(self, code, language, explanation_context=None, locale="en"):
        pass


@pytest.mark.asyncio
async def test_hybrid_engine_coverage_retry_and_line_validation():
    # Mocking db since it's not actually used if save_history=False
    svc = ExplanationService(db=None)
    svc.llm = FailOnceLLM()
    
    # We will pass a python code snippet with 3 lines
    req = ExplainCodeRequest(
        code="def foo():\n    pass\nfoo()",
        language="python",
        level="Beginner",
        include_ast_analysis=True,
        save_history=False
    )
    
    res = await svc.explain_code(req)
    
    # Check calls
    assert svc.llm.calls == 2 # 1 initial + 1 retry
    
    # Check blocks are sorted and complete
    # Should have top level and function block (assuming AST parses them)
    # The parser gives 'Function: foo' and maybe 'Top-level'
    assert len(res.blocks) >= 1
    
    # Check that line references were bounded to 1..3
    assert res.blocks[0].line_start >= 1
    assert res.blocks[0].line_end <= 3

class DuplicatesLLM(BaseLLMService):
    async def generate_explanation(self, code, language, level, ast_context=None, required_blocks=None):
        blocks = []
        if required_blocks:
            for rb in required_blocks:
                blocks.append(BlockExplanation(title=rb.title, explanation="Expl", line_start=rb.line_start, line_end=rb.line_end))
                # Add a duplicate
                blocks.append(BlockExplanation(title=rb.title, explanation="Expl Dup", line_start=rb.line_start, line_end=rb.line_end))
        return LLMExplanationResult(summary="Test", blocks=blocks, concepts=[], algorithm_steps=[], complexity=AlgorithmComplexity(time_complexity="", space_complexity="", explanation=""), hints=[])
    
    async def generate_quiz(self, code, language, explanation_context=None, locale="en"):
        pass

@pytest.mark.asyncio
async def test_duplicate_explanations():
    svc = ExplanationService(db=None)
    svc.llm = DuplicatesLLM()
    req = ExplainCodeRequest(code="def a():\n    pass", language="python", level="Beginner", include_ast_analysis=True, save_history=False)
    res = await svc.explain_code(req)
    
    # Check that duplicates by title are still handled gracefully or kept if intentional?
    # Our engine currently just merges them. But let's check it doesn't crash.
    assert len(res.blocks) > 0

class MalformedLLM(BaseLLMService):
    async def generate_explanation(self, code, language, level, ast_context=None, required_blocks=None):
        raise ValueError("Malformed AI Response JSON")
        
    async def generate_quiz(self, code, language, explanation_context=None, locale="en"):
        pass

@pytest.mark.asyncio
async def test_malformed_ai_response():
    svc = ExplanationService(db=None)
    svc.llm = MalformedLLM()
    req = ExplainCodeRequest(code="x = 1", language="python", level="Beginner", include_ast_analysis=True, save_history=False)
    with pytest.raises(ValueError, match="Malformed AI Response JSON"):
        await svc.explain_code(req)
