"""Static Analyzer coordinating rule execution, complexity indicators, and syntax block splitting."""

from typing import Any
from backend.schemas.explanation import (
    CodeConstructs,
    StaticHint,
    SyntaxBlock,
)
from backend.services.analysis.rules import (
    BaseStaticRule,
    UnusedVariablesRule,
    DeepNestingRule,
    MissingReturnsRule,
)


class StaticAnalyzer:
    """Performs static lint analysis, complexity assessment, and block splitting."""

    def __init__(self, rules: list[BaseStaticRule] | None = None):
        if rules is None:
            self.rules: list[BaseStaticRule] = [
                UnusedVariablesRule(),
                DeepNestingRule(),
                MissingReturnsRule(),
            ]
        else:
            self.rules = rules

    def run_rules(
        self,
        code: str,
        language: str,
        ast_tree: Any,
        constructs: CodeConstructs,
    ) -> list[StaticHint]:
        """Execute all registered static analysis rules."""
        hints: list[StaticHint] = []
        for rule in self.rules:
            try:
                rule_hints = rule.analyze(code, language, ast_tree, constructs)
                hints.extend(rule_hints)
            except Exception:
                # Rules must never crash the analyzer
                continue
        return hints

    def split_syntax_blocks(
        self,
        code: str,
        constructs: CodeConstructs,
    ) -> list[SyntaxBlock]:
        """Split source code into logical, non-overlapping or hierarchical syntax blocks."""
        lines = code.splitlines()
        blocks: list[SyntaxBlock] = []
        block_counter = 1

        # 1. Imports block (if any imports present)
        if constructs.imports:
            start_l = min(i.line_start for i in constructs.imports)
            end_l = max(i.line_end for i in constructs.imports)
            block_code = "\n".join(lines[start_l - 1 : end_l])
            blocks.append(
                SyntaxBlock(
                    block_id=f"block_{block_counter}",
                    block_type="imports",
                    title="Import Statements",
                    line_start=start_l,
                    line_end=end_l,
                    code_content=block_code,
                    complexity_score=1,
                )
            )
            block_counter += 1

        # 2. Classes blocks
        for cls in constructs.classes:
            block_code = "\n".join(lines[cls.line_start - 1 : cls.line_end])
            blocks.append(
                SyntaxBlock(
                    block_id=f"block_{block_counter}",
                    block_type="class",
                    title=f"Class {cls.name}",
                    line_start=cls.line_start,
                    line_end=cls.line_end,
                    code_content=block_code,
                    complexity_score=1 + len(cls.methods),
                )
            )
            block_counter += 1

        # 3. Top-level Functions blocks
        class_ranges = [(c.line_start, c.line_end) for c in constructs.classes]
        for fn in constructs.functions:
            # Check if function is inside a class
            inside_class = any(start <= fn.line_start and fn.line_end <= end for start, end in class_ranges)
            if not inside_class:
                block_code = "\n".join(lines[fn.line_start - 1 : fn.line_end])
                blocks.append(
                    SyntaxBlock(
                        block_id=f"block_{block_counter}",
                        block_type="function",
                        title=f"{'Async ' if fn.is_async else ''}Function {fn.name}()",
                        line_start=fn.line_start,
                        line_end=fn.line_end,
                        code_content=block_code,
                        complexity_score=1,
                    )
                )
                block_counter += 1

        # If no structured blocks (functions/classes) found, create a top-level block
        if not blocks:
            blocks.append(
                SyntaxBlock(
                    block_id="block_1",
                    block_type="top_level",
                    title="Main Script Logic",
                    line_start=1,
                    line_end=len(lines) if lines else 1,
                    code_content=code,
                    complexity_score=1,
                )
            )

        return blocks
