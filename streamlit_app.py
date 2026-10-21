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

# Make the Streamlit host page blend into the original dashboard canvas and
# remove excess margins. The HTML app remains its own document in the iframe.
st.markdown(
    """
    <style>
      :root { color-scheme: light; }
      html, body, [data-testid="stApp"],
      [data-testid="stAppViewContainer"], [data-testid="stMain"],
      [data-testid="stMainBlockContainer"] {
        background: #f5f7f7 !important;
      }
      [data-testid="stMainBlockContainer"] {
        max-width: 100% !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
      }
      [data-testid="stHeader"] { background: #f5f7f7 !important; }
      [data-testid="stToolbar"], #MainMenu, footer { visibility: hidden !important; }
      iframe { border: 0 !important; display: block !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not HTML_FILE.is_file():
    st.error("Missing index.html. Keep it beside streamlit_app.py.")
    st.stop()

html = HTML_FILE.read_text(encoding="utf-8")
if STYLESHEET_LINK in html:
    if not CSS_FILE.is_file():
        st.error("Missing styles.css. Keep it beside index.html and streamlit_app.py.")
        st.stop()
    css = CSS_FILE.read_text(encoding="utf-8")
    html = html.replace(STYLESHEET_LINK, "<style>\n" + css + "\n</style>", 1)

# A tall, non-scrolling iframe avoids nested scrollbars. The outer page scrolls
# naturally; the matching host background prevents the black frame around it.
components.html(html, height=5200, scrolling=False)
