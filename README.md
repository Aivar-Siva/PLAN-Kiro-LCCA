# PLAN-Kiro-LCCA

Context-Optimised Coding Agent — Kiro CLI + MCP small-model tools.

The main Kiro agent handles reasoning and code changes. A local MCP server (`lcca-context-tools`) intercepts large I/O operations (file reads, grep results, test logs) and compresses them with a small model before they reach Kiro's context.

## Setup

**1. Clone and init submodule**
```bash
git clone <repo-url>
cd PLAN-Kiro-LCCA
git submodule update --init
```

**2. Create venv and install MCP server**
```bash
python3 -m venv .venv
.venv/bin/pip install -e ./lcca-context-tools
.venv/bin/pip install -e "pyjwt[crypto]" pytest
```

**3. Configure the Lambda endpoint**

Edit `lcca-context-tools/lcca-config.yaml` and set your Lambda URL and model:
```yaml
lambda_url: "https://<your-lambda-url>/"
model_id: "us.meta.llama4-scout-17b-instruct-v1:0"
```

**4. Verify MCP server starts**
```bash
.venv/bin/lcca-context-tools
# Should start silently (waiting for stdio). Ctrl+C to stop.
```

**5. Register with Kiro**

The workspace MCP config is already at `.kiro/settings/mcp.json`. Kiro picks it up automatically when you open the project. Verify:
```bash
kiro-cli mcp list
# Should show: lcca-context-tools
```

## Usage

**With MCP compression (LCCA agent):**
```bash
kiro-cli chat --agent lcca-coding-agent
```

**Without MCP (baseline):**
```bash
kiro-cli chat --agent baseline-coding-agent
```

## Evaluation

See [eval.md](eval.md) for the three evaluation tasks and how to measure token usage and cost.

## MCP Tools

| Tool | Replaces | When small model fires |
|---|---|---|
| `read_or_summarize` | `fs_read` | File > 200 lines |
| `smart_grep` | `grep` | Results > 10 matches |
| `analyze_error` | manual log reading | Always |

Token usage per call is logged to `lcca-metrics.jsonl` (gitignored).
