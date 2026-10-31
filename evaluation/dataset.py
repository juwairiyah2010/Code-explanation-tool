"""Benchmark dataset for Code Lore evaluation framework.

Contains representative, deterministic Python and JavaScript programs spanning
core syntax constructs, algorithmic complexity, error conditions, beginner mistakes,
inefficiencies, and security-critical patterns.
"""

from dataclasses import dataclass, field


@dataclass
class BenchmarkCase:
    case_id: str
    name: str
    language: str  # "python" or "javascript"
    category: str
    code: str
    description: str
    expected_relevant_lines: list[int]
    expected_constructs: list[str]  # e.g., ["functions", "loops", "classes", "conditions"]
    expected_complexity_range: tuple[int, int]  # (min, max)
    expected_deterministic_output: str | None
    expected_concepts: list[str]
    expected_findings: list[str] = field(default_factory=list)
    is_traceable: bool = False  # Deterministic execution in isolated Python sandbox


BENCHMARK_DATASET: list[BenchmarkCase] = [
    # ── 1. Python: Basic Variables ─────────────────────────────────────
    BenchmarkCase(
        case_id="py_basic_variables",
        name="Python Variable Calculations",
        language="python",
        category="basic_variables",
        code=(
            "width = 10\n"
            "height = 5\n"
            "area = width * height\n"
            "perimeter = 2 * (width + height)\n"
            "print(f\"Area: {area}, Perimeter: {perimeter}\")\n"
        ),
        description="Sequential variable assignment and arithmetic arithmetic operations.",
        expected_relevant_lines=[1, 2, 3, 4, 5],
        expected_constructs=["assignments"],
        expected_complexity_range=(1, 1),
        expected_deterministic_output="Area: 50, Perimeter: 30\n",
        expected_concepts=["variables", "arithmetic", "assignment"],
        expected_findings=[],
        is_traceable=True,
    ),

    # ── 2. Python: Conditionals ────────────────────────────────────────
    BenchmarkCase(
        case_id="py_conditionals",
        name="Python Age Category Classifier",
        language="python",
        category="conditionals",
        code=(
            "def classify_age(age: int) -> str:\n"
            "    if age < 0:\n"
            "        return \"invalid\"\n"
            "    elif age < 13:\n"
            "        return \"child\"\n"
            "    elif age < 20:\n"
            "        return \"teen\"\n"
            "    else:\n"
            "        return \"adult\"\n"
            "\n"
            "status = classify_age(15)\n"
            "print(f\"Status: {status}\")\n"
        ),
        description="Multi-branch if/elif/else decision control flow.",
        expected_relevant_lines=[1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12],
        expected_constructs=["functions", "conditions"],
        expected_complexity_range=(3, 5),
        expected_deterministic_output="Status: teen\n",
        expected_concepts=["conditionals", "functions", "branching"],
        expected_findings=[],
        is_traceable=True,
    ),

    # ── 3. Python: Loops ───────────────────────────────────────────────
    BenchmarkCase(
        case_id="py_loops",
        name="Python Loop Aggregation",
        language="python",
        category="loops",
        code=(
            "numbers = [1, 2, 3, 4, 5]\n"
            "total = 0\n"
            "for num in numbers:\n"
            "    if num % 2 != 0:\n"
            "        total += num\n"
            "print(f\"Odd Sum: {total}\")\n"
        ),
        description="Iterating over a collection with conditional filter and accumulator.",
        expected_relevant_lines=[1, 2, 3, 4, 5, 6],
        expected_constructs=["loops", "conditions"],
        expected_complexity_range=(2, 3),
        expected_deterministic_output="Odd Sum: 9\n",
        expected_concepts=["loops", "iteration", "modulo"],
        expected_findings=[],
        is_traceable=True,
    ),

    # ── 4. Python: Functions ───────────────────────────────────────────
    BenchmarkCase(
        case_id="py_functions",
        name="Python Pure Function and Multiplication",
        language="python",
        category="functions",
        code=(
            "def calculate_tax(subtotal: float, rate: float = 0.05) -> float:\n"
            "    \"\"\"Calculate total tax on a given subtotal.\"\"\"\n"
            "    return round(subtotal * rate, 2)\n"
            "\n"
            "order_tax = calculate_tax(100.0, 0.08)\n"
            "print(f\"Tax: {order_tax}\")\n"
        ),
        description="Function definition with default parameters and type annotations.",
        expected_relevant_lines=[1, 3, 5, 6],
        expected_constructs=["functions", "calls"],
        expected_complexity_range=(1, 2),
        expected_deterministic_output="Tax: 8.0\n",
        expected_concepts=["functions", "parameters", "return value"],
        expected_findings=[],
        is_traceable=True,
    ),

    # ── 5. Python: Recursion ───────────────────────────────────────────
    BenchmarkCase(
        case_id="py_recursion",
        name="Python Recursive Fibonacci",
        language="python",
        category="recursion",
        code=(
            "def fibonacci(n: int) -> int:\n"
            "    if n <= 0:\n"
            "        return 0\n"
            "    elif n == 1:\n"
            "        return 1\n"
            "    return fibonacci(n - 1) + fibonacci(n - 2)\n"
            "\n"
            "res = fibonacci(5)\n"
            "print(f\"Fib 5: {res}\")\n"
        ),
        description="Recursive algorithm with dual base cases and branching calls.",
        expected_relevant_lines=[1, 2, 3, 4, 5, 6, 8, 9],
        expected_constructs=["functions", "conditions", "calls"],
        expected_complexity_range=(3, 4),
        expected_deterministic_output="Fib 5: 5\n",
        expected_concepts=["recursion", "base case", "call stack"],
        expected_findings=[],
        is_traceable=True,
    ),

    # ── 6. Python: Classes ─────────────────────────────────────────────
    BenchmarkCase(
        case_id="py_classes",
        name="Python Bank Account Class",
        language="python",
        category="classes",
        code=(
            "class BankAccount:\n"
            "    def __init__(self, owner: str, balance: float = 0.0):\n"
            "        self.owner = owner\n"
            "        self.balance = balance\n"
            "\n"
            "    def deposit(self, amount: float) -> float:\n"
            "        if amount > 0:\n"
            "            self.balance += amount\n"
            "        return self.balance\n"
            "\n"
            "account = BankAccount(\"Alice\", 100.0)\n"
            "account.deposit(50.0)\n"
            "print(f\"{account.owner}: {account.balance}\")\n"
        ),
        description="Object-oriented class with constructor, instance methods, and state mutation.",
        expected_relevant_lines=[1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13],
        expected_constructs=["classes", "functions", "conditions"],
        expected_complexity_range=(2, 6),
        expected_deterministic_output="Alice: 150.0\n",
        expected_concepts=["classes", "methods", "object-oriented programming"],
        expected_findings=[],
        is_traceable=True,
    ),

    # ── 7. Python: Exceptions ──────────────────────────────────────────
    BenchmarkCase(
        case_id="py_exceptions",
        name="Python Safe Division with Handled Exception",
        language="python",
        category="exceptions",
        code=(
            "def safe_divide(a: float, b: float) -> float | None:\n"
            "    try:\n"
            "        return a / b\n"
            "    except ZeroDivisionError:\n"
            "        print(\"Error: cannot divide by zero\")\n"
            "        return None\n"
            "\n"
            "ans = safe_divide(10, 0)\n"
            "print(f\"Result: {ans}\")\n"
        ),
        description="Explicit exception handling catching ZeroDivisionError gracefully.",
        expected_relevant_lines=[1, 2, 3, 4, 5, 6, 8, 9],
        expected_constructs=["functions", "calls"],
        expected_complexity_range=(2, 3),
        expected_deterministic_output="Error: cannot divide by zero\nResult: None\n",
        expected_concepts=["exceptions", "try except", "error handling"],
        expected_findings=[],
        is_traceable=True,
    ),

    # ── 8. Python: Common Beginner Mistakes ────────────────────────────
    BenchmarkCase(
        case_id="py_beginner_mistake",
        name="Python Shadowed Builtin and Bare Except",
        language="python",
        category="common_beginner_mistakes",
        code=(
            "def get_first_item(list, id):\n"
            "    try:\n"
            "        return list[0]\n"
            "    except:\n"
            "        return None\n"
        ),
        description="Antipatterns: shadowing built-in 'list' and using a bare except clause.",
        expected_relevant_lines=[1, 2, 3, 4, 5],
        expected_constructs=["functions"],
        expected_complexity_range=(2, 3),
        expected_deterministic_output=None,
        expected_concepts=["shadowing", "bare except", "error handling"],
        expected_findings=["SHADOWED_BUILTIN", "BARE_EXCEPT"],
        is_traceable=False,
    ),

    # ── 9. Python: Inefficient Code ────────────────────────────────────
    BenchmarkCase(
        case_id="py_inefficient_code",
        name="Python Repeated String Concatenation in Loop",
        language="python",
        category="inefficient_code",
        code=(
            "def build_csv_string(rows: list) -> str:\n"
            "    out_str = \"\"\n"
            "    for row in rows:\n"
            "        out_str += str(row) + \",\"\n"
            "    return out_str\n"
        ),
        description="Antipattern: in-place string concatenation inside a loop causing O(N^2) churn.",
        expected_relevant_lines=[1, 2, 3, 4, 5],
        expected_constructs=["functions", "loops"],
        expected_complexity_range=(2, 3),
        expected_deterministic_output=None,
        expected_concepts=["performance", "string immutability", "loop efficiency"],
        expected_findings=["INEFFICIENT_STRING_CONCAT"],
        is_traceable=False,
    ),

    # ── 10. Python: Security-Related Example ───────────────────────────
    BenchmarkCase(
        case_id="py_security_eval",
        name="Python Dynamic Eval and Hardcoded Secret",
        language="python",
        category="security_related",
        code=(
            "api_key = \"AKIAIOSFODNN7EXAMPLE\"\n"
            "def execute_user_formula(formula_str: str):\n"
            "    return eval(formula_str)\n"
        ),
        description="High-severity security risks: raw eval() execution and hardcoded API secret.",
        expected_relevant_lines=[1, 2, 3],
        expected_constructs=["functions", "assignments"],
        expected_complexity_range=(1, 2),
        expected_deterministic_output=None,
        expected_concepts=["security", "code injection", "secret management"],
        expected_findings=["DANGEROUS_EVAL", "HARDCODED_SECRET"],
        is_traceable=False,
    ),

    # ── 11. JavaScript: Basic Variables & Functions ────────────────────
    BenchmarkCase(
        case_id="js_basic_variables_and_functions",
        name="JavaScript Pure Math Function",
        language="javascript",
        category="basic_variables",
        code=(
            "function calculateVolume(length, width, height) {\n"
            "    const baseArea = length * width;\n"
            "    const volume = baseArea * height;\n"
            "    return volume;\n"
            "}\n"
            "const boxVolume = calculateVolume(3, 4, 5);\n"
            "console.log(`Volume: ${boxVolume}`);\n"
        ),
        description="JavaScript variable declarations and modular function calculation.",
        expected_relevant_lines=[1, 2, 3, 4, 6, 7],
        expected_constructs=["functions", "assignments", "calls"],
        expected_complexity_range=(1, 2),
        expected_deterministic_output="Volume: 60\n",
        expected_concepts=["variables", "functions", "template literals"],
        expected_findings=[],
        is_traceable=False,
    ),

    # ── 12. JavaScript: Loops and Conditionals ─────────────────────────
    BenchmarkCase(
        case_id="js_loops_and_conditionals",
        name="JavaScript Array Filter and Accumulator",
        language="javascript",
        category="loops",
        code=(
            "function countEvens(items) {\n"
            "    let count = 0;\n"
            "    for (const item of items) {\n"
            "        if (item % 2 === 0) {\n"
            "            count += 1;\n"
            "        }\n"
            "    }\n"
            "    return count;\n"
            "}\n"
        ),
        description="JavaScript for-of iteration and conditional modulo testing.",
        expected_relevant_lines=[1, 2, 3, 4, 5, 8],
        expected_constructs=["functions", "loops", "conditions"],
        expected_complexity_range=(2, 3),
        expected_deterministic_output=None,
        expected_concepts=["loops", "for of", "modulo"],
        expected_findings=[],
        is_traceable=False,
    ),

    # ── 13. JavaScript: Classes and Inheritance ────────────────────────
    BenchmarkCase(
        case_id="js_classes_and_inheritance",
        name="JavaScript ES6 Class Hierarchy",
        language="javascript",
        category="classes",
        code=(
            "class Vehicle {\n"
            "    constructor(make, model) {\n"
            "        this.make = make;\n"
            "        this.model = model;\n"
            "    }\n"
            "}\n"
            "\n"
            "class Car extends Vehicle {\n"
            "    constructor(make, model, doors) {\n"
            "        super(make, model);\n"
            "        this.doors = doors;\n"
            "    }\n"
            "    describe() {\n"
            "        return `${this.make} ${this.model} with ${this.doors} doors`;\n"
            "    }\n"
            "}\n"
        ),
        description="ES6 classes with inheritance (extends), super() invocation, and methods.",
        expected_relevant_lines=[1, 2, 7, 8, 12, 13],
        expected_constructs=["classes", "functions"],
        expected_complexity_range=(1, 3),
        expected_deterministic_output=None,
        expected_concepts=["classes", "inheritance", "object-oriented programming"],
        expected_findings=[],
        is_traceable=False,
    ),

    # ── 14. JavaScript: Recursion ──────────────────────────────────────
    BenchmarkCase(
        case_id="js_recursion",
        name="JavaScript Recursive Factorial",
        language="javascript",
        category="recursion",
        code=(
            "function factorial(n) {\n"
            "    if (n <= 1) {\n"
            "        return 1;\n"
            "    }\n"
            "    return n * factorial(n - 1);\n"
            "}\n"
        ),
        description="Recursive factorial implementation in JavaScript with guard condition.",
        expected_relevant_lines=[1, 2, 3, 5],
        expected_constructs=["functions", "conditions", "calls"],
        expected_complexity_range=(2, 3),
        expected_deterministic_output=None,
        expected_concepts=["recursion", "base case", "call stack"],
        expected_findings=[],
        is_traceable=False,
    ),

    # ── 15. JavaScript: Exceptions ─────────────────────────────────────
    BenchmarkCase(
        case_id="js_exceptions",
        name="JavaScript Try-Catch JSON Parser",
        language="javascript",
        category="exceptions",
        code=(
            "function parsePayload(rawText) {\n"
            "    try {\n"
            "        return JSON.parse(rawText);\n"
            "    } catch (err) {\n"
            "        console.error(`Invalid JSON: ${err.message}`);\n"
            "        return null;\n"
            "    }\n"
            "}\n"
        ),
        description="Defensive JSON parsing with structured try/catch exception block.",
        expected_relevant_lines=[1, 2, 3, 4, 5, 6],
        expected_constructs=["functions", "calls"],
        expected_complexity_range=(1, 3),
        expected_deterministic_output=None,
        expected_concepts=["exceptions", "try catch", "error handling"],
        expected_findings=[],
        is_traceable=False,
    ),
]
