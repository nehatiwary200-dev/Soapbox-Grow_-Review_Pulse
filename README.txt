Soapbox Streamlit scroll/background fix

Replace ONLY streamlit_app.py in the existing Streamlit GitHub repository with this version.
Keep index.html, styles.css, requirements.txt, the MCP server, and other files unchanged.

This wrapper keeps the HTML in an iframe but removes Streamlit host-page margins,
sets its background to match the dashboard, and uses a tall non-scrolling iframe
to avoid the nested scrollbar. The Streamlit Cloud owner's “Manage app” overlay
may still be shown by the hosting platform and is not part of the dashboard CSS.
