"""JavaScript AST Parser using Tree-sitter with comprehensive construct extraction, static rules, and fallback."""

import re
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

# Check Tree-sitter availability
TREE_SITTER_AVAILABLE = False
try:
    import tree_sitter
    import tree_sitter_javascript

    JS_LANGUAGE = tree_sitter.Language(tree_sitter_javascript.language())
    TREE_SITTER_AVAILABLE = True
except Exception:
    TREE_SITTER_AVAILABLE = False


class JavaScriptCodeParser(BaseCodeParser):
    """Parses JavaScript / TypeScript code using Tree-sitter with comprehensive construct extraction."""

    def __init__(self) -> None:
        self.analyzer = StaticAnalyzer()
        self.parser = None
        if TREE_SITTER_AVAILABLE:
            try:
                self.parser = tree_sitter.Parser(JS_LANGUAGE)
            except Exception:
                self.parser = None

    def parse(self, code: str, detection_method: str = "explicit") -> CodeAnalysisResponse:
        lines = code.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(
            1 for line in lines if line.strip().startswith("//") or line.strip().startswith("/*")
        )

        if not code.strip():
            return CodeAnalysisResponse(
                language="javascript",
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

        if self.parser:
            return self._parse_with_tree_sitter(code, total_lines, blank_lines, comment_lines, detection_method)
        else:
            return self._parse_with_fallback(code, total_lines, blank_lines, comment_lines, detection_method)

    def _parse_with_tree_sitter(
        self,
        code: str,
        total_lines: int,
        blank_lines: int,
        comment_lines: int,
        detection_method: str,
    ) -> CodeAnalysisResponse:
        try:
            tree = self.parser.parse(bytes(code, "utf8"))
            root = tree.root_node

            functions: list[FunctionConstruct] = []
            classes: list[ClassConstruct] = []
            loops: list[LoopConstruct] = []
            conditions: list[ConditionConstruct] = []
            assignments: list[AssignmentConstruct] = []
            imports: list[ImportConstruct] = []
            calls: list[CallConstruct] = []

            complexity = 1
            max_nesting = 0
            current_nesting = 0
            has_error = False
            syntax_errors: list[SyntaxErrorInfo] = []

            def enter_nest():
                nonlocal current_nesting, max_nesting
                current_nesting += 1
                if current_nesting > max_nesting:
                    max_nesting = current_nesting

            def exit_nest():
                nonlocal current_nesting
                current_nesting = max(0, current_nesting - 1)

            def traverse(node: Any) -> None:
                nonlocal complexity, has_error

                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1

                # Check for syntax error nodes
                if node.type == "ERROR" or node.is_missing:
                    has_error = True
                    syntax_errors.append(
                        SyntaxErrorInfo(
                            line=start_l,
                            column=node.start_point[1] + 1,
                            message=f"Syntax error at line {start_l}, col {node.start_point[1] + 1}",
                        )
                    )

                # 1. Functions
                if node.type in ("function_declaration", "generator_function_declaration"):
                    name = "anonymous"
                    params = []
                    is_async = False
                    for child in node.children:
                        if child.type == "async":
                            is_async = True
                        elif child.type == "identifier":
                            name = child.text.decode("utf8")
                        elif child.type == "formal_parameters":
                            params = [
                                p.text.decode("utf8")
                                for p in child.children
                                if p.type in ("identifier", "pattern", "required_parameter")
                            ]
                    functions.append(
                        FunctionConstruct(
                            name=name,
                            parameters=params,
                            is_async=is_async,
                            line_start=start_l,
                            line_end=end_l,
                        )
                    )

                elif node.type in ("lexical_declaration", "variable_declaration"):
                    # Extract variables & arrow functions
                    is_const = any(c.type == "const" for c in node.children)
                    for decl in node.children:
                        if decl.type == "variable_declarator":
                            var_name = None
                            is_arrow = False
                            arrow_params = []
                            is_async_arrow = False
                            for child in decl.children:
                                if child.type == "identifier":
                                    var_name = child.text.decode("utf8")
                                elif child.type == "arrow_function":
                                    is_arrow = True
                                    for sub in child.children:
                                        if sub.type == "async":
                                            is_async_arrow = True
                                        elif sub.type in ("formal_parameters", "identifier"):
                                            if sub.type == "identifier":
                                                arrow_params = [sub.text.decode("utf8")]
                                            else:
                                                arrow_params = [
                                                    p.text.decode("utf8")
                                                    for p in sub.children
                                                    if p.type in ("identifier", "pattern")
                                                ]
                            if var_name:
                                if is_arrow:
                                    functions.append(
                                        FunctionConstruct(
                                            name=var_name,
                                            parameters=arrow_params,
                                            is_async=is_async_arrow,
                                            line_start=start_l,
                                            line_end=end_l,
                                        )
                                    )
                                else:
                                    assignments.append(
                                        AssignmentConstruct(
                                            targets=[var_name],
                                            line_start=start_l,
                                            line_end=end_l,
                                            is_constant=is_const,
                                        )
                                    )

                elif node.type == "method_definition":
                    name = "method"
                    params = []
                    is_async = False
                    for child in node.children:
                        if child.type == "async":
                            is_async = True
                        elif child.type == "property_identifier":
                            name = child.text.decode("utf8")
                        elif child.type == "formal_parameters":
                            params = [
                                p.text.decode("utf8")
                                for p in child.children
                                if p.type in ("identifier", "pattern")
                            ]
                    functions.append(
                        FunctionConstruct(
                            name=name,
                            parameters=params,
                            is_async=is_async,
                            line_start=start_l,
                            line_end=end_l,
                        )
                    )

                # 2. Classes
                elif node.type == "class_declaration":
                    name = "anonymous"
                    bases = []
                    methods = []
                    for child in node.children:
                        if child.type == "identifier":
                            name = child.text.decode("utf8")
                        elif child.type == "class_heritage":
                            bases = [child.text.decode("utf8").replace("extends ", "").strip()]
                        elif child.type == "class_body":
                            for m in child.children:
                                if m.type == "method_definition":
                                    for sub in m.children:
                                        if sub.type == "property_identifier":
                                            methods.append(sub.text.decode("utf8"))
                    classes.append(
                        ClassConstruct(
                            name=name,
                            bases=bases,
                            methods=methods,
                            line_start=start_l,
                            line_end=end_l,
                        )
                    )

                # 3. Loops
                elif node.type in ("for_statement", "for_in_statement", "for_of_statement", "while_statement", "do_statement"):
                    complexity += 1
                    enter_nest()
                    loops.append(
                        LoopConstruct(
                            loop_type=node.type.replace("_statement", ""),
                            target=node.text.decode("utf8")[:40],
                            line_start=start_l,
                            line_end=end_l,
                        )
                    )

                # 4. Conditions
                elif node.type in ("if_statement", "switch_statement", "ternary_expression"):
                    complexity += 1
                    enter_nest()
                    conditions.append(
                        ConditionConstruct(
                            condition_type="if" if "if" in node.type else node.type,
                            test_expression=node.text.decode("utf8")[:40],
                            line_start=start_l,
                            line_end=end_l,
                        )
                    )

                # 5. Imports
                elif node.type == "import_statement":
                    import_str = node.text.decode("utf8").strip()
                    imports.append(
                        ImportConstruct(
                            module=import_str,
                            names=[import_str],
                            line_start=start_l,
                            line_end=end_l,
                        )
                    )

                # 6. Function Calls
                elif node.type == "call_expression":
                    callee_node = node.child_by_field_name("function")
                    callee_name = callee_node.text.decode("utf8") if callee_node else "call"
                    args_node = node.child_by_field_name("arguments")
                    arg_count = len(args_node.children) // 2 if args_node else 0
                    calls.append(
                        CallConstruct(
                            callee=callee_name,
                            arg_count=max(0, arg_count),
                            line_start=start_l,
                            line_end=end_l,
                        )
                    )

                # Binary branching
                elif node.type == "binary_expression":
                    op = node.child_by_field_name("operator")
                    if op and op.text.decode("utf8") in ("&&", "||", "??"):
                        complexity += 1

                for child in node.children:
                    traverse(child)

                if node.type in (
                    "if_statement",
                    "switch_statement",
                    "for_statement",
                    "for_in_statement",
                    "for_of_statement",
                    "while_statement",
                    "do_statement",
                ):
                    exit_nest()

            traverse(root)

            constructs = CodeConstructs(
                functions=functions,
                classes=classes,
                loops=loops,
                conditions=conditions,
                assignments=assignments,
                imports=imports,
                calls=calls,
            )

            # Static rules & blocks
            static_hints = self.analyzer.run_rules(code, "javascript", tree, constructs)
            blocks = self.analyzer.split_syntax_blocks(code, constructs)

            # Legacy fields
            legacy_functions = [
                ASTNodeInfo(
                    name=f.name,
                    node_type="function_declaration",
                    line_start=f.line_start,
                    line_end=f.line_end,
                    parameters=f.parameters,
                )
                for f in functions
            ]
            legacy_classes = [
                ASTNodeInfo(
                    name=c.name,
                    node_type="class_declaration",
                    line_start=c.line_start,
                    line_end=c.line_end,
                    parameters=[],
                )
                for c in classes
            ]
            legacy_imports = [imp.module for imp in imports]

            metrics = {
                "total_lines": total_lines,
                "code_lines": total_lines - blank_lines - comment_lines,
                "blank_lines": blank_lines,
                "comment_lines": comment_lines,
                "num_functions": len(functions),
                "num_classes": len(classes),
                "num_loops": len(loops),
                "num_conditions": len(conditions),
                "num_assignments": len(assignments),
                "num_imports": len(imports),
                "num_calls": len(calls),
                "num_blocks": len(blocks),
                "num_hints": len(static_hints),
                "parser_engine": "tree-sitter",
            }

            primary_err = syntax_errors[0].message if syntax_errors else None

            return CodeAnalysisResponse(
                language="javascript",
                detection_method=detection_method,
                is_valid_syntax=not has_error,
                syntax_error=primary_err,
                syntax_errors=syntax_errors,
                blocks=blocks,
                constructs=constructs,
                static_hints=static_hints,
                complexity_score=max(1, complexity),
                max_nesting_depth=max_nesting,
                metrics=metrics,
                functions=legacy_functions,
                classes=legacy_classes,
                imports=legacy_imports,
            )

        except Exception as e:
            return self._parse_with_fallback(code, total_lines, blank_lines, comment_lines, detection_method, str(e))

    def _parse_with_fallback(
        self,
        code: str,
        total_lines: int,
        blank_lines: int,
        comment_lines: int,
        detection_method: str = "explicit",
        prev_error: str | None = None,
    ) -> CodeAnalysisResponse:
        """Heuristic regex parsing when Tree-sitter parser is not initialized."""
        functions = []
        classes = []
        loops = []
        conditions = []
        assignments = []
        imports = []
        calls = []
        complexity = 1

        # Functions
        for m in re.finditer(r"function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)", code):
            line_no = code[: m.start()].count("\n") + 1
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            functions.append(
                FunctionConstruct(
                    name=m.group(1),
                    parameters=params,
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        # Arrow functions & variable declarations
        for m in re.finditer(r"\b(const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?(?:\(([^)]*)\)|([a-zA-Z0-9_$]+))\s*=>", code):
            line_no = code[: m.start()].count("\n") + 1
            raw_params = m.group(3) or m.group(4) or ""
            params = [p.strip() for p in raw_params.split(",") if p.strip()]
            functions.append(
                FunctionConstruct(
                    name=m.group(2),
                    parameters=params,
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        # Standard assignments
        for m in re.finditer(r"\b(const|let|var)\s+([a-zA-Z0-9_$]+)\s*=", code):
            line_no = code[: m.start()].count("\n") + 1
            is_const = m.group(1) == "const"
            assignments.append(
                AssignmentConstruct(
                    targets=[m.group(2)],
                    line_start=line_no,
                    line_end=line_no,
                    is_constant=is_const,
                )
            )

        # Classes
        for m in re.finditer(r"class\s+([a-zA-Z0-9_$]+)(?:\s+extends\s+([a-zA-Z0-9_$]+))?", code):
            line_no = code[: m.start()].count("\n") + 1
            bases = [m.group(2)] if m.group(2) else []
            classes.append(
                ClassConstruct(
                    name=m.group(1),
                    bases=bases,
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        # Loops
        for m in re.finditer(r"\b(for|while|do)\b", code):
            line_no = code[: m.start()].count("\n") + 1
            loops.append(
                LoopConstruct(
                    loop_type=m.group(1),
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        # Conditions
        for m in re.finditer(r"\b(if|switch)\b", code):
            line_no = code[: m.start()].count("\n") + 1
            conditions.append(
                ConditionConstruct(
                    condition_type=m.group(1),
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        # Imports
        for m in re.finditer(r"import\s+.*?;|const\s+.*=\s*require\(.*?\);", code):
            line_no = code[: m.start()].count("\n") + 1
            imports.append(
                ImportConstruct(
                    module=m.group(0).strip(),
                    names=[m.group(0).strip()],
                    line_start=line_no,
                    line_end=line_no,
                )
            )

        complexity += len(loops) + len(conditions)

        constructs = CodeConstructs(
            functions=functions,
            classes=classes,
            loops=loops,
            conditions=conditions,
            assignments=assignments,
            imports=imports,
            calls=calls,
        )

        static_hints = self.analyzer.run_rules(code, "javascript", None, constructs)
        blocks = self.analyzer.split_syntax_blocks(code, constructs)

        legacy_functions = [
            ASTNodeInfo(
                name=f.name,
                node_type="function_declaration",
                line_start=f.line_start,
                line_end=f.line_end,
                parameters=f.parameters,
            )
            for f in functions
        ]
        legacy_classes = [
            ASTNodeInfo(
                name=c.name,
                node_type="class_declaration",
                line_start=c.line_start,
                line_end=c.line_end,
                parameters=[],
            )
            for c in classes
        ]

        metrics = {
            "total_lines": total_lines,
            "code_lines": total_lines - blank_lines - comment_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "num_functions": len(functions),
            "num_classes": len(classes),
            "num_loops": len(loops),
            "num_conditions": len(conditions),
            "num_assignments": len(assignments),
            "num_imports": len(imports),
            "num_blocks": len(blocks),
            "num_hints": len(static_hints),
            "parser_engine": "heuristic_fallback",
        }

        return CodeAnalysisResponse(
            language="javascript",
            detection_method=detection_method,
            is_valid_syntax=True,
            syntax_error=prev_error,
            syntax_errors=[],
            blocks=blocks,
            constructs=constructs,
            static_hints=static_hints,
            complexity_score=max(1, complexity),
            max_nesting_depth=1,
            metrics=metrics,
            functions=legacy_functions,
            classes=legacy_classes,
            imports=[i.module for i in imports],
        )
