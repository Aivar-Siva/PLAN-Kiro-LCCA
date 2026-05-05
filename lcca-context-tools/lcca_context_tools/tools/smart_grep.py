import subprocess
from lcca_context_tools.bedrock_client import call_small_model
from lcca_context_tools.metrics import log_metric
import json


def smart_grep(pattern: str, path: str, task_query: str, config: dict,
               max_results: int = None) -> dict:
    max_results = max_results or config["tools"]["smart_grep"]["max_results"]

    result = subprocess.run(
        ["grep", "-rn", "--include=*.py", pattern, path],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    total = len(lines)

    if total <= max_results:
        log_metric(config, "smart_grep", "raw", {}, {"pattern": pattern, "total_found": total})
        return {
            "top_matches": [{"raw": l} for l in lines],
            "summary": f"Found {total} matches.",
            "total_found": total,
        }

    matches_text = "\n".join(lines)
    prompt = (
        f"Task: {task_query}\n\n"
        f"From these grep results, return a JSON object with keys:\n"
        f"- top_matches: list of the {max_results} most relevant match strings\n"
        f"- summary: one sentence explaining what the matches indicate\n\n"
        f"Output ONLY valid JSON, no markdown fences.\n\n"
        f"Matches:\n{matches_text}"
    )
    raw, usage = call_small_model(prompt, 600, config)
    log_metric(config, "smart_grep", "ranked", usage,
               {"pattern": pattern, "total_found": total})

    try:
        result_data = json.loads(raw)
    except json.JSONDecodeError:
        result_data = {"top_matches": lines[:max_results], "summary": raw}

    result_data["total_found"] = total
    return result_data
