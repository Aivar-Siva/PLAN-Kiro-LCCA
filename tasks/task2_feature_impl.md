# Task 2: Feature Implementation

## Context
Repository: `pyjwt/` (local clone of jpadilla/pyjwt)

## Feature spec
Add strict `iss` (issuer) claim presence enforcement.

Currently, `options["require"]` can include `"iss"` to require the claim be present.
The existing behaviour raises `MissingRequiredClaimError` if `iss` is in `options["require"]`
but absent from the token. This already works.

**New behaviour required:**
Add a new option `options["strict_iss"]` (boolean, default `False`).
When `strict_iss=True` and `issuer` is passed to `decode()`:
- If the `iss` claim is **missing** from the token payload, raise `MissingRequiredClaimError("iss")`.
- If the `iss` claim is **present but does not match** `issuer`, raise `InvalidIssuerError`.
- If `strict_iss=False` (default), behaviour is unchanged from current.

## Files likely involved
- `jwt/api_jwt.py` — claim validation logic
- `tests/test_api_jwt.py` — add tests for the new option

## Acceptance criteria
1. New tests covering `strict_iss=True` with missing `iss`, mismatched `iss`, and matching `iss`.
2. All existing tests continue to pass.
