# Plan: Kiro-Integrated Context-Optimized Coding Agent (MCP Small-Model Tools)

## 1. Problem Statement (Kiro Variant)

Coding agents on real codebases quickly fill their context windows when they read whole files, stream full test logs, or inspect long stack traces. In a Kiro CLI setup, the built-in tools like `read`, `grep`, `glob`, `write`, `shell`, and `code` make it easy for the agent to pull large amounts of content into the conversation, but every unfiltered tool result directly increases the large model's context and cost.[cite:27][cite:1]

**Goal (Kiro-centric):**
Build a **Kiro CLI custom agent** on Linux where:
- Kiro's agent (Auto or a configured large model) is the **primary reasoning engine** and orchestrator.[cite:2]
- A separate **MCP server**, running locally, exposes **small-model compression tools only** (no planner inside MCP).[cite:3]
- Kiro's agent uses those MCP tools for context-intensive I/O (file contents, logs, search results), so that the main context stays lean and cheap while preserving or improving task success.
- We compare this **Kiro+MCP small-model setup** against a **baseline Kiro agent** that uses only built-in tools (no compression MCP), on the same tasks, measuring:
  - Task success rate.
  - Large-model context token usage.
  - Cost per task.

This directly aligns with the assignment constraints: large model as primary agent, small model invoked as a tool, multi-file codebases, and measured impact vs. a single-model baseline.[cite:27]


## 2. High-Level Architecture

### 2.1 Actors

- **Kiro CLI Agent (Large Model):**
  - Runs on Linux via `kiro-cli chat`.
  - Configured as a custom agent that:
    - Has access to built-in tools (`read`, `grep`, `glob`, `write`, `shell`, `code`, etc.).[cite:1]
    - Has access to one local **MCP server**: `lcca-context-tools`.
  - Acts as the **only planner and conversation owner**.

- **MCP Server `lcca-context-tools` (Small Model Tools):**
  - Headless Python service, started by Kiro via `mcp.json` or `kiro-cli mcp add`.
  - Uses Groq small model (e.g., `llama-3.1-8b-instant`) for compression and extraction.
  - Exposes a small set of tools only for **reading and compressing large artifacts**.
  - Does **not** talk directly to the user or make high-level decisions.

- **Codebase + Environment:**
  - Linux development environment where Kiro CLI is installed.[cite:2]
  - Git repository with multiple directories/files.
  - Tests runnable via Kiro tools (`shell`, `code`, or project-specific scripts).


### 2.2 Data Flow Overview

1. **User** describes a SWE task in Kiro CLI (`kiro-cli chat`).
2. **Kiro agent** plans and decides which tools to call.
3. For **small or simple operations**, Kiro uses built-in tools directly:
   - `grep` / `glob` / `code` / `read` when results are expected to be small.[cite:1]
4. For **potentially large artifacts** (full file contents, long logs, large search results), Kiro calls MCP tools from `lcca-context-tools` instead of raw `read`/`shell` output:
   - Example: `@lcca-context-tools/summarize_artifact` on a file path.
5. **MCP server** reads raw content from disk or command output, uses the small model to compress it according to a guideline, returns a structured summary.
6. **Kiro agent** reasons over the summary (plus any small raw snippets) and decides edits / next actions using built-in `write`, `shell`, etc.
7. For evaluation, we run the same tasks in two modes:
   - **Baseline Kiro:** built-in tools only, no `@lcca-context-tools/*` tools.
   - **LCCA Kiro:** built-in tools + MCP compression tools.

Kiro stays the main agent; the MCP server is purely context-management capability.


## 3. Kiro CLI Configuration

### 3.1 MCP Server Registration (Linux)

We register the MCP server either via command line:

```bash
kiro-cli mcp add \
  --name "lcca-context-tools" \
  --scope global \
  --command "uvx" \
  --args "lcca-context-tools@latest"
```

or via `~/.kiro/settings/mcp.json` (user-level) or `<project-root>/.kiro/settings/mcp.json` (workspace-level):[cite:3]

```json
{
  "mcpServers": {
    "lcca-context-tools": {
      "command": "uvx",
      "args": ["lcca-context-tools@latest"],
      "env": {
        "LCCA_CONFIG_PATH": "./lcca-config.yaml"
      },
      "disabled": false
    }
  }
}
```

The MCP server itself is our Python package / entry-point that exposes the tools listed in Section 4.

