"""MCP server exposing small-model context tools."""
import os
import yaml
from mcp.server.fastmcp import FastMCP
from lcca_context_tools.tools.read_or_summarize import read_or_summarize as _ros
from lcca_context_tools.tools.analyze_error import analyze_error as _ae
from lcca_context_tools.tools.smart_grep import smart_grep as _sg

mcp = FastMCP("lcca-context-tools")

def _cfg() -> dict:
    path = os.environ.get("LCCA_CONFIG_PATH", "./lcca-config.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


@mcp.tool()
def read_or_summarize(path: str, task_query: str,
                      threshold_lines: int = 200, max_summary_tokens: int = 800) -> dict:
    """Read a file. Returns raw content for small files, a task-focused summary for large ones."""
    return _ros(path, task_query, _cfg(), threshold_lines, max_summary_tokens)


@mcp.tool()
def analyze_error(path: str, task_query: str, max_tokens: int = 800) -> dict:
    """Analyze a test log or stack trace. Returns root cause, failing tests, and suspected files."""
    return _ae(path, task_query, _cfg(), max_tokens)


@mcp.tool()
def smart_grep(pattern: str, path: str, task_query: str, max_results: int = 10) -> dict:
    """Search for a pattern. Returns top-ranked matches without flooding context."""
    return _sg(pattern, path, task_query, _cfg(), max_results)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
