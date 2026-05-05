from pathlib import Path
from lcca_context_tools.bedrock_client import call_small_model
from lcca_context_tools.metrics import log_metric
import json


def analyze_error(path: str, task_query: str, config: dict, max_tokens: int = None) -> dict:
    max_tokens = max_tokens or config["tools"]["analyze_error"]["max_tokens"]
    content = Path(path).read_text(errors="replace")

    prompt = (
        f"Task: {task_query}\n\n"
        f"Analyze this test/error output. Return a JSON object with keys:\n"
        f"- summary: one paragraph root cause analysis\n"
        f"- failing_tests: list of failing test names\n"
        f"- suspected_files: list of source files implicated\n"
        f"- key_errors: list of the most important error messages\n\n"
        f"Output ONLY valid JSON, no markdown fences.\n\n"
        f"Log:\n{content}"
    )
    raw, usage = call_small_model(prompt, max_tokens, config)
    log_metric(config, "analyze_error", "summarized", usage, {"path": path})

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"summary": raw, "failing_tests": [], "suspected_files": [], "key_errors": []}

    return result
