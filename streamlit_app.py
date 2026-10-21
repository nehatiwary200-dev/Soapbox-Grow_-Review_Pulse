from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "index.html"
CSS_FILE = BASE_DIR / "styles.css"
STYLESHEET_LINK = '<link rel="stylesheet" href="styles.css">'

st.set_page_config(
    page_title="Soapbox — Groww Review Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if not HTML_FILE.is_file():
    st.error("Missing index.html. Keep it in the same repository folder as streamlit_app.py.")
    st.stop()

html = HTML_FILE.read_text(encoding="utf-8")

# This wrapper renders the existing HTML/JavaScript UI as-is. It inlines the
# stylesheet because an iframe in Streamlit Cloud cannot reliably resolve a
# relative file URL such as ./styles.css.
if STYLESHEET_LINK in html:
    if not CSS_FILE.is_file():
        st.error("Missing styles.css. Keep it beside index.html and streamlit_app.py.")
        st.stop()
    css = CSS_FILE.read_text(encoding="utf-8")
    html = html.replace(STYLESHEET_LINK, "<style>\n" + css + "\n</style>", 1)

components.html(html, height=1900, scrolling=True)
