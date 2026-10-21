SOAPBOX STREAMLIT UI RECOVERY PACKAGE

This package renders the existing HTML/JavaScript dashboard in Streamlit rather than running the separate simplified soapbox_dashboard.py UI.

FILES TO KEEP TOGETHER AT THE ROOT OF THE GITHUB REPOSITORY:
- streamlit_app.py  (Streamlit entry point; this is the main file path to select)
- index.html        (HTML UI with link to styles.css)
- styles.css        (CSS extracted from the original inline style block; exact reconstitution returns the original HTML content)
- requirements.txt  (runtime dependencies)

STREAMLIT CLOUD:
1. Upload/commit these files at repository root.
2. In the Streamlit app settings, set Main file path to streamlit_app.py.
3. Reboot/redeploy the app.

Do not use soapbox_dashboard.py as the main file path for this UI. That file runs a different Streamlit-built interface and expects styles.css through a separate code path.

The wrapper inlines styles.css into the HTML before rendering, so the CSS rules and original JavaScript stay with the UI inside the component iframe.