### 3.2 Agent Configuration with MCP

We create a Kiro custom agent configuration (e.g., `.kiro/settings/agents/lcca-agent.json`) that:

- Uses Auto or a specific large model.
- Includes `lcca-context-tools` in its `mcpServers` section.
- Optionally restricts or pre-approves built-in tools and MCP tools via `allowedTools` and `toolsSettings`.[cite:2][cite:1][cite:3]

Example (schematic):

```json
{
  "name": "lcca-coding-agent",
  "description": "Kiro coding agent using small-model MCP for context compression",
  "mcpServers": {
    "lcca-context-tools": {
      "command": "uvx",
      "args": ["lcca-context-tools@latest"]
    }
  },
  "includeMcpJson": true,
  "allowedTools": [
    "read", "grep", "glob", "write", "shell", "code",
    "@lcca-context-tools/summarize_artifact",
    "@lcca-context-tools/analyze_error",
    "@lcca-context-tools/triage_matches"
  ],
  "toolsSettings": {
    "grep": {
      "allowedPaths": ["./src/**"],
      "allowReadOnly": true
    },
    "read": {
      "allowedPaths": ["./src/**"]
    }
  }
}
```

Final JSON structure will be kept consistent with Kiro docs but refined during implementation.


## 4. MCP Server Design (`lcca-context-tools`)

### 4.1 Responsibilities

The MCP server is responsible for:

- Reading **large artifacts** off-disk or from command outputs.
- Using a **small LLM** to generate bounded summaries / analyses.
- Returning **structured responses** that Kiro's large model can reason over.
- Staying **stateless per call** (no REPL, no user prompts).

It does **not**:

- Plan multi-step workflows.
- Apply file edits or run tests.
- Interact directly with users.


### 4.2 Exposed Tools (Final Set)

1. `read_or_summarize`
   - Purpose: Replace built-in `read` with intelligent routing — return raw content for small files, compressed summary for large files.
   - Parameters (MCP tool schema):
     - `path: string` – file path to read.
     - `task_query: string` – current task/bug/feature description.
     - `threshold_lines: integer` (optional, default 200) – files under this are returned raw.
     - `max_summary_tokens: integer` (optional, default 800) – target tokens for summary.
   - Behavior:
     - Reads the file content on disk.
     - If line count < `threshold_lines`: return raw content.
     - Else: call small model with compression guideline:
       - Keep relevant function/class signatures, failing tests, key control flow.
       - Drop comments, docstrings, and repetitive lines unless tied to `task_query`.
     - Returns structured JSON:
       ```json
       {
         "content": "...",  // raw or summary
         "mode": "raw" | "summarized",
         "key_symbols": ["ClassName.method", "function foo"],  // only if summarized
         "original_lines": 450  // only if summarized
       }
       ```

2. `analyze_error`
   - Purpose: Compress long test output or stack traces into root-cause hypotheses.
   - Parameters:
     - `path: string` – path to a log / test output file.
     - `task_query: string`.
     - `max_tokens: integer` (optional, default 800).
   - Behavior:
     - Reads log file, calls small model to extract:
       - Failing test names.
       - Important stack frames.
       - Likely root causes and relevant modules.
     - Returns JSON:
       ```json
       {
         "summary": "...",
         "failing_tests": ["test_foo", "test_bar"],
         "suspected_files": ["src/foo.py"],
         "key_errors": ["AssertionError: expected X got Y"]
       }
       ```

3. `smart_grep`
   - Purpose: Run grep internally and return only top-ranked matches, preventing raw flood from entering Kiro's context.
   - Parameters:
     - `pattern: string` – regex pattern to search.
     - `path: string` – directory or file path to search.
     - `task_query: string` – current task context for relevance ranking.
     - `max_results: integer` (optional, default 10) – number of top matches to return.
   - Behavior:
     - Runs grep internally (via subprocess or file scan).
     - If total matches <= `max_results`: return all raw.
     - Else: call small model to rank matches by relevance to `task_query`, return top N.
     - Returns JSON:
       ```json
       {
         "top_matches": [
           {"file": "jwt/api_jwt.py", "line": 45, "snippet": "def decode(...)"},
           ...
         ],
         "summary": "Found 87 matches, top 10 are in jwt/api_jwt.py and jwt/algorithms.py related to decoding logic",
         "total_found": 87
       }
       ```

