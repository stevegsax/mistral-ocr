# Development Process

> This repository follows a structured workflow. Each stage must be completed in order before moving to the next one.

## Context Switching and Blocked Tasks
- An agent should operate in only one of these contexts at a time.
- If a request is made to perform a task before its prerequisites are satisfied, mark the task as **blocked** and halt work.
- Move from one phase to another only when explicitly directed by the user.

## Steps

### 1. Requirement Analysis

- Review current requirements analysis in file `specs/01_REQUIREMENTS.md`. Create this file if it does not alrady exist. 
- Ask clarifying questions if necessary.
- Capture the desired functionality and goals.
- Document assumptions, constraints, and open questions.
- Merge requirement analysis into file `specs/01_REQUIREMENTS.md`. Create this file if it does not alrady exist.

### 2. Architectural Analysis

- Think hard about the requirement specifications, the current state of the programm, and any new pseudocode that has been created since the last architectural analysis was performed.
- Outline the high‑level architecture for the solution.
- Identify opportunities to clarify and simplify the architecture, following industry best practices.
- Ask clarifying questions if necessary.
- Identify components, data flow, and interfaces.
- Merge architecture analysis into file `specs/02_ARCHIECTURE.md`. Create this file if it does not alrady exist.
- **Always design the architecture before writing any pseudocode.**

### 3. Implementation Design and Pseudocode

- Think hard about the requirement specifications, the current state of the program, and the architectural analysis.
- Think hard about opportunities to clarify and simplify the implementation, following industry best practices.
- Ask clarifying questions if necessary.
- Write pseudocode describing the main logic without committing to exact syntax.
- Include comments discussing the intent of the program and reasons for the particular design decisions that were made. Comments should focus on what each fragment is intended to accomplish.
- Use this step to reason about potential pitfalls and edge cases.
- Merge the implementation design into file `specs/03_PSEUDOCODE.md`. Create this file if it does not alrady exist.
- **Pseudocode comes only after the architecture is defined.**

### 4. Mockup Test Case Enumeration

- Think hard about what to test in the implementation design, and how to test it.
- List everything that will be tested, starting with most basic and proceeding to most complex.
- Organize test cases in order of increasing complexity and dependency.
- Test for basic integrity first (e.g. run the `--help` command first to ensure the program can be found and starts without errors or warnings, all configuration variables are set, the configuration file can be found, log files are created where they are expected to be, the program is able to create or connect to the database, the program is able to perform queries against test data, etc).
- **Tests are enumerated only after pseudocode is complete.**

### 5. Mockup Test Design

- Think hard about the test cases enumerated in the previous step.
- Think hard about planning the tests that will verify the implementation.
- Include positive cases, failure scenarios, and edge conditions.
- Tests proceed from simplest to most complex.
- **Tests are designed only after test cases are enumerated**

### 6. Mockup Test Implementation

- Build the test code based on the enumerated test cases, using mockups for all external data sources.
- Implement tests in the order they were listed, from basic to complex.
- **Mockup tests are implemented after test cases are enumerated.**


