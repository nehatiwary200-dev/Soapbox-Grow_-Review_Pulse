import json
import os
from datetime import datetime, timezone
from pathlib import Path
from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = Path(os.environ.get("LOG_FILE", str(BASE_DIR / "mcp_approval_log.jsonl")))

mcp = FastMCP("Soapbox MCP Logger", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

@mcp.tool()
def log_approved_output(
    output_type: str,
    content: str,
    approval_status: str,
    reporting_window: str = ""
) -> str:
    """Log a Soapbox output only after explicit approval."""
    if approval_status.strip().lower() != "approved":
        raise ValueError("Output not logged: explicit approval is required.")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_type": output_type,
        "content": content,
        "approval_status": "approved",
        "reporting_window": reporting_window,
    }

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
