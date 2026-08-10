"""Visual theme: aurora-glass dark UI, plus small HTML building blocks."""
import html

import streamlit as st

# Bright, high-contrast accents that read well on a deep background.
CATEGORY_COLORS = {
    "📸 Sightseeing": "#ff6b8b",
    "🍜 Food": "#ffb457",
    "☕ R&R": "#4ade80",
    "🛍️ Shopping": "#c084fc",
    "🚶 Exploration": "#38dbff",
    "🚗 Transport": "#94a3c8",
    "🏨 Lodging": "#f472b6",
}

DAY_COLORS = ["#7c6cff", "#38dbff", "#ffb457", "#ff6b8b", "#4ade80",
              "#c084fc", "#f472b6", "#22d3ee", "#fbbf24", "#a3e635"]

PRIORITY_STYLES = {
    "🔥 Must Do": ("#ff6b8b", "rgba(255,107,139,.16)"),
    "👍 Would Like": ("#38dbff", "rgba(56,219,255,.14)"),
    "🤷 Optional": ("#94a3c8", "rgba(148,163,200,.14)"),
}


def day_color(day_index):
    return DAY_COLORS[day_index % len(DAY_COLORS)]


def esc(value):
    return html.escape(str(value if value is not None else ""))


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

:root {
    --bg-0: #05070f;
    --bg-1: #0a0f20;
    --text: #eaf0ff;
    --muted: #9aa6c9;
    --glass: rgba(255,255,255,0.055);
    --glass-strong: rgba(255,255,255,0.085);
    --hairline: rgba(255,255,255,0.11);
    --violet: #7c6cff;
    --cyan: #38dbff;
    --pink: #ff6b8b;
    --radius: 22px;
}

/* ---------- page canvas with aurora blooms ---------- */
.stApp {
    background:
        radial-gradient(900px 520px at 12% -8%, rgba(124,108,255,.30), transparent 60%),
        radial-gradient(760px 460px at 88% 2%, rgba(56,219,255,.20), transparent 62%),
        radial-gradient(700px 600px at 70% 100%, rgba(255,107,139,.16), transparent 60%),
        linear-gradient(180deg, var(--bg-0) 0%, var(--bg-1) 55%, #070c19 100%);
    background-attachment: fixed;
    color: var(--text);
}
.stApp, .stApp p, .stApp span, .stApp label, .stApp li { font-family: 'Inter', sans-serif; }
h1, h2, h3, h4, .tp-display {
    font-family: 'Sora', sans-serif !important;
    letter-spacing: -0.02em;
    color: var(--text);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMain"] .block-container { padding-top: 1.6rem; max-width: 1500px; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(10,15,32,.96), rgba(6,10,22,.99));
    border-right: 1px solid var(--hairline);
    backdrop-filter: blur(20px);
}
[data-testid="stSidebar"] .block-container { padding-top: 1.4rem; }

/* ---------- hero ---------- */
.tp-hero {
    position: relative;
    overflow: hidden;
    border-radius: 28px;
    padding: 2.1rem 2.3rem 1.7rem;
    margin-bottom: 1.4rem;
    background:
        radial-gradient(680px 300px at 88% -30%, rgba(56,219,255,.30), transparent 65%),
        radial-gradient(560px 280px at 4% 120%, rgba(255,107,139,.24), transparent 60%),
        linear-gradient(135deg, rgba(124,108,255,.34), rgba(10,15,32,.66));
    border: 1px solid var(--hairline);
    box-shadow: 0 24px 70px rgba(3,6,18,.62), inset 0 1px 0 rgba(255,255,255,.10);
}
.tp-hero::before {
    content: "";
    position: absolute; inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px);
    background-size: 46px 46px;
    mask-image: radial-gradient(70% 120% at 80% 0%, #000 20%, transparent 75%);
    pointer-events: none;
}
.tp-eyebrow {
    font-size: .72rem; font-weight: 700; letter-spacing: .18em;
    text-transform: uppercase; color: rgba(234,240,255,.62);
}
.tp-hero h1 {
    margin: .3rem 0 .1rem;
    font-size: clamp(1.9rem, 3.4vw, 2.9rem);
    font-weight: 800; line-height: 1.06;
}
.tp-hero-sub { color: rgba(234,240,255,.80); font-size: 1.02rem; }
.tp-chiprow { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.1rem; }
.tp-chip {
    display: inline-flex; align-items: center; gap: .4rem;
    padding: .42rem .85rem; border-radius: 999px;
    background: rgba(255,255,255,.10);
    border: 1px solid rgba(255,255,255,.16);
    font-size: .84rem; font-weight: 600; color: var(--text);
    backdrop-filter: blur(8px);
}
.tp-chip-accent {
    background: linear-gradient(135deg, rgba(124,108,255,.9), rgba(56,219,255,.85));
    border-color: transparent; color: #06091a; font-weight: 700;
}

/* ---------- stat tiles ---------- */
.tp-stat {
    border-radius: 18px; padding: 1rem 1.1rem; height: 100%;
    background: var(--glass); border: 1px solid var(--hairline);
    backdrop-filter: blur(14px);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.07);
}
.tp-stat-label {
    font-size: .74rem; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted); font-weight: 700;
}
.tp-stat-value {
    font-family: 'Sora', sans-serif; font-size: 1.65rem; font-weight: 800;
    margin-top: .3rem; line-height: 1;
}
.tp-stat-foot { font-size: .78rem; color: var(--muted); margin-top: .35rem; }

