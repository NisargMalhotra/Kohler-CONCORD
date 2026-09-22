"""
KOHLER CONCORD — Visual Theme Layer.

Injects custom CSS for the enterprise-grade look: dark navy sidebar,
brass/gold accents, Inter font, styled chat bubbles, cards, badges.
All functions are presentation-only — no backend logic.
"""

from __future__ import annotations

import streamlit as st


# ── CSS Variables & Theme ─────────────────────────────────────────────────────

_MAIN_CSS = """
<style>
/* ── Google Font ──────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── CSS Custom Properties ────────────────────────────────────── */
:root {
    --kc-navy:        #0F1B2D;
    --kc-navy-light:  #1A2942;
    --kc-gold:        #C4A469;
    --kc-gold-light:  #D4B87A;
    --kc-gold-dim:    rgba(196,164,105,0.15);
    --kc-bg:          #F7F8FA;
    --kc-surface:     #FFFFFF;
    --kc-text:        #1A1A2E;
    --kc-text-sec:    #5A6478;
    --kc-border:      #E2E8F0;
    --kc-success:     #10B981;
    --kc-warning:     #F59E0B;
    --kc-error:       #EF4444;
    --kc-info:        #3B82F6;
    --kc-radius:      10px;
    --kc-shadow:      0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --kc-shadow-md:   0 4px 12px rgba(0,0,0,0.08);
    --kc-shadow-lg:   0 8px 32px rgba(0,0,0,0.12);
}

/* ── Global ───────────────────────────────────────────────────── */
html, body, [class*="css"], .stMarkdown, .stText {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
.stApp {
    background: var(--kc-bg);
}

/* Hide default Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ── Sidebar ──────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--kc-navy) 0%, #0D1622 100%) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    color: #E8ECF1 !important;
}
[data-testid="stSidebar"] strong {
    color: var(--kc-gold) !important;
}
[data-testid="stSidebar"] .stCaption p {
    color: rgba(255,255,255,0.45) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.08) !important;
}
[data-testid="stSidebar"] label {
    color: rgba(255,255,255,0.7) !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    font-weight: 600 !important;
}
/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    background: var(--kc-gold-dim) !important;
    color: var(--kc-gold) !important;
    border: 1px solid rgba(196,164,105,0.25) !important;
    border-radius: var(--kc-radius) !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(196,164,105,0.28) !important;
    border-color: var(--kc-gold) !important;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(196,164,105,0.2) !important;
}
/* Sidebar selectbox & text input */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.06) !important;
    border-color: rgba(255,255,255,0.12) !important;
    color: #E8ECF1 !important;
    border-radius: var(--kc-radius) !important;
}
[data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.06) !important;
    border-color: rgba(255,255,255,0.12) !important;
    color: #E8ECF1 !important;
    border-radius: var(--kc-radius) !important;
}
/* Sidebar metrics */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: var(--kc-radius) !important;
    padding: 10px 12px !important;
}
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: var(--kc-gold) !important;
    font-size: 18px !important;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] p {
    color: rgba(255,255,255,0.55) !important;
    font-size: 11px !important;
}

/* ── Primary buttons ──────────────────────────────────────────── */
button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--kc-gold), var(--kc-gold-light)) !important;
    color: var(--kc-navy) !important;
    border: none !important;
    border-radius: var(--kc-radius) !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 6px rgba(196,164,105,0.25) !important;
}
button[data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(196,164,105,0.35) !important;
}

/* ── Secondary / default buttons ──────────────────────────────── */
[data-testid="stAppViewContainer"] .stButton > button {
    border-radius: var(--kc-radius) !important;
    transition: all 0.15s ease !important;
    font-weight: 500 !important;
}

/* ── Tabs ──────────────────────────────────────────────────────── */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 12px 20px !important;
    border-radius: 10px 10px 0 0 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--kc-navy) !important;
    font-weight: 600 !important;
}
[data-baseweb="tab-highlight"] {
    background-color: var(--kc-gold) !important;
    height: 3px !important;
    border-radius: 3px 3px 0 0 !important;
}

/* ── Chat messages ────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    border-radius: 14px !important;
    padding: 18px 22px !important;
    margin-bottom: 14px !important;
    transition: box-shadow 0.2s ease;
}
/* User messages — subtle indigo tint */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg, #EEF2FF, #E8EDFF) !important;
    border: 1px solid #C7D2FE !important;
}
/* Assistant messages — white card */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: var(--kc-surface) !important;
    border: 1px solid var(--kc-border) !important;
    box-shadow: var(--kc-shadow) !important;
}

/* Chat input */
[data-testid="stChatInput"] textarea {
    border-radius: 14px !important;
    border: 2px solid var(--kc-border) !important;
    padding: 14px 18px !important;
    font-size: 14px !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--kc-gold) !important;
    box-shadow: 0 0 0 3px rgba(196,164,105,0.15) !important;
}

/* ── Metrics ──────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] [data-testid="stMetric"] {
    background: var(--kc-surface) !important;
    padding: 18px 16px !important;
    border-radius: var(--kc-radius) !important;
    border: 1px solid var(--kc-border) !important;
    box-shadow: var(--kc-shadow) !important;
}
[data-testid="stMetricValue"] {
    font-weight: 700 !important;
}

/* ── Expanders ────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--kc-border) !important;
    border-radius: var(--kc-radius) !important;
    background: var(--kc-surface) !important;
    box-shadow: var(--kc-shadow) !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary {
    font-weight: 500 !important;
}

/* ── Status widget ────────────────────────────────────────────── */
[data-testid="stStatus"] {
    border-radius: var(--kc-radius) !important;
    border: 1px solid var(--kc-border) !important;
    background: var(--kc-surface) !important;
}

/* ── Alerts / callouts ────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--kc-radius) !important;
    font-size: 14px !important;
}

/* ── Download button ──────────────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
    border-radius: var(--kc-radius) !important;
    border: 1.5px solid var(--kc-gold) !important;
    color: var(--kc-gold) !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: var(--kc-gold-dim) !important;
}

/* ── DataFrames ───────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: var(--kc-radius) !important;
    overflow: hidden !important;
    border: 1px solid var(--kc-border) !important;
}

/* ── Charts ───────────────────────────────────────────────────── */
[data-testid="stVegaLiteChart"] {
    border-radius: var(--kc-radius) !important;
    background: var(--kc-surface) !important;
    padding: 12px !important;
    border: 1px solid var(--kc-border) !important;
    box-shadow: var(--kc-shadow) !important;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar        { width: 6px; height: 6px; }
::-webkit-scrollbar-track  { background: transparent; }
::-webkit-scrollbar-thumb  { background: #CBD5E1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94A3B8; }

/* ── Bordered containers ──────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: var(--kc-radius) !important;
    border-color: var(--kc-border) !important;
}

/* ── Custom component classes ─────────────────────────────────── */

/* Header bar */
.kc-header {
    background: linear-gradient(135deg, var(--kc-navy) 0%, var(--kc-navy-light) 100%);
    padding: 14px 28px;
    border-radius: 0 0 14px 14px;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
}
.kc-header-left {
    display: flex;
    align-items: center;
    gap: 14px;
}
.kc-header-logo {
    display: flex;
    align-items: center;
    gap: 10px;
}
.kc-header-logo img {
    width: 36px;
    height: 36px;
    border-radius: 8px;
}
.kc-header-title {
    font-size: 22px;
    font-weight: 700;
    color: var(--kc-gold);
    letter-spacing: 0.5px;
}
.kc-header-sub {
    font-size: 11px;
    color: rgba(255,255,255,0.5);
    letter-spacing: 0.5px;
}
.kc-role-badge {
    background: rgba(196,164,105,0.18);
    color: var(--kc-gold);
    padding: 7px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid rgba(196,164,105,0.3);
    letter-spacing: 0.3px;
}

/* Login page */
.kc-login-bg {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(135deg, #0F1B2D 0%, #162236 50%, #1A2942 100%);
    z-index: -1;
}
.kc-login-logo {
    text-align: center;
    padding: 32px 0 8px;
}
.kc-login-logo img {
    width: 72px;
    height: 72px;
    border-radius: 16px;
    margin-bottom: 12px;
}
.kc-login-title {
    font-size: 30px;
    font-weight: 700;
    color: var(--kc-navy);
    letter-spacing: 1.5px;
    text-align: center;
}
.kc-login-sub {
    font-size: 14px;
    color: var(--kc-text-sec);
    text-align: center;
    margin-bottom: 20px;
}

/* Confidence badges */
.kc-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    margin: 8px 0;
}
.kc-badge-high {
    background: rgba(16,185,129,0.1);
    color: #059669;
    border: 1px solid rgba(16,185,129,0.25);
}
.kc-badge-med {
    background: rgba(245,158,11,0.1);
    color: #D97706;
    border: 1px solid rgba(245,158,11,0.25);
}
.kc-badge-low {
    background: rgba(239,68,68,0.1);
    color: #DC2626;
    border: 1px solid rgba(239,68,68,0.25);
}

/* Citation cards */
.kc-cite {
    background: #F8FAFC;
    border: 1px solid var(--kc-border);
    border-left: 3px solid var(--kc-gold);
    border-radius: 0 var(--kc-radius) var(--kc-radius) 0;
    padding: 12px 16px;
    margin: 8px 0;
}
.kc-cite-id    { font-weight: 600; color: var(--kc-navy); font-size: 13px; }
.kc-cite-meta  { font-size: 12px; color: var(--kc-text-sec); margin-top: 2px; }
.kc-cite-text  { font-size: 13px; color: var(--kc-text); margin-top: 6px; font-style: italic; line-height: 1.6; }

/* Conflict cards */
.kc-conflict {
    background: rgba(245,158,11,0.05);
    border: 1px solid rgba(245,158,11,0.2);
    border-radius: var(--kc-radius);
    padding: 14px 18px;
    margin: 8px 0;
}
.kc-conflict-hdr  { font-weight: 600; color: #92400E; font-size: 14px; margin-bottom: 4px; }
.kc-conflict-desc { font-size: 13px; color: var(--kc-text); margin: 4px 0; }
.kc-conflict-rec  { font-size: 12px; color: var(--kc-text-sec); margin-top: 6px; }

/* Sidebar section labels */
.kc-section {
    color: var(--kc-gold);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    margin: 12px 0 4px;
    opacity: 0.85;
}

/* Dashboard metric boxes */
.kc-eval-metric {
    text-align: center;
    padding: 4px 0;
}
.kc-eval-metric-val {
    font-size: 32px;
    font-weight: 700;
    color: var(--kc-navy);
}
.kc-eval-metric-lbl {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--kc-text-sec);
    font-weight: 600;
}
</style>
"""

