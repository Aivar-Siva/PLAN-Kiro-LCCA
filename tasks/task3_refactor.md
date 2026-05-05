# Task 3: Refactor + Tests

## Context
Repository: `pyjwt/` (local clone of jpadilla/pyjwt)

## Goal
Refactor `jwt/algorithms.py` to reduce duplication across algorithm classes.

## Specific requirement
The `sign()` and `verify()` methods across `HMACAlgorithm`, `RSAAlgorithm`, and `ECAlgorithm`
each implement their own `prepare_key()` validation with repeated `isinstance` checks and
error messages.

Extract a shared `_validate_key(key, allowed_types, label)` helper (module-level function or
base class method) that:
- Accepts a key, a tuple of allowed types, and a label string.
- Raises `InvalidKeyError` with a consistent message if the key is not one of the allowed types.
- Returns the key unchanged if valid.

Replace the inline validation in each algorithm class with calls to this helper.

## Files involved
- `jwt/algorithms.py` — refactor target
- `tests/test_algorithms.py` — add or update tests to cover the shared helper directly

## Acceptance criteria
1. All existing algorithm tests pass.
2. At least 3 new tests directly testing `_validate_key` (or the base method) with invalid key types.
3. No duplication of key-type error messages across algorithm classes.
