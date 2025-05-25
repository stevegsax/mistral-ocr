# Development Process

This repository follows a structured workflow. Each stage must be completed in order before moving to the next one.

## 1. Requirement Analysis
- Capture the desired functionality and goals.
- Document assumptions, constraints, and open questions.

## 2. Architectural Analysis
- Outline the high‑level architecture for the solution.
- Identify components, data flow, and interfaces.
- **Always design the architecture before writing any pseudocode.**

## 3. First Pass Implementation Design
- Write pseudocode describing the main logic without committing to exact syntax.
- Use this step to reason about potential pitfalls and edge cases.
- **Pseudocode comes only after the architecture is defined.**

## 4. Test Design
- Plan the tests that will verify the implementation.
- Include positive cases, failure scenarios, and edge conditions.
- **Tests are designed after pseudocode is complete.**

## 5. Implementation
- Convert the pseudocode into working code.
- Refine the solution until all tests pass.
- **Implementation starts only once the tests are planned.**

## Context Switching and Blocked Tasks
- An agent should operate in only one of these contexts at a time.
- If a request is made to perform a task before its prerequisites are satisfied, mark the task as **blocked** and halt work.
- Move from one phase to another only when explicitly directed by the user.

