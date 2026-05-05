from pathlib import Path
from lcca_context_tools.bedrock_client import call_small_model
from lcca_context_tools.metrics import log_metric


def read_or_summarize(path: str, task_query: str, config: dict,
                      threshold_lines: int = None, max_summary_tokens: int = None) -> dict:
    tool_cfg = config["tools"]["read_or_summarize"]
    configured_threshold = tool_cfg["threshold_lines"]
    # Cap to configured default — agent cannot override upward
    threshold = min(threshold_lines or configured_threshold, configured_threshold)
    max_tokens = max_summary_tokens or tool_cfg["max_summary_tokens"]

    content = Path(path).read_text(errors="replace")
    lines = content.splitlines()

    if len(lines) <= threshold:
        log_metric(config, "read_or_summarize", "raw", {})
        return {"content": content, "mode": "raw"}

    prompt = (
        f"Task: {task_query}\n\n"
        f"Summarize the following code file. Keep relevant function/class signatures, "
        f"key control flow, and anything related to the task. Drop docstrings and comments "
        f"unless task-relevant. List key symbols.\n\n"
        f"File ({len(lines)} lines):\n{content}"
    )
    summary, usage = call_small_model(prompt, max_tokens, config)
    log_metric(config, "read_or_summarize", "summarized", usage,
               {"path": path, "original_lines": len(lines)})

    # Extract key symbols heuristically from summary lines starting with def/class
    key_symbols = [
        line.strip().split("(")[0].replace("def ", "").replace("class ", "")
        for line in summary.splitlines()
        if line.strip().startswith(("def ", "class "))
    ]
    return {
        "content": summary,
        "mode": "summarized",
        "key_symbols": key_symbols,
        "original_lines": len(lines),
    }
