# JavaScript Core Language Documentation
Source: MDN Web Docs (developer.mozilla.org)
Language: javascript
Topic: syntax_and_semantics

## Closures and Lexical Scoping
A closure is the combination of a function bundled together with references to its surrounding state (the lexical environment). In JavaScript, closures are created every time a function is created at function creation time. A closure allows an inner function to access an outer function's scope even after the outer function has finished executing. Common applications include data encapsulation, private state emulation, currying, and memoization.

## Asynchronous JavaScript: Event Loop, Promises, and Async/Await
JavaScript is single-threaded with an event-driven concurrency model based on an event loop:
- Call Stack: tracks executing function frames synchronously.
- Web APIs / Node APIs: handle background operations (timers, I/O, network requests).
- Task / Microtask Queues: Promises execute via the microtask queue, which has higher priority than the macrotask queue (`setTimeout`, `setInterval`).
- Promises: represent the eventual completion or failure of an asynchronous operation with three states: pending, fulfilled, rejected.
- `async/await`: syntactic sugar over Promises, enabling sequential error-handled code with standard `try/catch` syntax.

## Variable Declarations: var, let, and const
- `var`: function-scoped or globally-scoped, hoisted to the top of its scope and initialized with `undefined`. Does not respect block boundaries.
- `let`: block-scoped, hoisted but kept in a Temporal Dead Zone (TDZ) until evaluation. Reassignment is permitted.
- `const`: block-scoped, hoisted within TDZ, prevents reassignment to the binding itself (though contents of mutable objects and arrays bound by const can still be modified).

## Debouncing and Throttling
Debouncing and throttling are performance optimization patterns for high-frequency events (scroll, resize, keydown):
- Debounce: delays execution of the target function until a specified period of inactivity has elapsed. If the event fires again before the timer expires, the previous timer is canceled and reset.
- Throttle: guarantees that the target function executes at most once per specified time interval, smoothing out continuous event streams.

## Array Methods: Functional Transformations
JavaScript arrays provide higher-order methods:
- `map`: transforms each element into a new element without mutating the original array, returning a new array of identical length.
- `filter`: returns a subset array containing elements that satisfy the truthy predicate.
- `reduce`: accumulates array elements into a single derived value (object, sum, grouped dictionary) by applying a reducer callback iteratively.
