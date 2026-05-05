# Task 1: Bug Fix

## Context
Repository: `pyjwt/` (local clone of jpadilla/pyjwt)

## Problem
A bug has been introduced in the JWT decoding logic. Running the test suite reveals failures.

## Steps to reproduce
```bash
cd pyjwt
../.venv/bin/pytest tests/ -x -q 2>&1 | tee ../test-output-task1.log
```

## Acceptance criteria
All tests in `tests/` pass after your fix.

## Notes
- Start by running the tests and reading the error log.
- Use the error output to identify the failing test and suspected file.
- Read only the relevant source file(s) — do not read the entire codebase.