/* ---------- itinerary / place cards ---------- */
.tp-card {
    position: relative;
    border-radius: var(--radius);
    padding: 1.05rem 1.2rem 1.05rem 1.35rem;
    margin-bottom: .7rem;
    background: var(--glass);
    border: 1px solid var(--hairline);
    backdrop-filter: blur(14px);
    box-shadow: 0 8px 30px rgba(3,6,18,.40), inset 0 1px 0 rgba(255,255,255,.06);
    transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
}
.tp-card:hover {
    transform: translateY(-2px);
    background: var(--glass-strong);
    box-shadow: 0 16px 44px rgba(3,6,18,.55), inset 0 1px 0 rgba(255,255,255,.09);
}
.tp-card::before {
    content: ""; position: absolute; left: 0; top: 14px; bottom: 14px; width: 4px;
    border-radius: 0 4px 4px 0;
    background: linear-gradient(180deg, var(--accent, #7c6cff), transparent);
    box-shadow: 0 0 16px var(--accent, #7c6cff);
}
.tp-card-top {
    display: flex; align-items: center; gap: .55rem; flex-wrap: wrap;
    font-size: .82rem; color: var(--muted);
}
.tp-time {
    font-family: 'Sora', sans-serif; font-weight: 700; font-size: .95rem;
    color: var(--text);
}
.tp-card h4 {
    margin: .4rem 0 .2rem; font-size: 1.18rem; font-weight: 700;
}
.tp-note { color: var(--muted); font-size: .88rem; font-style: italic; }
.tp-pill {
    display: inline-flex; align-items: center; gap: .3rem;
    padding: .2rem .6rem; border-radius: 999px;
    font-size: .74rem; font-weight: 700; letter-spacing: .01em;
}
.tp-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.tp-cost {
    margin-left: auto; font-family: 'Sora', sans-serif; font-weight: 700;
    color: var(--text); font-size: .95rem;
}

/* ---------- day header ---------- */
.tp-dayhead {
    display: flex; align-items: center; gap: .7rem;
    margin: 1.3rem 0 .7rem;
}
.tp-daybadge {
    display: grid; place-items: center;
    width: 42px; height: 42px; border-radius: 14px;
    font-family: 'Sora', sans-serif; font-weight: 800; font-size: 1.05rem;
    color: #06091a;
    box-shadow: 0 6px 20px rgba(0,0,0,.4);
}
.tp-daytitle { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.12rem; }
.tp-daymeta { font-size: .8rem; color: var(--muted); }

/* ---------- section heading ---------- */
.tp-section {
    display: flex; align-items: baseline; gap: .6rem;
    margin: .2rem 0 .9rem;
}
.tp-section h3 { margin: 0; font-size: 1.3rem; font-weight: 700; }
.tp-section span { color: var(--muted); font-size: .86rem; }

/* ---------- empty state ---------- */
.tp-empty {
    border-radius: var(--radius); padding: 2.4rem 1.5rem; text-align: center;
    background: var(--glass); border: 1px dashed var(--hairline);
    color: var(--muted);
}
.tp-empty-icon { font-size: 2.1rem; display: block; margin-bottom: .5rem; }

/* ---------- legend ---------- */
.tp-legend { display: flex; flex-wrap: wrap; gap: .45rem; margin: .5rem 0 .2rem; }
.tp-legend-item {
    display: inline-flex; align-items: center; gap: .4rem;
    padding: .28rem .7rem; border-radius: 999px;
    background: var(--glass); border: 1px solid var(--hairline);
    font-size: .78rem; font-weight: 600; color: var(--text);
}

/* ---------- auth screen ---------- */
.tp-authwrap { max-width: 470px; margin: 3.2rem auto 1rem; text-align: center; }
.tp-authwrap h1 { font-size: 2.5rem; font-weight: 800; margin: .2rem 0 .3rem; }
.tp-authwrap p { color: var(--muted); }
.tp-logo {
    display: inline-grid; place-items: center;
    width: 62px; height: 62px; border-radius: 20px; font-size: 1.9rem;
    background: linear-gradient(135deg, var(--violet), var(--cyan));
    box-shadow: 0 14px 40px rgba(124,108,255,.45);
}
.tp-feature {
    display: flex; align-items: flex-start; gap: .6rem;
    text-align: left; font-size: .88rem; color: var(--muted);
    padding: .35rem 0;
}

/* ---------- Streamlit widget restyle ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: .4rem; background: transparent; border-bottom: 1px solid var(--hairline);
    padding-bottom: .3rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 999px; padding: .5rem 1.15rem; font-weight: 600;
    background: var(--glass); border: 1px solid var(--hairline);
    color: var(--muted);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--violet), var(--cyan)) !important;
    color: #06091a !important; border-color: transparent !important;
    box-shadow: 0 8px 24px rgba(124,108,255,.40);
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

div[data-testid="stForm"], div[data-testid="stExpander"] {
    background: var(--glass); border: 1px solid var(--hairline);
    border-radius: var(--radius); backdrop-filter: blur(14px);
}
div[data-testid="stExpander"] details summary { font-weight: 600; }
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: var(--radius);
}

.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stDateInput input, div[data-baseweb="select"] > div, .stTimeInput [data-baseweb="input"] {
    background: rgba(255,255,255,.055) !important;
    border: 1px solid var(--hairline) !important;
    border-radius: 13px !important;
    color: var(--text) !important;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(124,108,255,.75) !important;
    box-shadow: 0 0 0 3px rgba(124,108,255,.18) !important;
}
label, .stMarkdown label { color: var(--muted) !important; font-weight: 600; font-size: .82rem; }

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: 13px; font-weight: 650; padding: .5rem 1rem;
    white-space: nowrap;
    background: rgba(255,255,255,.07); color: var(--text);
    border: 1px solid var(--hairline); transition: all .16s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
    background: rgba(255,255,255,.13); border-color: rgba(255,255,255,.24);
    transform: translateY(-1px);
}
/* Regular primary buttons report kind="primary"; form submits report
   kind="primaryFormSubmit", so match both. */
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, var(--violet), var(--cyan)) !important;
    color: #06091a !important; border: none !important; font-weight: 750;
    box-shadow: 0 10px 28px rgba(124,108,255,.40);
}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
    box-shadow: 0 14px 36px rgba(124,108,255,.55);
    transform: translateY(-1px);
}

