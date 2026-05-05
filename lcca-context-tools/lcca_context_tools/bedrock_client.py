"""Thin HTTP client for the AWS Bedrock Lambda proxy (streaming SSE)."""
import json
import requests


def call_small_model(prompt: str, max_tokens: int, config: dict) -> tuple[str, dict]:
    """Call small model via Lambda proxy. Returns (text, usage)."""
    model_id = config["model_id"]

    # Llama 4 uses prompt/max_gen_len; Llama 3.x uses messages/max_tokens
    if "llama4" in model_id:
        payload = {"model_id": model_id, "prompt": prompt, "max_gen_len": max_tokens}
    else:
        payload = {"model_id": model_id, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}

    resp = requests.post(config["lambda_url"], json=payload, timeout=120, stream=True)
    resp.raise_for_status()

    text_parts = []
    prompt_tokens = 0
    completion_tokens = 0

    for raw_line in resp.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("data: "):
            line = line[6:]
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Accumulate text
        text_parts.append(chunk.get("generation", ""))

        # Capture token counts from first chunk (has prompt_token_count) and last (stop_reason)
        if chunk.get("prompt_token_count"):
            prompt_tokens = chunk["prompt_token_count"]
        if chunk.get("generation_token_count"):
            completion_tokens = chunk["generation_token_count"]

    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}
    return "".join(text_parts), usage