**Design rationale:**
- `read_or_summarize` replaces built-in `read` entirely, eliminating agent choice and prompt-steering risk.
- `smart_grep` solves the bootstrapping problem — raw grep results never enter Kiro's context.
- All tools use the same small model and return structured JSON for consistent parsing.


### 4.3 Small Model Usage

- **Small model:** `us.meta.llama3-2-3b-instruct-v1:0` via AWS Bedrock proxy.
- **Endpoint:** `https://ug36pewdpyfaepokw55klfit7y0ltgbn.lambda-url.us-west-2.on.aws/`
- **Payload format:**
  ```json
  {
    "model_id": "us.meta.llama3-2-3b-instruct-v1:0",
    "messages": [{"role": "user", "content": "..."}],
    "max_tokens": 800
  }
  ```
- Central configuration file (`lcca-config.yaml` or env vars) holds:
  - `LCCA_MODEL_ID` – small model ID.
  - `LCCA_LAMBDA_URL` – proxy endpoint.
  - Per-tool `max_tokens` limits.
- Each MCP request:
  - Validates parameters.
  - Reads artifacts.
  - Calls small model via HTTP POST to Lambda URL.
  - Logs `usage` from response (prompt_tokens, completion_tokens) to a JSON log file.
  - Returns structured JSON.


## 5. How Kiro Agent Uses MCP Tools

### 5.1 Tool Selection Strategy

The agent is configured with `read` removed from `allowedTools`, forcing use of MCP tools for all file and search operations:

- Use built-in `glob` and `code` for **discovering** files and symbols (output is always small).
- Use `@lcca-context-tools/read_or_summarize` instead of built-in `read` for all file content.
- Use `@lcca-context-tools/smart_grep` instead of built-in `grep` for all pattern searches.
- Use `@lcca-context-tools/analyze_error` when test output or logs need to be inspected.
- Use built-in `write` and `shell` for applying edits and running tests (output is controlled).

This is enforced structurally via `allowedTools` — no prompt steering required for the core I/O tools.


### 5.2 No Second Planner

We explicitly **do not** implement a second ReAct planner inside the MCP server:

- Kiro's agent is the only planner.[cite:2]
- MCP server is pure tools (stateless, one request → one response).
- This avoids conflicts between two planning loops and keeps the architecture aligned with Kiro’s design: MCP servers as specialized external capabilities.[cite:3]


## 6. Baseline vs LCCA Modes

### 6.1 Baseline Kiro Agent

- Same Kiro custom agent (or a copy) but **without** `lcca-context-tools` configured:
  - `mcpServers` section empty or `includeMcpJson: false` with no `lcca-context-tools`.
  - `allowedTools` includes built-ins only.
- The agent uses built-in `read`, `grep`, `glob`, `write`, and `shell` directly.[cite:1]

### 6.2 LCCA Kiro Agent

- Identical to baseline, but with:
  - MCP server `lcca-context-tools` configured.
  - MCP tools listed in `allowedTools`.
  - Additional prompt instructions about using MCP tools for large outputs.

### 6.3 Evaluation Tasks

Target repository: **`jpadilla/pyjwt`** (cloned locally).

1. **Bug fix:** Introduce a subtle bug in `jwt/api_jwt.py` (e.g., wrong exception type on expiry, or missing claim validation). Agent must find and fix it using a failing test as the entry point.
2. **Feature implementation:** Add strict `iss` (issuer) claim validation — when `options["require_iss"]` is set, raise `InvalidIssuerError` if `iss` is missing (not just mismatched). Spec provided as text.
3. **Refactor + tests:** Refactor `jwt/algorithms.py` (large file, multiple algorithm classes) to extract a shared base class, and update/add tests in `tests/test_algorithms.py`.

Each task:
- Touches multiple files.
- Requires reading non-trivial code or logs.
- Has a clear pass/fail criterion (tests pass).


## 7. Measurement and Instrumentation

### 7.1 Metrics

For each task and mode (baseline vs LCCA):

- `success`: boolean (did the final code pass tests / meet acceptance criteria?).
- `turns`: number of agent turns until done.
- `large_model_tokens`: input/output tokens consumed by Kiro's large model (from provider usage / Kiro logs, where available).[cite:2]
- `small_model_tokens`: input/output tokens in MCP server (we log Groq usage per small-model call).
- `total_cost_usd`: estimated from provider pricing and logged tokens.

### 7.2 Instrumentation Approach