div[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--violet), var(--cyan)) !important;
}
div[data-testid="stProgress"] > div > div { background: rgba(255,255,255,.09) !important; }

div[data-testid="stMetric"] {
    background: var(--glass); border: 1px solid var(--hairline);
    border-radius: 18px; padding: 1rem 1.1rem; backdrop-filter: blur(14px);
}
div[data-testid="stMetricValue"] { font-family: 'Sora', sans-serif; font-weight: 800; }

div[data-testid="stAlert"] { border-radius: 15px; border: 1px solid var(--hairline); }

/* Streamlit draws icons as Material Symbols ligatures. If that icon font is
   unavailable (offline host, blocked CDN) the raw ligature text leaks into the
   layout — "visibility" beside password fields, "upload" beside the uploader
   label. Clipping the glyph box keeps the layout intact either way. */
[data-testid="stIconMaterial"] {
    overflow: hidden;
    max-width: 1.4em;
    max-height: 1.4em;
    line-height: 1.4em;
}
[data-testid="stFileUploaderDropzone"] { border-radius: 15px; }
[data-testid="stFileUploaderDropzone"] button { white-space: nowrap; }
hr, div[data-testid="stDivider"] hr { border-color: var(--hairline); }
div[data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; }
div[data-testid="stDeckGlJsonChart"] {
    border-radius: var(--radius); overflow: hidden;
    border: 1px solid var(--hairline);
    box-shadow: 0 16px 46px rgba(3,6,18,.55);
}
#MainMenu, footer { visibility: hidden; }
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------ blocks


