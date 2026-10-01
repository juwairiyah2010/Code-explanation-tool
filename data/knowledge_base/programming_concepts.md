# Fundamental Programming Concepts
Source: MIT OpenCourseWare & CS Curricula Reference
Language: general
Topic: programming_concepts

## Recursion and Base Cases
Recursion is a programming technique where a function calls itself directly or indirectly to solve smaller instances of the same problem. Every recursive implementation requires:
1. Base Case: a termination condition that returns a direct result without recursive invocation, preventing infinite recursion and call stack exhaustion.
2. Recursive Step: reducing the input toward the base case with each step.
Recursion consumes call stack frames proportional to recursion depth (O(depth) memory), which can lead to stack overflow if not properly bounded or optimized via tail-call elimination.

## Pure Functions and Immutability
A pure function is a function where:
1. The return value is identical for identical arguments (deterministic, referential transparency).
2. The function generates no side effects (does not alter external mutable state, perform network I/O, or modify arguments).
Immutability prevents race conditions in concurrent contexts, simplifies debugging, and allows predictive state management.

## Separation of Concerns and Modular Architecture
Separation of concerns (SoC) is a software design principle that partitions a program into distinct sections, where each section addresses a separate responsibility:
- Routing / Presentation: receives input and validates client payloads.
- Business Logic / Services: orchestrates core domain algorithms independently of transport or UI.
- Data Persistence / Repositories: manages database transactions and queries.
This decoupling ensures individual layers can be tested, refactored, and maintained in isolation.
