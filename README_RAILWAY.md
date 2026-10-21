# Soapbox Railway deployment

This service serves the original HTML/CSS dashboard and the MCP logger from one Railway web service:

- Dashboard: `/`
- CSS: `/styles.css`
- Health check: `/health`
- MCP Streamable HTTP endpoint: `/mcp`

The original dashboard HTML and its JavaScript are preserved from the reviewed local HTML/CSS pair. `mcp_server.py` only serves those static files and hosts the existing MCP tools; it does not render the UI through Streamlit.

## Railway settings

- Source: this GitHub repository, branch `main`
- Build command: `pip install -r requirements.txt`
- Start command: `python mcp_server.py`
- Health check path: `/health`
- Generate a public domain in Railway Networking settings

## Log persistence

Add a Railway Volume mounted at `/app/data`, then set the service variable:

`LOG_FILE=/app/data/mcp_approval_log.jsonl`

Without a volume, the log file may be lost when a container is replaced.

## n8n MCP Client

After deploy succeeds, set Server Transport to HTTP Streamable and use:

`https://YOUR-RAILWAY-DOMAIN/mcp`

The service's current MCP tools are unauthenticated, matching the existing tested n8n configuration. Restrict access (or add authentication) before using this endpoint for sensitive logs in a production environment.

## Public repository hygiene

Do not commit `mcp_approval_log.jsonl` or any tokens. It contains saved review/output content. If the repository is public, remove the log from the repository and make the repository private if appropriate.