def hero(title, destination, chips):
    chip_html = "".join(
        f'<span class="tp-chip{" tp-chip-accent" if accent else ""}">{esc(text)}</span>'
        for text, accent in chips
    )
    st.markdown(
        f"""
        <div class="tp-hero">
            <div class="tp-eyebrow">Your itinerary</div>
            <h1>{esc(title)}</h1>
            <div class="tp-hero-sub">📍 {esc(destination)}</div>
            <div class="tp-chiprow">{chip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat(label, value, foot=""):
    st.markdown(
        f"""
        <div class="tp-stat">
            <div class="tp-stat-label">{esc(label)}</div>
            <div class="tp-stat-value">{esc(value)}</div>
            <div class="tp-stat-foot">{esc(foot)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title, subtitle=""):
    st.markdown(
        f'<div class="tp-section"><h3>{esc(title)}</h3><span>{esc(subtitle)}</span></div>',
        unsafe_allow_html=True,
    )


def day_header(index, title, meta):
    color = day_color(index)
    st.markdown(
        f"""
        <div class="tp-dayhead">
            <div class="tp-daybadge" style="background: linear-gradient(135deg, {color}, {color}aa);">
                {index + 1}
            </div>
            <div>
                <div class="tp-daytitle">{esc(title)}</div>
                <div class="tp-daymeta">{esc(meta)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def priority_pill(priority):
    color, background = PRIORITY_STYLES.get(priority, ("#94a3c8", "rgba(148,163,200,.14)"))
    return (f'<span class="tp-pill" style="background:{background};color:{color};">'
            f'{esc(priority)}</span>')


def category_pill(category):
    color = CATEGORY_COLORS.get(category, "#94a3c8")
    return (f'<span class="tp-pill" style="background:rgba(255,255,255,.07);color:{color};">'
            f'<span class="tp-dot" style="background:{color};"></span>{esc(category)}</span>')


def place_card(item, accent, time_text="", cost_text=""):
    """Render one itinerary/bucket-list entry as a glass card."""
    top = f'<span class="tp-time">{esc(time_text)}</span>' if time_text else ""
    top += category_pill(item["Category"]) + priority_pill(item["Priority"])
    if cost_text:
        top += f'<span class="tp-cost">{esc(cost_text)}</span>'

    note = (f'<div class="tp-note">{esc(item.get("Notes"))}</div>'
            if item.get("Notes") else "")
    st.markdown(
        f"""
        <div class="tp-card" style="--accent: {accent};">
            <div class="tp-card-top">{top}</div>
            <h4>{esc(item["Place"])}</h4>
            {note}
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon, message):
    st.markdown(
        f'<div class="tp-empty"><span class="tp-empty-icon">{icon}</span>{esc(message)}</div>',
        unsafe_allow_html=True,
    )


def legend(entries):
    items = "".join(
        f'<span class="tp-legend-item"><span class="tp-dot" style="background:{color};">'
        f'</span>{esc(label)}</span>'
        for label, color in entries
    )
    st.markdown(f'<div class="tp-legend">{items}</div>', unsafe_allow_html=True)
