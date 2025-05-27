# Development Process

> This repository follows a structured workflow. Each stage must be completed in order before moving to the next one. The intent is to ensure that all requirements are reflected in the architecture, that comprehensive tests are created, and that the final product accurately represents the design.

## Context Switching and Blocked Tasks

- An agent should operate in only one of these contexts at a time.
- If a request is made to perform a task before its prerequisites are satisfied, mark the task as **blocked** and halt work.
- Move from one phase to another only when explicitly directed by the user.

## Steps

### 1. Requirement Analysis

- Review current requirements analysis in file `specs/01_REQUIREMENTS.md`. Create this file if it does not already exist. 
- Ask clarifying questions if necessary.
- Capture the desired functionality and goals.
- Document assumptions, constraints, and open questions.

### 2. Update the TODO List

- Carefully review the current requirements and the set of tasks defined in 'specs/02_TODO.md'. Create this file if it does not already exist.
- Enumerate the tasks required to build the featues described in the product document.
    - Each task should be numbered (zero padded to three digits), have a completion checkbox, a status value, and a description. Statuses will be one of "NOT_STARTED", "MOCKUP", "ERROR", "DONE" as described below.
        - For example: `023. - [ ] NOT_STARTED Logging output should be saved to XDG_STATUS_DIR`. 
- List everything that will be built, starting with most basic and proceeding to most complex.
- Based on the current status of the program and tests, mark each requirement as:
    - "NOT_STARTED" if this feature 
    - "MOCKUP" if this feature has only been designed to the mockup test stage.
    - "ERROR" if the feature has tests but the tests fail.
    - "DONE" if this feature has been fully implemented and all tests pass.
- Merge requirement analysis into file `specs/01_REQUIREMENTS.md`. Create this file if it does not already exist.

### 3. Architectural Analysis

- Think hard about the requirement specifications, the current state of the programm, and any new pseudocode that has been created since the last architectural analysis was performed.
- Outline the high‑level architecture for the solution.
- Identify opportunities to clarify and simplify the architecture, following industry best practices.
- Ask clarifying questions if necessary.
- Identify components, data flow, and interfaces.
- Merge architecture analysis into file `specs/03_ARCHIECTURE.md`. Create this file if it does not already exist.
- **Always design the architecture before writing any pseudocode.**

### 4. Implementation Design and Pseudocode

- Think hard about the requirement specifications, the current state of the program, and the architectural analysis.
- Think hard about opportunities to clarify and simplify the implementation, following industry best practices.
- Ask clarifying questions if necessary.
- Write pseudocode describing the main logic without committing to exact syntax.
- Include comments discussing the intent of the program and reasons for the particular design decisions that were made. Comments should focus on what each fragment is intended to accomplish.
- Use this step to reason about potential pitfalls and edge cases.
- Merge the implementation design into file `specs/04_PSEUDOCODE.md`. Create this file if it does not already exist.
- **Pseudocode comes only after the architecture is defined.**

### 5. Test Case Enumeration

- Think hard about what to test in the implementation design, and how to test it.
- List everything should be tested in order to ensure implementation correctness, starting with most basic and proceeding to most complex.
- Organize test cases in order of increasing complexity and dependency.
- Test for basic integrity first (e.g. run the `--help` command first to ensure the program can be found and starts without errors or warnings, all configuration variables are set, the configuration file can be found, log files are created where they are expected to be, the program is able to create or connect to the database, the program is able to perform queries against test data, etc).
- Merge the enumerated tests into file `specs/05_TEST_CASE_ENUMERATION.md`. Create this file if it does not already exist.
- **Tests are enumerated only after pseudocode is complete.**

### 6. Design Tests 

- Think hard about the test cases enumerated in the previous step.
- Think hard about planning the tests that will verify the implementation.
- Include positive cases, failure scenarios, and edge conditions.
- Tests proceed from simplest to most complex.
- Design mockup fixtures to stand in for any remote resources (for example: remote APIs). Database operations should not be mocked up. 
- Merge the test design into file `specs/06_TEST_DESIGN.md`. Create this file if it does not already exist. Note which tests use mockups and which are fully implemented.
- **Tests are designed only after test cases are enumerated**

### 6. Mockup Test Implementation

- Build the test code based on the enumerated test cases, using mockups for all external data sources.
- Implement tests in the order they were listed, from basic to complex.
- Merge the test into file `specs/07_TEST_IMPLEMENTATION.md`. Create this file if it does not already exist. Note which tests use mockups and which are fully implemented.
- **Mockup tests are implemented after test cases are enumerated.**


