# Development Process

> This repository follows an iterative Test-Driven Development (TDD) workflow. The intent is to ensure high-quality, tested software through short feedback loops, continuous validation, and incremental delivery of working features.

## Core Principles

- **Test-Driven Development**: Write failing tests first, then implement to make them pass
- **Short Feedback Loops**: Validate assumptions quickly through working code
- **Continuous Integration**: Run tests on every change to maintain quality
- **Incremental Value**: Deliver working features in small, valuable chunks
- **Adaptive Planning**: Adjust course based on implementation learnings

## Feature Development Cycle

Each user story or feature follows this iterative cycle:

### 1. Feature Discovery

**Goal**: Break down requirements into small, testable increments

- Review `specs/01_REQUIREMENTS.md` to identify the next user story
- Break the story into tasks completable in 1-2 days maximum
- Define clear acceptance criteria as executable behaviors
- Propose updates to `specs/02_TODO.md` with specific, testable tasks and await User approval
- Each task should have: ID, status (NOT_STARTED/IN_PROGRESS/DONE), and description

**Quality Gate**: Story is small enough to complete in one cycle

### 2. Test-First Design

**Goal**: Define expected behavior through failing tests

- Write the simplest failing test that describes the desired behavior
- Start with basic integration tests (CLI behavior, file operations)
- Use mocks/stubs for external dependencies (Mistral API)
- Let tests drive API and interface design decisions
- Run tests to confirm they fail for the right reasons

**Quality Gate**: Tests clearly define the expected behavior and fail appropriately

### 3. Minimal Implementation

**Goal**: Make tests pass with the simplest possible code

- Write just enough code to make the failing test pass
- Focus on working software over perfect design
- Implement incrementally: CLI → core logic → external integrations
- Refactor continuously while keeping tests green
- Add error handling and edge cases as needed

**Quality Gate**: All tests pass and code meets basic quality standards

### 4. Integration & Validation

**Goal**: Ensure the feature works in the complete system

- Run full test suite: `pytest`
- Check code quality: `ruff check` and `ruff format`
- Verify type safety: `mypy src/`
- Test CLI manually for user experience
- Propose documentation updates if interfaces changed and await User approval

**Quality Gate**: All quality checks pass and feature works end-to-end

### 5. Planning Next Iteration

**Goal**: Learn and adapt for the next cycle

- Suggest marking completed tasks as DONE in `specs/02_TODO.md` and await User approval
- Propose updates to architectural docs (`specs/03_ARCHITECTURE.md`) if design evolved and await User approval
- Document any new insights or changed assumptions only after User approval
- Plan the next smallest valuable increment
- Identify dependencies or blockers for upcoming work

**Quality Gate**: Clear plan for next iteration with lessons learned captured

## Documentation Strategy

### Living Documentation
- **NEVER update specs without explicit User approval**
- Suggest spec updates to User and await their approval before making changes
- When implementation differs from specs, propose changes rather than making them
- Document design decisions and their rationale only after User approval

### Spec Files Organization
- `specs/01_REQUIREMENTS.md`: User stories and acceptance criteria
- `specs/02_TODO.md`: Current task backlog with status tracking
- `specs/03_ARCHITECTURE.md`: High-level system design (updated as it evolves)
- `specs/04_PSEUDOCODE.md`: Implementation sketches (optional, for complex algorithms)
- `specs/05_TEST_CASE_ENUMERATION.md`: Comprehensive test scenarios
- `specs/06_TEST_DESIGN.md`: Test implementation strategy
- `specs/07_TEST_IMPLEMENTATION.md`: Actual test code and results

## Context Switching Rules

- **Single Feature Focus**: Work on one user story at a time
- **Complete Cycles**: Finish the entire TDD cycle before switching features
- **Blocked Tasks**: If prerequisites are missing, mark task as blocked and work on unblocking
- **Quality Gates**: Don't proceed to next phase until current quality gate is met

## Continuous Quality Practices

### Test Automation
- Run `pytest` on every code change
- Maintain test coverage for all core functionality
- Use TDD red-green-refactor cycle religiously

### Code Quality
- Apply `ruff format` before every commit
- Fix all `ruff check` warnings
- Resolve all `mypy` type errors
- Follow project coding standards

### Integration Testing
- Test CLI commands end-to-end
- Verify file operations and database interactions
- Mock external API calls but test integration points

## Handling External Dependencies

- **Mistral API**: Mock for unit tests, use test environment for integration
- **File System**: Use temporary directories for test isolation
- **Database**: Use in-memory SQLite for fast test execution
- **Configuration**: Override with test values using environment variables

This process ensures that every feature is thoroughly tested, properly integrated, and delivers real value before moving to the next increment.