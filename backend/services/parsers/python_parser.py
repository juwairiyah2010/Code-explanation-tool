"""Python AST Parser using the built-in ast module with comprehensive construct extraction and static analysis."""

import ast
from typing import Any
from backend.schemas.explanation import (
    ASTNodeInfo,
    AssignmentConstruct,
    CallConstruct,
    ClassConstruct,
    CodeAnalysisResponse,
    CodeConstructs,
    ConditionConstruct,
    FunctionConstruct,
    ImportConstruct,
    LoopConstruct,
    SyntaxErrorInfo,
)
from backend.services.analysis.static_analyzer import StaticAnalyzer
from backend.services.parsers.base import BaseCodeParser


class PythonComprehensiveASTVisitor(ast.NodeVisitor):
    """Visitor extracting all Python constructs, calls, assignments, loops, conditions, and nesting."""

    def __init__(self) -> None:
        self.functions: list[FunctionConstruct] = []
        self.classes: list[ClassConstruct] = []
        self.loops: list[LoopConstruct] = []
        self.conditions: list[ConditionConstruct] = []
        self.assignments: list[AssignmentConstruct] = []
        self.imports: list[ImportConstruct] = []
        self.calls: list[CallConstruct] = []

        self.complexity_score: int = 1
        self.max_nesting_depth: int = 0
        self._current_nesting: int = 0

    def _enter_nesting(self) -> None:
        self._current_nesting += 1
        if self._current_nesting > self.max_nesting_depth:
            self.max_nesting_depth = self._current_nesting

    def _exit_nesting(self) -> None:
        self._current_nesting = max(0, self._current_nesting - 1)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._process_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_function(node, is_async=True)
        self.generic_visit(node)

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        params = [arg.arg for arg in node.args.args]
        docstring = ast.get_docstring(node)
        end_lineno = getattr(node, "end_lineno", node.lineno)
        return_type = ast.unparse(node.returns) if getattr(node, "returns", None) else None

        self.functions.append(
            FunctionConstruct(
                name=node.name,
                parameters=params,
                is_async=is_async,
                docstring=docstring,
                line_start=node.lineno,
                line_end=end_lineno,
                return_type=return_type,
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        docstring = ast.get_docstring(node)
        end_lineno = getattr(node, "end_lineno", node.lineno)
        bases = [ast.unparse(b) for b in node.bases]
        methods = [
            n.name
            for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        self.classes.append(
            ClassConstruct(
                name=node.name,
                bases=bases,
                methods=methods,
                docstring=docstring,
                line_start=node.lineno,
                line_end=end_lineno,
            )
        )
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity_score += 1
        self._enter_nesting()
        target_str = ast.unparse(node.target) if hasattr(ast, "unparse") else "target"
        self.loops.append(
            LoopConstruct(
                loop_type="for",
                target=target_str,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
            )
        )
        self.generic_visit(node)
        self._exit_nesting()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity_score += 1
        self._enter_nesting()
        target_str = ast.unparse(node.target) if hasattr(ast, "unparse") else "target"
        self.loops.append(
            LoopConstruct(
                loop_type="async_for",
                target=target_str,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
            )
        )
        self.generic_visit(node)
        self._exit_nesting()

    def visit_While(self, node: ast.While) -> None:
        self.complexity_score += 1
        self._enter_nesting()
        test_str = ast.unparse(node.test) if hasattr(ast, "unparse") else "condition"
        self.loops.append(
            LoopConstruct(
                loop_type="while",
                target=test_str,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
            )
        )
        self.generic_visit(node)
        self._exit_nesting()

    def visit_If(self, node: ast.If) -> None:
        self.complexity_score += 1
        self._enter_nesting()
        test_str = ast.unparse(node.test) if hasattr(ast, "unparse") else "condition"
        self.conditions.append(
            ConditionConstruct(
                condition_type="if",
                test_expression=test_str,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
            )
        )
        self.generic_visit(node)
        self._exit_nesting()

    def visit_Assign(self, node: ast.Assign) -> None:
        targets = [ast.unparse(t) for t in node.targets if hasattr(ast, "unparse")]
        self.assignments.append(
            AssignmentConstruct(
                targets=targets,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                is_constant=False,
            )
        )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        target = ast.unparse(node.target) if hasattr(ast, "unparse") else "target"
        self.assignments.append(
            AssignmentConstruct(
                targets=[target],
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                is_constant=False,
            )
        )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportConstruct(
                    module=alias.name,
                    names=[alias.name],
                    alias=alias.asname,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        names = [a.name for a in node.names]
        self.imports.append(
            ImportConstruct(
                module=module,
                names=names,
                alias=node.names[0].asname if len(node.names) == 1 else None,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
            )
        )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        callee = ast.unparse(node.func) if hasattr(ast, "unparse") else "callee"
        self.calls.append(
            CallConstruct(
                callee=callee,
                arg_count=len(node.args) + len(node.keywords),
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
            )
        )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity_score += len(node.values) - 1
        self.generic_visit(node)


class PythonCodeParser(BaseCodeParser):
    """Parses Python source code, extracts rich constructs, checks static rules, and splits syntax blocks."""

    def __init__(self) -> None:
        self.analyzer = StaticAnalyzer()

    def parse(self, code: str, detection_method: str = "explicit") -> CodeAnalysisResponse:
        lines = code.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))

        if not code.strip():
            return CodeAnalysisResponse(
                language="python",
                detection_method=detection_method,
                is_valid_syntax=True,
                syntax_error=None,
                syntax_errors=[],
                blocks=[],
                constructs=CodeConstructs(),
                static_hints=[],
                complexity_score=1,
                max_nesting_depth=0,
                metrics={
                    "total_lines": total_lines,
                    "code_lines": 0,
                    "blank_lines": blank_lines,
                    "comment_lines": comment_lines,
                },
            )

        try:
            tree = ast.parse(code)
            visitor = PythonComprehensiveASTVisitor()
            visitor.visit(tree)

            constructs = CodeConstructs(
                functions=visitor.functions,
                classes=visitor.classes,
                loops=visitor.loops,
                conditions=visitor.conditions,
                assignments=visitor.assignments,
                imports=visitor.imports,
                calls=visitor.calls,
            )

            # Run static rules
            static_hints = self.analyzer.run_rules(code, "python", tree, constructs)

            # Split code into syntax blocks
            blocks = self.analyzer.split_syntax_blocks(code, constructs)

            # Backward-compatibility legacy fields
            legacy_functions = [
                ASTNodeInfo(
                    name=f.name,
                    node_type="AsyncFunctionDef" if f.is_async else "FunctionDef",
                    line_start=f.line_start,
                    line_end=f.line_end,
                    docstring=f.docstring,
                    parameters=f.parameters,
                )
                for f in visitor.functions
            ]
            legacy_classes = [
                ASTNodeInfo(
                    name=c.name,
                    node_type="ClassDef",
                    line_start=c.line_start,
                    line_end=c.line_end,
                    docstring=c.docstring,
                    parameters=[],
                )
                for c in visitor.classes
            ]
            legacy_imports = [imp.module for imp in visitor.imports]

            metrics: dict[str, Any] = {
                "total_lines": total_lines,
                "code_lines": total_lines - blank_lines - comment_lines,
                "blank_lines": blank_lines,
                "comment_lines": comment_lines,
                "num_functions": len(visitor.functions),
                "num_classes": len(visitor.classes),
                "num_loops": len(visitor.loops),
                "num_conditions": len(visitor.conditions),
                "num_assignments": len(visitor.assignments),
                "num_imports": len(visitor.imports),
                "num_calls": len(visitor.calls),
                "num_blocks": len(blocks),
                "num_hints": len(static_hints),
            }

            return CodeAnalysisResponse(
                language="python",
                detection_method=detection_method,
                is_valid_syntax=True,
                syntax_error=None,
                syntax_errors=[],
                blocks=blocks,
                constructs=constructs,
                static_hints=static_hints,
                complexity_score=visitor.complexity_score,
                max_nesting_depth=visitor.max_nesting_depth,
                metrics=metrics,
                functions=legacy_functions,
                classes=legacy_classes,
                imports=legacy_imports,
            )

        except SyntaxError as e:
            error_msg = f"Line {e.lineno}, Col {e.offset}: {e.msg}"
            syntax_err = SyntaxErrorInfo(
                line=e.lineno or 1,
                column=e.offset or 1,
                message=e.msg or "Syntax error",
            )
            return CodeAnalysisResponse(
                language="python",
                detection_method=detection_method,
                is_valid_syntax=False,
                syntax_error=error_msg,
                syntax_errors=[syntax_err],
                blocks=[],
                constructs=CodeConstructs(),
                static_hints=[],
                complexity_score=1,
                max_nesting_depth=0,
                metrics={"total_lines": total_lines, "error_line": e.lineno},
                functions=[],
                classes=[],
                imports=[],
            )
        except Exception as e:
            return CodeAnalysisResponse(
                language="python",
                detection_method=detection_method,
                is_valid_syntax=False,
                syntax_error=str(e),
                syntax_errors=[SyntaxErrorInfo(line=1, column=1, message=str(e))],
                blocks=[],
                constructs=CodeConstructs(),
                static_hints=[],
                complexity_score=1,
                max_nesting_depth=0,
                metrics={"total_lines": total_lines},
                functions=[],
                classes=[],
                imports=[],
            )
