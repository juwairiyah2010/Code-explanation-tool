"""Deterministic code sample fixtures for unit and integration testing.

Contains small, focused Python and JavaScript programs covering:
- Standard constructs (functions, classes, loops, conditionals)
- Edge cases: empty code, syntax errors, very long code, nested functions, recursion, loops, exceptions
- Malformed LLM response structures
- Irrelevant RAG queries
"""

# 1. Standard Samples
PYTHON_BASIC_MATH = """def add_numbers(a: int, b: int) -> int:
    \"\"\"Add two numbers and return the result.\"\"\"
    result = a + b
    return result

total = add_numbers(5, 7)
print(f"Total: {total}")
"""

JAVASCRIPT_BASIC_MATH = """function addNumbers(a, b) {
    // Add two numbers and return the sum
    const result = a + b;
    return result;
}

const total = addNumbers(5, 7);
console.log(`Total: ${total}`);
"""

# 2. Edge Case: Empty Code & Whitespace
PYTHON_EMPTY = ""
PYTHON_WHITESPACE = "    \n\t   \n"
JAVASCRIPT_EMPTY = ""
JAVASCRIPT_WHITESPACE = "   \n\n  "

# 3. Edge Case: Syntax Errors
PYTHON_SYNTAX_ERROR = """def broken_function(x, y
    print("Missing closing parenthesis and colon")
"""

JAVASCRIPT_SYNTAX_ERROR = """function brokenFunction(x, y {
    console.log("Missing parameter closing parenthesis");
"""

# 4. Edge Case: Very Long Code (> 150 lines)
PYTHON_VERY_LONG = "\n".join([f"var_{i} = {i} * 2" for i in range(160)]) + "\nresult = sum([var_0, var_1, var_2])\n"

JAVASCRIPT_VERY_LONG = "\n".join([f"const var_{i} = {i} * 2;" for i in range(160)]) + "\nconst result = var_0 + var_1;\n"

# 5. Edge Case: Nested Functions & Closures
PYTHON_NESTED_FUNCTIONS = """def make_multiplier(factor: int):
    \"\"\"Outer enclosing function establishing scope.\"\"\"
    def multiply(value: int) -> int:
        \"\"\"Inner closure function accessing factor.\"\"\"
        return value * factor
    return multiply

double = make_multiplier(2)
output = double(10)
print(output)
"""

JAVASCRIPT_NESTED_FUNCTIONS = """function makeMultiplier(factor) {
    // Outer function establishing closure scope
    function multiply(value) {
        // Inner function using factor
        return value * factor;
    }
    return multiply;
}

const double = makeMultiplier(2);
const output = double(10);
"""

# 6. Edge Case: Recursion
PYTHON_RECURSION = """def factorial(n: int) -> int:
    \"\"\"Compute factorial recursively with base case.\"\"\"
    if n <= 1:
        return 1
    return n * factorial(n - 1)

fact_val = factorial(4)
print(f"Factorial 4 is {fact_val}")
"""

JAVASCRIPT_RECURSION = """function factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

const factVal = factorial(4);
"""

# 7. Edge Case: Loops (For, While, Nested)
PYTHON_LOOPS = """total = 0
matrix = [[1, 2], [3, 4]]
for row in matrix:
    for item in row:
        total += item

counter = 0
while counter < 3:
    counter += 1
"""

JAVASCRIPT_LOOPS = """let total = 0;
const matrix = [[1, 2], [3, 4]];
for (const row of matrix) {
    for (const item of row) {
        total += item;
    }
}

let counter = 0;
while (counter < 3) {
    counter++;
}
"""

# 8. Edge Case: Exceptions
PYTHON_ZERO_DIVISION = """x = 10
y = 0
result = x / y
"""

PYTHON_INDEX_ERROR = """items = [1, 2, 3]
invalid_item = items[10]
"""

PYTHON_CUSTOM_EXCEPTION = """class InvalidAgeError(Exception):
    pass

def verify_age(age: int):
    if age < 0:
        raise InvalidAgeError("Age cannot be negative")

verify_age(-5)
"""

# 9. Edge Case: Malformed LLM Responses
MALFORMED_LLM_NOT_JSON = "Here is your explanation: this code is very nice."
MALFORMED_LLM_MISSING_FIELDS = '{"summary": "A code snippet."}'
MALFORMED_LLM_INVALID_LINES = """{
  "summary": "Loops over a list.",
  "complexity": {"time": "O(N)", "space": "O(1)"},
  "line_explanations": [
    {"line": 999, "explanation": "This line does not exist in code."}
  ],
  "hints": [],
  "key_takeaways": []
}"""

# 10. Edge Case: Irrelevant RAG Queries
IRRELEVANT_RAG_QUERIES = [
    "how to bake sourdough bread with active starter",
    "distance from Earth to Andromeda galaxy in light years",
    "recipe for spicy chicken curry with garam masala",
    "history of the Roman Empire from Julius Caesar",
]
