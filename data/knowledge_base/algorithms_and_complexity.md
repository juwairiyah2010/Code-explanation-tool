# Algorithms and Time/Space Complexity (Big-O)
Source: Introduction to Algorithms & Algorithm Design Manual
Language: general
Topic: time_complexity

## Big-O Asymptotic Analysis Overview
Big-O notation describes the upper bound of an algorithm's runtime growth or memory consumption as the input size n approaches infinity, abstracting away hardware constants.
- O(1) Constant: Execution time is invariant with respect to input size (e.g. hash map lookup, array direct indexing).
- O(log n) Logarithmic: Input size is halved at each step (e.g. binary search on sorted sequences, balanced binary search tree lookups).
- O(n) Linear: Execution time grows directly proportional to input size (e.g. single loop traversal, linear search).
- O(n log n) Linearithmic: Optimal comparison-based sorting (e.g. Merge Sort, QuickSort average case, TimSort in Python).
- O(n^2) Quadratic: Processing all pairs in an input collection (e.g. nested loops, Bubble Sort, naive matrix multiplication).
- O(2^n) Exponential: Doubling computation with each added input element (e.g. naive recursive Fibonacci, generating all subsets / power set).

## Space Complexity: Auxiliary vs Total Space
Space complexity measures the peak working memory utilized by an algorithm:
- Total Space: Includes memory required to store the initial inputs plus any additional working storage.
- Auxiliary Space: Only measures additional or temporary memory created by the algorithm during execution.
- Call Stack Overhead: Recursive algorithms allocate a stack frame for every active recursion level. An algorithm making n nested calls consumes at least O(n) auxiliary stack space, even if no explicit variables are allocated.
