# Python Core Language Documentation
Source: Python Official Documentation (docs.python.org)
Language: python
Topic: syntax_and_semantics

## Functions and Parameter Passing
In Python, functions are defined using the `def` keyword. All arguments in Python are passed by assignment (call-by-object-reference). If a mutable object (like a list or dictionary) is passed, modifying it inside the function will affect the caller. Immutable objects (integers, strings, tuples) cannot be modified in place. Default arguments are evaluated once at function definition time; using mutable default arguments (such as `def foo(items=[])`) leads to shared state across function invocations. Use `items=None` followed by `if items is None: items = []` instead.

## Variable Scopes and LEGB Rule
Python resolves variable names using the LEGB hierarchy: Local, Enclosing (closure), Global, and Built-in scopes. Assigning to a variable inside a function makes it local to that function unless declared with `global` or `nonlocal`. If a variable is read before assignment in the same scope, Python raises `UnboundLocalError`.

## Data Structures: Lists, Tuples, Sets, and Dictionaries
Python provides built-in composite data structures:
- Lists: mutable sequences indexed by non-negative integers or negative offsets. Time complexity for append is O(1) amortized, insert/delete at arbitrary positions is O(n).
- Tuples: immutable sequences useful for fixed record structures and hashable dictionary keys.
- Sets: unordered collections of unique, hashable elements. Membership testing (`x in set`) has an average time complexity of O(1).
- Dictionaries: hash map mappings from unique hashable keys to arbitrary values. Lookup, insertion, and deletion run in average O(1) time complexity.

## Iterators and Generators
Generators are functions that yield values one at a time using the `yield` statement. They maintain internal execution state between invocations and follow the iterator protocol (`__iter__` and `__next__`). Generators provide lazy evaluation with O(1) auxiliary memory consumption regardless of the sequence size, avoiding the memory overhead of constructing full in-memory lists.

## Exception Handling
Python handles runtime errors using `try`, `except`, `else`, and `finally` blocks.
- `try`: runs the protected code block.
- `except ExceptionType as err`: catches matching exception instances. Bare `except:` is discouraged as it catches system signals like `KeyboardInterrupt`.
- `else`: executes only if no exception was raised in the `try` block.
- `finally`: executes unconditionally, guaranteeing cleanup such as closing open files or network connections.
