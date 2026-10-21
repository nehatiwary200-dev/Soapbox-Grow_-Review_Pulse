"""Soapbox static dashboard + MCP approval logger for Railway.

Serves the original HTML/CSS at / and /styles.css, and exposes the MCP
Streamable HTTP endpoint at /mcp. The dashboard files are served as-is; this
file does not re-render or rewrite the UI.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = Path(os.environ.get("LOG_FILE", str(BASE_DIR / "mcp_approval_log.jsonl")))
PORT = int(os.environ.get("PORT", "8000"))

mcp = FastMCP("Soapbox MCP Logger", host="0.0.0.0", port=PORT)


@mcp.custom_route("/", methods=["GET"])
async def dashboard(_request: Request) -> FileResponse:
    """Serve the original standalone Soapbox dashboard."""
    return FileResponse(BASE_DIR / "index.html", media_type="text/html")


@mcp.custom_route("/styles.css", methods=["GET"])
async def stylesheet(_request: Request) -> FileResponse:
    """Serve the dashboard stylesheet separately from the HTML."""
    return FileResponse(BASE_DIR / "styles.css", media_type="text/css")


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    """Health endpoint for Railway deployment checks."""
    return JSONResponse({"status": "ok", "service": "soapbox-mcp-logger"})


@mcp.tool()
def log_approved_output(
    output_type: str,
    content: str,
    approval_status: str,
    reporting_window: str = "",
) -> str:
    """Append a Soapbox output to the audit log only after explicit approval."""
    if approval_status.strip().lower() != "approved":
        raise ValueError("Output not logged: explicit approval is required.")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_type": output_type,
        "content": content,
        "approval_status": "approved",
        "reporting_window": reporting_window,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return f"Approved {output_type} logged successfully."


@mcp.tool()
def get_recent_logs(limit: int = 10) -> str:
    """Retrieve recent Soapbox approval logs."""
    limit = max(1, min(limit, 50))
    if not LOG_FILE.exists():
        return "No approved outputs logged yet."
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-limit:]) or "No approved outputs logged yet."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
