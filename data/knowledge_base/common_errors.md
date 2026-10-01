# Common Programming Errors and Debugging Patterns
Source: Software Engineering Debugging Standards & Language References
Language: general
Topic: common_errors

## Off-by-One Errors and Boundary Conditions
An off-by-one error (OBOE) occurs when an iterative loop iterates one time too few or one time too many. Common causes include:
- Confusing `<` with `<=` when indexing 0-indexed arrays of length n. Valid indices range from 0 to n-1; accessing index n causes `IndexError` in Python or evaluates to `undefined` in JavaScript.
- Slicing boundaries: Python's slice syntax `array[start:end]` includes `start` but excludes `end` (half-open interval `[start, end)`).

## Null and Undefined Dereferencing
Attempting to access properties or call methods on null or uninitialized values results in catastrophic runtime failure:
- Python: `AttributeError: 'NoneType' object has no attribute 'x'` or `TypeError: 'NoneType' object is not subscriptable`. Remediate by validating `if obj is not None:` or returning explicit default values.
- JavaScript: `TypeError: Cannot read properties of undefined (reading 'x')`. Remediate using optional chaining `obj?.property` and nullish coalescing `val ?? defaultVal`.

## Mutable Default Arguments Pitfall (Python)
In Python, default parameter expressions are evaluated once when the function definition is executed, not each time the function is called.
- Bug: `def append_to(element, target_list=[]): target_list.append(element); return target_list`
- Result: Every call without a second argument modifies the same persistent list instance in memory.
- Fix: Set default to `None` and instantiate a fresh list inside the function body.

## Floating-Point Arithmetic and Precision Issues
Standard binary floating-point representation (IEEE 754) cannot precisely represent all base-10 fractions (e.g. `0.1 + 0.2 === 0.30000000000000004`).
- Direct equality comparison (`a == b`) fails on calculated floats.
- Remediate by checking difference against an epsilon tolerance: `abs(a - b) < 1e-9` or using exact decimal packages (`decimal.Decimal` in Python).
