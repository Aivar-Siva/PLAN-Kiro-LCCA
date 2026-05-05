# Evaluation Guide

## Prerequisites

```bash
# Clone the repo
git clone <repo-url>
cd PLAN-Kiro-LCCA

# Init pyjwt submodule
git submodule update --init

# Create venv and install dependencies
python3 -m venv .venv
.venv/bin/pip install -e "pyjwt[crypto]" pytest -q
```

## Agents

| Agent | Description |
|---|---|
| `baseline-coding-agent` | Built-in tools only (`fs_read`, `grep`, `glob`, `fs_write`, `execute_bash`) |
| `lcca-coding-agent` | MCP small-model tools (`read_or_summarize`, `smart_grep`, `analyze_error`) |

## Launch

**With MCP (LCCA agent):**
```bash
kiro-cli chat --agent lcca-coding-agent
```

**Without MCP (baseline):**
```bash
kiro-cli chat --agent baseline-coding-agent
# or just
kiro-cli chat
```

## Before Each Run

Reset pyjwt to the buggy evaluation state:
```bash
cd pyjwt && git checkout -- . && cd ..
rm -f lcca-metrics.jsonl
```

Verify bug is active:
```bash
.venv/bin/pytest pyjwt/tests/test_api_jwt.py -x -q 2>&1 | tail -3
# Expected: 1 failed (test_encode_datetime)
```

## Metrics

Note your Kiro credit balance before and after each task.

For LCCA runs, view small-model token usage after all tasks:
```bash
cat lcca-metrics.jsonl | python3 -c "
import sys, json
records = [json.loads(l) for l in sys.stdin]
for r in records:
    print(f\"{r['timestamp'][:19]}  {r['tool']:<25} {r['mode']:<12} in={r['prompt_tokens']} out={r['completion_tokens']}\")
print(f'\nTotal small model: in={sum(r[\"prompt_tokens\"] for r in records)} out={sum(r[\"completion_tokens\"] for r in records)}')
"
```

---

## Task 1 — Bug Fix

Paste into Kiro chat:

```
I have a bug in the pyjwt codebase at <absolute-path>/pyjwt.

Run the tests first:
cd <absolute-path>/pyjwt && <absolute-path>/.venv/bin/pytest tests/ -x -q 2>&1 | tee <absolute-path>/test-output-task1.log

Then find and fix the bug. All tests must pass after your fix.
```

**Acceptance:** All 344 tests pass.

---

## Task 2 — Feature Implementation

Paste into Kiro chat:

```
In the pyjwt codebase at <absolute-path>/pyjwt, implement the following feature:

Add a new option `options["strict_iss"]` (boolean, default False).
When strict_iss=True and issuer is passed to decode():
- If the iss claim is missing from the token payload, raise MissingRequiredClaimError("iss")
- If the iss claim is present but does not match issuer, raise InvalidIssuerError
- If strict_iss=False (default), behaviour is unchanged

Files to modify:
- jwt/api_jwt.py — add the validation logic
- tests/test_api_jwt.py — add tests for the new option (missing iss, mismatched iss, matching iss)

All existing tests must still pass.
Run tests with: <absolute-path>/.venv/bin/pytest pyjwt/tests/test_api_jwt.py -q
```

**Acceptance:** All existing tests pass + 3 new tests added.

---

## Task 3 — Refactor + Tests

Paste into Kiro chat:

```
In the pyjwt codebase at <absolute-path>/pyjwt, refactor jwt/algorithms.py:

Extract a shared helper `_validate_key(key, allowed_types, label)` (module-level function) that:
- Accepts a key, a tuple of allowed types, and a label string
- Raises InvalidKeyError with a consistent message if key is not one of the allowed types
- Returns the key unchanged if valid

Replace the inline key-type validation in HMACAlgorithm, RSAAlgorithm, and ECAlgorithm with calls to this helper.

Then in tests/test_algorithms.py, add at least 3 tests that directly test _validate_key with invalid key types.

All existing tests must still pass.
Run tests with: <absolute-path>/.venv/bin/pytest pyjwt/tests/test_algorithms.py -q
```

**Acceptance:** All existing tests pass + 3+ new tests for `_validate_key`.

---

## Results Table

| Task | Baseline credits | LCCA credits | LCCA small model tokens (in/out) | Success |
|---|---|---|---|---|
| Task 1 — Bug fix | | | | |
| Task 2 — Feature impl | | | | |
| Task 3 — Refactor | | | | |
| **Total** | | | | |
