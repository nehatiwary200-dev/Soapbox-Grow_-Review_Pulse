"""Soapbox — Groww Review Intelligence (Streamlit native port).

Preserves the original index.html design and functionality:
  * embedded 1,500-row Groww Google Play review dataset
  * five-theme keyword classification
  * date filtering + dedup by Review URL
  * evidence investigation with supporting quotes
  * fee sentiment breakdown (complaint / positive / mention)
  * weekly pulse draft + product-action draft dialogs
  * CSV upload (replaces dataset) and filtered CSV export
  * prototype-guardrail copy throughout

Run:  streamlit run soapbox_dashboard.py
"""
from __future__ import annotations

import base64
import csv
import io
import re
from datetime import date, datetime
from html import escape

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Embedded dataset (source of truth: index.html <script id="dataset">)
# ---------------------------------------------------------------------------
from dataset_literal import DATASET  # noqa: E402  (generated from index.html)

# ---------------------------------------------------------------------------
# Theme definitions (mirrors index.html keyword rules, in priority order)
# ---------------------------------------------------------------------------
DEFINITIONS = [
    {
        "id": "trading",
        "name": "Trading reliability & execution",
        "tag": "Trading experience",
        "desc": "Reviews mentioning order execution, app hangs, latency, charts, intraday or trading failures.",
        "re": r"\b(order|execution|execut|trade|trading|intraday|stop.?loss|market open|hang|stuck|freeze|lag|slow|crash|chart|price|sell order|buy order)\b",
        "question": "Are these reports concentrated around a particular order type, time, app version or device?",
    },
    {
        "id": "account",
        "name": "Account access & support",
        "tag": "Account and support",
        "desc": "Reviews mentioning login, OTP, KYC, verification, account access or support response.",
        "re": r"\b(otp|login|log in|sign in|account|kyc|verification|verify|password|support|customer care|customer service|ticket|blocked|locked)\b",
        "question": "Which step in access or support is failing, and how often do independent reviews describe the same step?",
    },
    {
        "id": "fees",
        "name": "Fees, charges & deductions",
        "tag": "Fee transparency",
        "desc": "Reviews explicitly mentioning charges, brokerage, fees, deductions or money allegedly taken.",
        "re": r"\b(charge|charges|brokerage|fee|fees|deduct|deduction|cutting money|money cut|paisa kat|hidden charge|dp charge|cdsl|gst|commission|expensive brokerage)\b",
        "question": "Which specific charge is named by multiple independent reviews, and does official documentation confirm how it is calculated?",
    },
    {
        "id": "money",
        "name": "Funds, withdrawals & transactions",
        "tag": "Money movement",
        "desc": "Reviews mentioning withdrawal, redemption, deposits, refunds or settlement delays.",
        "re": r"\b(withdraw|withdrawal|redeem|redemption|deposit|refund|credited|credit money|settlement|bank transfer|payment failed|money not|payout|upi)\b",
        "question": "At which transaction stage do users report delays or failures, and is the issue consistent across transaction types?",
    },
    {
        "id": "general",
        "name": "General sentiment & other feedback",
        "tag": "General feedback",
        "desc": "Reviews that do not match a more specific issue category using the current keyword rules.",
        "re": r".*",
        "question": "Can more specific reviews be separated from generic ratings and low-detail comments?",
    },
]

# Compiled regexes
for d in DEFINITIONS:
    d["re_compiled"] = re.compile(d["re"], re.IGNORECASE)