_LOGIN_CSS = """
<style>
.stApp {
    background: linear-gradient(135deg, #0F1B2D 0%, #162236 50%, #1A2942 100%) !important;
}
/* Style the bordered container as a white card */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--kc-surface, #FFFFFF) !important;
    border-radius: 16px !important;
    border: none !important;
    box-shadow: 0 8px 40px rgba(0,0,0,0.25) !important;
    padding: 8px !important;
}
/* Style inputs on login page */
[data-testid="stTextInput"] input {
    border-radius: 10px !important;
}
[data-baseweb="select"] > div {
    border-radius: 10px !important;
}
/* Caption text on login page */
.stCaption p {
    color: rgba(255,255,255,0.5) !important;
}
</style>
"""


def inject_custom_css() -> None:
    """Inject the main theme CSS into the Streamlit app."""
    st.markdown(_MAIN_CSS, unsafe_allow_html=True)


def inject_login_css() -> None:
    """Inject login-page-specific CSS (dark background, card styling)."""
    st.markdown(_MAIN_CSS, unsafe_allow_html=True)  # base styles
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)  # login overrides


def render_header(persona_display_name: str, favicon_path: str = "") -> None:
    """Render the top header bar with logo and role badge."""
    img_tag = ""
    if favicon_path:
        import base64, os
        if os.path.isfile(favicon_path):
            with open(favicon_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            img_tag = f'<img src="data:image/jpeg;base64,{b64}" alt="logo">'

    st.markdown(
        f"""
        <div class="kc-header">
            <div class="kc-header-left">
                <div class="kc-header-logo">
                    {img_tag}
                    <div>
                        <div class="kc-header-title">KOHLER CONCORD</div>
                        <div class="kc-header-sub">Unified Enterprise AI Agent</div>
                    </div>
                </div>
            </div>
            <div class="kc-role-badge">{persona_display_name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
