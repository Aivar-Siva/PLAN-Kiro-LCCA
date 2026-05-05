"""Thin HTTP client for the AWS Bedrock Lambda proxy."""
import requests

def call_small_model(prompt: str, max_tokens: int, config: dict) -> tuple[str, dict]:
    """Call small model via Lambda proxy. Returns (text, usage)."""
    payload = {
        "model_id": config["model_id"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    resp = requests.post(config["lambda_url"], json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Extract text from Llama 3.x response format
    text = data.get("generation") or data.get("content", [{}])[0].get("text", "")
    usage = data.get("usage", {})
    return text, usage
