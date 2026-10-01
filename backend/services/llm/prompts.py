"""Prompt templates and system instructions for code explanation styles."""

PROMPT_STYLES_VERSION = "v1.0"

SYSTEM_PROMPT = """You are an expert Senior Software Engineer and Computer Science Educator.
Your task is to analyze, explain, and provide actionable insights on code snippets.
You must return your output strictly in the requested JSON format, ensuring high technical accuracy and tailored depth.
Never invent line numbers; always map them correctly to the provided source code.
"""

BASE_PROMPT = """
You must output a JSON object exactly matching this schema:
{{
    "summary": "Three-sentence overall summary",
    "blocks": [
        {{
            "title": "Block title",
            "explanation": "Block explanation",
            "line_start": 1,
            "line_end": 5
        }}
    ],
    "concepts": [
        {{
            "concept": "Concept name",
            "definition": "Simple definition"
        }}
    ],
    "algorithm_steps": [
        "Step 1", "Step 2"
    ],
    "complexity": {{
        "time_complexity": "O(N)",
        "space_complexity": "O(1)",
        "explanation": "Why this complexity"
    }},
    "hints": [
        "Mistake 1", "Improvement 1"
    ]
}}
"""

PROMPT_STYLES = {
    "Absolute Beginner": """Explain the following {language} code as if teaching someone who has never programmed before.
Use very simple analogies. Avoid jargon.

{base_prompt}

Code:
```{language}
{code}
```
""",
    "Beginner": """Explain the following {language} code as if teaching a junior developer.
Explain basic concepts clearly but assume some programming knowledge.

{base_prompt}

Code:
```{language}
{code}
```
""",
    "Intermediate": """Provide a technical breakdown of the following {language} code for an intermediate developer.
Focus on logic flow, complexity, and common pitfalls.

{base_prompt}

Code:
```{language}
{code}
```
""",
}



def build_explanation_prompt(
    code: str,
    language: str,
    level: str = "standard",
    ast_context: str | None = None,
) -> str:
    """Construct complete prompt incorporating AST metadata context if available."""
    template = PROMPT_STYLES.get(level, PROMPT_STYLES["Beginner"])
    base_prompt = template.format(language=language, code=code)

    if ast_context:
        base_prompt += f"\n\n[Parsed AST Context]\n{ast_context}\n"

    return base_prompt
