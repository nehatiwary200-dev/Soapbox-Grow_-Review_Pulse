# Soapbox — Groww Review Pulse

Soapbox turns a date-bounded export of Groww Play Store reviews into a weekly product pulse and a support-ready fee explainer. It combines a lightweight dashboard with an n8n workflow for review processing, human approval, publishing, and audit logging.

## Demo links

- **Live frontend prototype:** https://nehatiwary200-dev.github.io/Soapbox-Grow_-Review_Pulse/
- **Published n8n workflow form:** https://neha045.app.n8n.cloud/form/ec41e5c7-6c19-49d2-ad04-8752c5ee7e2b
- **GitHub repository:** https://github.com/nehatiwary200-dev/Soapbox-Grow_-Review_Pulse

> **Important:** The n8n form is an interactive workflow entry point, not a read-only demo page. Submitting it may start a workflow run and create or update a Google Doc and a Gmail draft. Do not submit it just to preview the form. The n8n editor link is not included because it may require account access.

## What it does

1. Accepts a review CSV through the n8n form workflow.
2. Filters reviews to the reporting window and deduplicates records.
3. Classifies reviews into a small set of themes and ranks the leading themes.
4. Builds a weekly product pulse with evidence and user quotes.
5. Prepares a fee-and-charges explainer with links to official Groww resources.
6. Pauses for human approval before the Google Docs and Gmail draft publishing branch.
7. Logs the approved output through the MCP client tool.

## Demonstrated run

The demonstrated execution processed **1,111 unique reviews** for **22 July–14 October 2026**. The n8n run completed review classification and output generation, created/updated a Google Doc, created a Gmail draft, and returned this MCP logging result:

`Approved weekly_pulse_and_fee_explainer logged successfully.`

This describes the demonstrated run; results can change with a different CSV or reporting window.

## Architecture

- **Frontend:** Static HTML/CSS dashboard hosted on GitHub Pages.
- **Workflow and approval:** n8n Cloud.
- **Publishing outputs:** Google Docs and a Gmail draft. The workflow creates a draft; it does not send the email.
- **MCP logging:** MCP Client call logs the approved pulse and fee explainer.
- **Python components:** The repository also contains Python dashboard/server components for inspection and further development.

GitHub Pages hosts the frontend only. The review-processing and publishing workflow runs in n8n and uses configured integrations. The form and dashboard are separate entry points; do not imply that the static frontend directly runs the n8n backend unless that connection is implemented and verified.

## Approval and safety

- Human approval is required before the Google Docs and Gmail draft publishing branch.
- Rejected output should not trigger publishing actions.
- Gmail creates a draft only; no send-email action is intended.
- Review quotes should remain verbatim and traceable to the source review records.
- Fee claims should be checked against official Groww pages and carry a last-checked date.
- Do not commit API keys, credentials, bearer tokens, or other secrets to this repository.

## Data and sources

The workflow expects a CSV review export supplied through the form. The demonstrated reporting window was 22 July–14 October 2026.

Official references used for the fee explainer:

- Groww pricing: https://groww.in/pricing
- Groww Help Centre: https://groww.in/help

Include the exact review CSV in the submission only if distribution is permitted and the file contains no sensitive information.

## How to review the submission

1. Open the [live frontend prototype](https://nehatiwary200-dev.github.io/Soapbox-Grow_-Review_Pulse/).
2. Inspect the exported n8n workflow JSON in the repository or submission materials.
3. Review the successful n8n execution screenshot.
4. Open the generated Google Doc and check the pulse and fee explainer.
5. Open Gmail Drafts and inspect the generated draft. **Do not send it.**

## Deployment note

The frontend is published on GitHub Pages and the workflow is hosted in n8n Cloud. The demonstrated MCP client configuration used a temporary ngrok endpoint without authentication. Therefore, the tested workflow should be described as a working demonstration, not as a permanently hosted, production-hardened MCP service. A stable authenticated endpoint should be configured before ongoing production use.
