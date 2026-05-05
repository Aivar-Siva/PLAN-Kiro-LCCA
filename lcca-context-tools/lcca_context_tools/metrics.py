"""Append-only JSONL metrics logger."""
import json
import os
from datetime import datetime, timezone


def log_metric(config: dict, tool: str, mode: str, usage: dict, extra: dict = None):
    path = config.get("metrics_path", "./lcca-metrics.jsonl")
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "mode": mode,
        "prompt_tokens": usage.get("prompt_tokens", usage.get("inputTokens", 0)),
        "completion_tokens": usage.get("completion_tokens", usage.get("outputTokens", 0)),
    }
    if extra:
        record.update(extra)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