- **MCP side (small model) — precise:**
  - Log each request to `lcca-metrics.jsonl`:
    ```json
    {"task": "bug_fix", "tool": "read_or_summarize", "mode": "summarized", "prompt_tokens": 1200, "completion_tokens": 180, "timestamp": "..."}
    ```
  - Token counts come directly from the Lambda response `usage` field.

- **Kiro side (large model) — cost-derived:**
  - Record Kiro credit balance before and after each task run via `kiro-cli usage`.
  - Credit delta gives cost per task; convert to approximate tokens using provider pricing.
  - Save full session transcript per task for post-hoc token estimation with `tiktoken` if needed.

- **Comparison report:**
  - Aggregate `lcca-metrics.jsonl` per task.
  - Compute: baseline cost delta vs LCCA cost delta (large model) + LCCA small model cost.
  - Net saving = baseline large model cost − (LCCA large model cost + LCCA small model cost).


## 8. Implementation Plan (Order)

1. **MCP server skeleton:**
   - Set up Python project `lcca-context-tools` with a minimal MCP server exposing a dummy tool.
   - Integrate Bedrock proxy HTTP client and config (`LCCA_MODEL_ID`, `LCCA_LAMBDA_URL`).

2. **Implement `read_or_summarize`:**
   - Read file, branch on line count, call small model if large, return structured JSON.
   - Add basic tests with synthetic files (small and large).

3. **Implement `analyze_error`:**
   - Read log file, call small model, return structured JSON with failing tests and suspected files.

4. **Implement `smart_grep`:**
   - Run grep via subprocess, branch on result count, call small model to rank if large, return top matches.

5. **Add metrics logging:**
   - Per-call append to `lcca-metrics.jsonl` with tool name, mode, token counts from Lambda response.

6. **Kiro MCP integration:**
   - Register `lcca-context-tools` via `.kiro/settings/mcp.json`.
   - Confirm tools appear in Kiro.

7. **Custom agent configuration:**
   - Create `lcca-coding-agent` with `mcpServers` pointing to `lcca-context-tools`.
   - Set `allowedTools` to exclude built-in `read` and `grep`, include MCP tools.

8. **Clone pyjwt and prepare tasks:**
   - Clone `jpadilla/pyjwt` locally.
   - Write three task description files in `tasks/` (bug_fix.md, feature_impl.md, refactor.md).
   - Introduce the bug for task 1.

9. **Run baseline mode (3 tasks):**
   - Agent without MCP tools; record credit usage before/after, save transcript.

10. **Run LCCA mode (3 tasks):**
    - Same tasks with MCP tools; record credit usage before/after, save transcript and `lcca-metrics.jsonl`.

11. **Aggregate and document results:**
    - Compare success, token estimates, and cost per task across both modes.


## 9. Risks and Limitations

- **Agent compliance with tool restrictions:**
  - Removing `read` and `grep` from `allowedTools` enforces MCP usage structurally, but the agent may use `shell` with `cat` or `grep` as a workaround.
  - Mitigation: monitor session transcripts; if needed, add a shell command filter or note in the write-up.

- **Token accounting precision:**
  - Kiro CLI credit delta gives cost, not exact token counts. Large-model token estimates are derived from pricing, not direct measurement.
  - Mitigation: supplement with `tiktoken` estimates on saved transcripts; be explicit in write-up about methodology.

- **Over-compression by small model:**
  - Llama 3.2 3B may omit crucial code details when summarising.
  - Mitigation: conservative `max_tokens` limits, task-specific prompts, and documenting any observed failures in the write-up.


## 10. Sources

- PLAN-ContextAwareCodingAgent.md (previous standalone agent plan; used for internal architecture ideas like small-model tools and measurement fields).[cite:27]
- Kiro CLI built-in tools documentation (read, grep, glob, write, shell, code, tool_settings, allowedTools, and MCP tool naming for `@server_name/tool_name`).[cite:1]
- "Bring Kiro agents to your terminal with Kiro CLI" – official blog post explaining Kiro CLI, custom agents, context management, MCP support, and credit usage.[cite:2]
- "Model Context Protocol (MCP) - CLI - Docs - Kiro" – describes how to configure MCP servers via `kiro-cli mcp add`, `mcp.json`, and the `mcpServers` field in agent configs.[cite:3]
- AVAILABLE_MODELS.md – AWS Bedrock proxy available models; small model selected: `us.meta.llama3-2-3b-instruct-v1:0`.
