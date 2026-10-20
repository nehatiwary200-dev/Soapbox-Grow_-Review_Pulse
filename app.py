from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Soapbox — Groww Review Intelligence",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

html_path = Path(__file__).parent / "index.html"

if not html_path.exists():
    st.error("index.html was not found beside app.py. Put your original Soapbox index.html in the same folder.")
    st.stop()

html = html_path.read_text(encoding="utf-8")
# Render the original HTML app inside Streamlit, preserving its layout, embedded dataset,
# keyword clas/Users/nehatiwary/Documents/Soapbox-dashboard/index.htmlsifications, date filtering, evidence investigation, drafts, and CSV export.
components.html(html, height=1800, scrolling=True)