FEE_NEG = re.compile(
    r"(hidden|unexpected|unfair|too high|high brokerage|high charges|high charge|extra charge|wrong charge|wrongly deduct|"
    r"money (was )?deduct|deducted|deduction|paisa bahut kat|paisa kat raha|loot|chor|stolen|charged me|charging too much|"
    r"overcharg|expensive|not transparent|without (my )?consent|money cut|cut my money|cutting money|fees? are high|charges? are high)",
    re.IGNORECASE,
)
FEE_POS = re.compile(
    r"(low (broker|charge|fee)|broker charge low|brokerage (is )?low|free brokerage|zero brokerage|no brokerage|cheap|"
    r"affordable|reasonable charge|low charges|low fees|good brokerage|good app broker charge low)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers (ported from index.html JS)
# ---------------------------------------------------------------------------
def fmt(n: int) -> str:
    return f"{n:,}"


def day(s) -> str:
    return str(s or "")[:10]


def classify(row) -> str:
    text = f"{row.get('Title','')} {row.get('Review','')}"
    for d in DEFINITIONS[:4]:
        if d["re_compiled"].search(text):
            return d["id"]
    return "general"


def fee_sentiment(row) -> str:
    s = f"{row.get('Title','')} {row.get('Review','')}".lower()
    neg = bool(FEE_NEG.search(s))
    pos = bool(FEE_POS.search(s))
    if neg and not pos:
        return "complaint"
    if pos and not neg:
        return "positive"
    return "mention"


def parse_csv_text(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for r in reader:
        rows.append({k: (v if v is not None else "") for k, v in r.items()})
    return rows


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def apply_filter(df: pd.DataFrame, start: date, end: date):
    """Return (unique_df, themes, date_rows_count, dup_removed)."""
    start_s = start.isoformat()
    end_s = end.isoformat()
    if start > end:
        return None

    date_rows = df[(df["Date"] >= start_s) & (df["Date"] <= end_s)].copy()

    seen = set()
    unique_rows = []
    for _, r in date_rows.iterrows():
        url = str(r.get("Review URL") or "").strip()
        if url:
            key = url
        else:
            key = "|".join([day(r.get("Date")), str(r.get("Rating")), str(r.get("Title")), str(r.get("Review"))])
        if key in seen:
            continue
        seen.add(key)
        row = r.to_dict()
        row["_theme"] = classify(row)
        unique_rows.append(row)

    unique = pd.DataFrame(unique_rows) if unique_rows else pd.DataFrame(columns=list(df.columns) + ["_theme"])

    themes = []
    for d in DEFINITIONS:
        items = unique[unique["_theme"] == d["id"]] if "_theme" in unique.columns else unique.iloc[0:0]
        themes.append({**d, "count": int(len(items)), "items": items.to_dict("records")})
    themes.sort(key=lambda t: t["count"], reverse=True)

    return {
        "unique": unique,
        "themes": themes,
        "date_rows_count": len(date_rows),
        "dup_removed": len(date_rows) - len(unique),
    }


def quote_for(items, limit: int = 3):
    valid = [r for r in items if str(r.get("Review") or r.get("Title") or "").strip()]
    valid.sort(key=lambda r: str(r.get("Date") or ""), reverse=True)
    return valid[:limit]


def make_pulse(start_s: str, end_s: str, filtered_count: int, themes) -> str:
    top = [t for t in themes if t["count"]][:3]
    lines = [
        f"Soapbox weekly review pulse — {start_s} to {end_s}",
        f"Dataset: {filtered_count} unique reviews from the uploaded public Google Play export. The source export is a sample, not a census of all Groww users.",
        "",
        "Top themes (rule-based; manually validate before sharing):",
    ]
    for i, t in enumerate(top, 1):
        pct = round(t["count"] / filtered_count * 1000) / 10 if filtered_count else 0
        lines.append(f"{i}. {t['name']}: {t['count']} reviews ({pct}%).")
    lines.append("")
    lines.append("Evidence excerpts:")
    fees = next((t for t in themes if t["id"] == "fees"), None)
    source_theme = fees or (top[0] if top else None) or (themes[0] if themes else None)
    q = quote_for(source_theme["items"]) if source_theme else []
    if q:
        for r in q:
            text = str(r.get("Review") or r.get("Title")).strip()[:240]
            lines.append(f"• {day(r.get('Date'))}, {r.get('Rating')}★: “{text}”")
    else:
        lines.append("• No substantive source quotes available in the selected dataset.")
    lines += [
        "",
        "Key observation: Keyword themes indicate topics mentioned in this export; they do not establish root cause or represent all Groww customers. Fee confusion should be described as a hypothesis unless multiple independent reviews identify the same specific charge.",
        "",
        "Suggested actions:",
        "1. Inspect source reviews and manually validate the highest-volume issue theme.",
        "2. Compare recurring claims with official documentation and support-contact data before proposing a fix.",
        "3. Track theme counts and evidence quality in the next review window; separate generic sentiment from actionable complaints.",
    ]
    return "\n".join(lines)


def make_actions(start_s: str, end_s: str, themes) -> str:
    top = [t for t in themes if t["count"]][:3]
    parts = [
        "Draft product actions — Soapbox",
        f"Reporting window: {start_s} to {end_s}",
        "",
        "Evidence caveat: themes are keyword grouped and require human validation.",
        "",
    ]
    for i, x in enumerate(top, 1):
        parts.append(
            f"{i}. Investigate “{x['name']}” ({x['count']} matching unique reviews).\n"
            f"   Question: {x['question']}\n"
            f"   Next step: inspect source reviews, segment by rating/date/app version, and validate against product/support data before prioritising."
        )
    parts += ["", "No external actions have been taken."]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Page config + CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Soapbox — Groww Review Intelligence",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = open("styles.css", encoding="utf-8").read()
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
st.markdown('<div class="soapbox-page">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
DEFAULT_START = date(2026, 7, 22)
DEFAULT_END = date(2026, 10, 14)

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(DATASET)
    st.session_state.source_file_label = "Embedded Groww Google Play review snapshot"
if "start" not in st.session_state:
    st.session_state.start = DEFAULT_START
if "end" not in st.session_state:
    st.session_state.end = DEFAULT_END
if "selected" not in st.session_state:
    st.session_state.selected = ""
if "derived" not in st.session_state:
    st.session_state.derived = None


def recompute():
    res = apply_filter(st.session_state.df, st.session_state.start, st.session_state.end)
    if res is None:
        st.toast("Choose a valid date range.")
        return
    st.session_state.derived = res
    themes = res["themes"]
    if not st.session_state.selected or not any(
        t["id"] == st.session_state.selected and t["count"] for t in themes
    ):
        st.session_state.selected = next((t["id"] for t in themes if t["count"]), "general")
    st.toast("Date filter and theme counts recalculated from loaded CSV.")


# Initial compute
if st.session_state.derived is None:
    recompute()

# ---------------------------------------------------------------------------
# Sidebar (brand + nav + source chip)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-brandname">◉ Soapbox</div>'
        '<div class="sb-tagline">VOICE → ACTION</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sb-nav">', unsafe_allow_html=True)
    nav_items = [
        ("Review Inbox", "▤", "inbox"),
        ("Investigation Room", "⌕", "investigation"),
        ("Weekly Pulse", "⌁", "pulse"),
        ("Approved Outputs", "✓", "outputs"),
    ]
    active_view = st.session_state.get("view", "investigation")
    for label, icon, key in nav_items:
        is_active = active_view == key
        cls = "nav-link active" if is_active else "nav-link"
        if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            st.session_state.view = key
            st.rerun()
        # Visual active state via button is limited; mark via CSS class not applicable to st.button.
        # We track active in session_state and render a small indicator instead.
    st.markdown("</div>", unsafe_allow_html=True)

    # Active-view indicator (small chips under nav)
    st.markdown(
        f'<div style="margin-top:8px;font-size:11px;color:#bfd0dd;">View: <strong style="color:#93c5fd">{active_view.replace("_"," ").title()}</strong></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-source">'
        '<strong><span class="dot"></span> Local dataset loaded</strong>'
        f'<small id="sourceSummary">{fmt(len(st.session_state.df))} rows · '
        f"{fmt(st.session_state.df['Review URL'].astype(str).str.strip().ne('').sum())} unique URLs</small>"
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
with st.container():
    st.markdown('<div class="soapbox-main">', unsafe_allow_html=True)

    # Utility bar: filters + status
    st.markdown('<div class="utility"><div class="filters">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1.15, 1.15, 0.95, 1.6])
    with c1:
        st.session_state.start = st.date_input("From", value=st.session_state.start, key="inp_start")
    with c2:
        st.session_state.end = st.date_input("To", value=st.session_state.end, key="inp_end")
    with c3:
        if st.button("Apply", key="btn_apply", use_container_width=True):
            recompute()
    with c4:
        upload = st.file_uploader("Upload CSV", type=["csv"], key="file_upload", label_visibility="collapsed")
        if upload is not None:
            text = upload.read().decode("utf-8", errors="replace")
            try:
                parsed = parse_csv_text(text)
                if not parsed:
                    st.toast("Could not parse CSV. Please upload a standard comma-separated review export.")
                else:
                    st.session_state.df = pd.DataFrame(parsed)
                    st.session_state.source_file_label = upload.name
                    st.session_state.derived = None
                    recompute()
                    st.toast(f"Loaded {fmt(len(st.session_state.df))} rows from {upload.name}")
            except Exception:
                st.toast("Could not parse CSV. Please upload a standard comma-separated review export.")
    st.markdown("</div>", unsafe_allow_html=True)

    derived = st.session_state.derived
    if derived is None:
        st.stop()

    unique = derived["unique"]
    themes = derived["themes"]
    date_rows_count = derived["date_rows_count"]
    dup_removed = derived["dup_removed"]
    filtered_count = len(unique)

    c5, c6 = st.columns([4, 1])
    with c5:
        st.markdown('<div class="status"><span class="dot"></span><span id="datasetStatus">Dataset loaded</span></div>', unsafe_allow_html=True)
    with c6:
        if st.button("↓ Export filtered CSV", key="btn_export", use_container_width=True):
            csv_bytes = dataframe_to_csv_bytes(unique)
            st.download_button(
                "Download filtered CSV",
                data=csv_bytes,
                file_name="soapbox_groww_reviews_filtered.csv",
                mime="text/csv",
                key="dl_filtered",
                use_container_width=True,
            )

    # Heading
    st.markdown(
        '<div class="heading"><div class="heading-left">'
        '<div class="eyebrow">ANALYSING: GROWW · GOOGLE PLAY</div>'
        '<h1 class="h1">Investigation Room</h1>'
        '<p class="subtitle">Understand the evidence before deciding what to fix.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # Provenance
    start_s = st.session_state.start.isoformat()
    end_s = st.session_state.end.isoformat()
    start_label = st.session_state.start.strftime("%d %b")
    end_label = st.session_state.end.strftime("%d %b %Y")
    st.markdown(
        f'<div class="provenance card" aria-live="polite">'
        '<div class="prov-icon">↳</div>'
        '<div class="prov-copy">'
        '<strong>Analysis based on loaded CSV data</strong>'
        f'<span id="provenanceFile">{escape(st.session_state.source_file_label)}</span>'
        '<small id="provenanceDetail">Results below are calculated from this dataset and the selected date window. Keyword themes require human review.</small>'
        '</div>'
        '<div class="prov-meta">'
        f'<span class="prov-chip" id="provenanceWindow">{start_label} – {end_label}</span>'
        f'<span class="prov-chip" id="provenanceRows">{fmt(len(st.session_state.df))} source rows</span>'
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Metrics
    st.markdown(
        f'<div class="metrics">'
        f'<div class="metric"><div class="label">Unique reviews analysed</div>'
        f'<div class="metricnum" id="metricReviews">{fmt(filtered_count)}</div>'
        f'<div class="hint" id="metricReviewHint">{fmt(date_rows_count)} matching rows · {fmt(dup_removed)} duplicate rows removed</div></div>'
        f'<div class="metric"><div class="label">Candidate themes</div>'
        f'<div class="metricnum" id="metricThemes">5</div>'
        f'<div class="hint">Rule-based grouping · review before use</div></div>'
        f'<div class="metric"><div class="label">Evidence confidence</div>'
        f'<div class="metricnum" style="font-size:23px">Needs review</div>'
        f'<div class="hint">Counts are reproducible; interpretations need human validation.</div></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    # === Review themes panel ===
    st.markdown(
        '<div class="card"><div class="panelhead"><div>'
        '<h2 class="paneltitle">Review themes</h2>'
        '<div style="margin-top:4px;font-size:12px;color:var(--muted);">Select a theme to inspect the underlying customer evidence.</div>'
        f"</div><span class=\"pill\" id=\"themePeriod\">{start_label} – {end_label}</span></div>",
        unsafe_allow_html=True,
    )
    max_count = max([t["count"] for t in themes], default=1)
    cols = st.columns(3)
    for i, t in enumerate(themes):
        with cols[i % 3]:
            pct = round(t["count"] / filtered_count * 1000) / 10 if filtered_count else 0
            bar_w = max(0, min(100, t["count"] / max_count * 100)) if max_count else 0
            is_selected = st.session_state.selected == t["id"]
            sel_cls = " selected" if is_selected else ""
            st.markdown(f'<div class="theme-header">', unsafe_allow_html=True)
            if st.button(t["name"], key=f"theme_{t['id']}", use_container_width=True):
                st.session_state.selected = t["id"]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(
                f'<div class="theme-tile{sel_cls}">'
                f'<div class="tile-top">'
                f'<span class="tile-rank">THEME {i+1}</span>'
                f'<span class="tile-share">{pct}%</span>'
                f"</div>"
                f'<div class="tile-name">{escape(t["name"])}</div>'
                f'<div class="tile-count">{fmt(t["count"])}</div>'
                f'<div class="tile-share">matching reviews</div>'
                f'<div class="tile-bar"><span style="width:{bar_w}%"></span></div>'
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown(
        f'<div class="theme-grid-note small muted" id="themeNote">Theme counts use transparent keyword rules. Treat them as candidate patterns until source reviews are inspected.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)  # close themes card

    # === Investigation grid ===
    st.markdown('<div class="investigation-grid">', unsafe_allow_html=True)

    # Left: Evidence investigation
    st.markdown(
        '<div class="card"><div class="panelhead"><div>'
        '<h2 class="paneltitle">Evidence investigation</h2>'
        '<div style="margin-top:4px;font-size:12px;color:var(--muted);">Source reviews and interpretation guardrails</div>'
        f"</div><span class=\"pill\" id=\"selectedPill\">{fmt(next((t['count'] for t in themes if t['id']==st.session_state.selected),0))} reviews</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="panelbody">', unsafe_allow_html=True)
    t = next((x for x in themes if x["id"] == st.session_state.selected), themes[0])
    st.markdown(f'<div class="detail-eyebrow" id="detailEyebrow">{escape(t["tag"].upper())}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="detail-title" id="detailTitle">{escape(t["name"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="detail-desc" id="detailDesc">{escape(t["desc"])}</p>', unsafe_allow_html=True)

    # Fee breakdown (only for fees theme)
    if t["id"] == "fees":
        buckets = {"complaint": 0, "positive": 0, "mention": 0}
        for r in t["items"]:
            buckets[fee_sentiment(r)] += 1
        st.markdown('<div class="fee-breakdown" id="feeBreakdown">', unsafe_allow_html=True)
        fc = st.columns(3)
        bucket_labels = [("Possible complaints", buckets["complaint"]), ("Positive or low-fee mentions", buckets["positive"]), ("Unclear / mention only", buckets["mention"])]
        for col, (label, val) in zip(fc, bucket_labels):
            with col:
                st.markdown(
                    f'<div class="fee-bucket"><strong>{val}</strong><span>{label}</span></div>',
                    unsafe_allow_html=True,
                )
        st.markdown(
            '<div class="fee-breakdown-note">Preliminary keyword sentiment only. Review each source before treating these groups as findings.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="sectionlabel">Supporting customer reviews</div>', unsafe_allow_html=True)
    quotes = quote_for(t["items"])
    if quotes:
        st.markdown('<div class="quote-list" id="quotes">', unsafe_allow_html=True)
        for r in quotes:
            text = str(r.get("Review") or r.get("Title")).strip()
            if len(text) > 520:
                text = text[:517] + "…"
            stars = "★" * max(0, min(5, int(r.get("Rating") or 0)))
            appver = escape(str(r.get("App version") or "Version unavailable"))
            url = str(r.get("Review URL") or "")
            url_html = f'<a href="{escape(url)}" target="_blank" rel="noopener">Open original review ↗</a>' if url else '<span class="muted small">No source URL in row</span>'
            st.markdown(
                f'<article class="quote">'
                f'<div class="quotehead">'
                f'<span><span class="stars">{stars}</span> · {escape(day(r.get("Date")))}</span>'
                f'<span>{appver}</span>'
                f"</div>"
                f'<p>“{escape(text)}”</p>'
                f'<div style="margin-top:8px">{url_html}</div>'
                f"</article>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div id="quotes"><div class="empty">No review text available for this theme in the selected date range.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sectionlabel">Interpretation guardrails</div>', unsafe_allow_html=True)
    confirms_txt = (
        f"{fmt(t['count'])} unique reviews in the selected window match this theme's keyword rules. "
        "This is a reproducible classification count, not a verified root-cause finding."
    )
    uncertain_txt = (
        "These comments do not by themselves establish which exact charge is misunderstood, whether a charge was incorrect, "
        "or how many customers experienced it."
        if t["id"] == "fees"
        else "A review mentions an issue, but does not establish prevalence among all Groww users or prove root cause."
    )
    for icon, strong_txt, span_txt, amber in [
        ("✓", "What the data confirms", confirms_txt, False),
        ("?", "What remains uncertain", uncertain_txt, True),
        ("→", "Next question to investigate", t["question"], False),
    ]:
        icon_cls = "facticon amberbg" if amber else "facticon"
        st.markdown(
            f'<div class="factrow">'
            f'<div class="{icon_cls}">{escape(icon)}</div>'
            f'<div><strong>{escape(strong_txt)}</strong><span class="small muted">{escape(span_txt)}</span></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)  # close panelbody + card

    # Right: evidence side panel
    st.markdown('<div class="evidence-side">', unsafe_allow_html=True)

    # Official sources
    st.markdown(
        '<div class="card"><div class="panelhead"><h2 class="paneltitle">Official sources</h2>'
        '<span class="pill">Reference</span></div>'
        '<div class="panelbody"><div class="sourcebox">'
        '<a href="https://groww.in/pricing" target="_blank" rel="noopener">Groww pricing page ↗</a>'
        '<a href="https://groww.in/help/payments-%26-withdrawals/payments-charges/what-fees-does-groww-charge--58" target="_blank" rel="noopener">Groww Help: What fees does Groww charge? ↗</a>'
        '<div class="footnote">References only; not proof of an individual customer’s experience. Last checked: 14 October 2026.</div>'
        "</div></div></div>",
        unsafe_allow_html=True,
    )

    # Next actions
    st.markdown(
        '<div class="card"><div class="panelhead"><h2 class="paneltitle">Next actions</h2></div>'
        '<div class="panelbody"><div class="bottomactions">',
        unsafe_allow_html=True,
    )
    col_p, col_a = st.columns(2)
    with col_p:
        if st.button("▤ Prepare weekly pulse", key="btn_pulse", use_container_width=True):
            st.session_state.open_dialog = "pulse"
            st.rerun()
    with col_a:
        if st.button("✧ Draft product actions", key="btn_actions", use_container_width=True):
            st.session_state.open_dialog = "actions"
            st.rerun()
    st.markdown(
        '</div><div class="footnote">Local drafts only. No Google Docs write, Gmail draft or external action is performed.</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    # Evidence quality check
    st.markdown(
        '<div class="card"><div class="panelhead"><h2 class="paneltitle">Evidence quality check</h2></div>'
        '<div class="panelbody">'
        '<div class="checkrow"><span class="checkmark">1</span><div><strong>Inspect independent reviews</strong><div class="small muted">Confirm that similar wording reflects the same customer problem.</div></div></div>'
        '<div class="checkrow"><span class="checkmark">2</span><div><strong>Separate claims from facts</strong><div class="small muted">A complaint is not proof of root cause.</div></div></div>'
        '<div class="checkrow"><span class="checkmark">3</span><div><strong>Check the reporting window</strong><div class="small muted">Use deduplicated reviews in the selected dates.</div></div></div>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)  # close evidence-side
    st.markdown("</div>", unsafe_allow_html=True)  # close investigation-grid

    # Prototype warning
    st.markdown(
        '<div class="warning"><strong>Prototype limitation:</strong> CSV filtering and keyword grouping run in this session. '
        "This is not an AI model or MCP connection. Do not publish fee-specific claims until supported by review evidence and current official documentation.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)  # close soapbox-main
    st.markdown("</div>", unsafe_allow_html=True)  # close soapbox-page

# ---------------------------------------------------------------------------
# Dialogs (weekly pulse / product actions)
# ---------------------------------------------------------------------------
@st.dialog("Weekly pulse draft")
def _dialog_pulse():
    st.markdown('<p class="muted small">Generated from the current filtered review set. Check every claim before sharing.</p>', unsafe_allow_html=True)
    text = make_pulse(start_s, end_s, filtered_count, themes)
    st.code(text, language=None)
    st.download_button("Download .txt", data=text.encode("utf-8"), file_name="soapbox_weekly_pulse.txt", mime="text/plain", key="dl_pulse", use_container_width=True)
    if st.button("Close", key="close_pulse", use_container_width=True):
        st.session_state.open_dialog = None
        st.rerun()


@st.dialog("Product actions draft")
def _dialog_actions():
    st.markdown('<p class="muted small">These are investigation hypotheses, not approved product decisions.</p>', unsafe_allow_html=True)
    text = make_actions(start_s, end_s, themes)
    st.code(text, language=None)
    st.download_button("Download .txt", data=text.encode("utf-8"), file_name="soapbox_product_actions.txt", mime="text/plain", key="dl_actions", use_container_width=True)
    if st.button("Close", key="close_actions", use_container_width=True):
        st.session_state.open_dialog = None
        st.rerun()


if st.session_state.get("open_dialog") == "pulse":
    _dialog_pulse()
elif st.session_state.get("open_dialog") == "actions":
    _dialog_actions()

# ---------------------------------------------------------------------------
# Non-dashboard navigation stubs
# ---------------------------------------------------------------------------
if active_view == "inbox":
    st.title("Review Inbox")
    st.info("Coming soon: raw review inbox view. Investigation Room is the active dashboard.")
elif active_view == "pulse":
    st.title("Weekly Pulse")
    st.info("Use ▤ Prepare weekly pulse in the Investigation Room to generate a pulse draft.")
elif active_view == "outputs":
    st.title("Approved Outputs")
    st.info("Coming soon: approved product-action outputs.")
