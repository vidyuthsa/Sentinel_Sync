"""
app.py — Sentinel Sync: a predictive command center for high-stakes job
application pipelines.

Run with:  streamlit run app.py

Pages:
  - Pipeline Dashboard : priority-ranked grid + Last-Mile Execution Engine
  - Ingestion Hub       : LLM-powered parsing of raw job text into the pipeline
  - Schedule Engine     : conflict-free interview scheduling
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, date, time as dt_time

import streamlit as st

import currency
from models import Application, PipelineStage, ALL_STAGES, INTERVIEW_STAGES
from priority import (
    sorted_by_priority,
    total_active,
    average_package,
    ghost_meter,
    find_offer_companies,
)
from scheduler import validate_and_schedule
from llm_engine import SentinelLLM
from sample_data import load_sample_applications

DATA_FILE = os.path.join(os.path.dirname(__file__), "sentinel_data.json")

NAV_ITEMS = ["📊 Pipeline Dashboard", "📥 Ingestion Hub", "📅 Schedule Engine"]
NAV_LABELS = ["Pipeline Dashboard", "Ingestion Hub", "Schedule Engine"]

CARD_BACKGROUNDS = [
    "#151A24", "#1A1722", "#121E1C", "#1E1A14", "#181421",
    "#141F1A", "#211519", "#14181F", "#1C1A14", "#15201F",
]
CARD_ACCENTS = [
    "#3B82F6", "#A78BFA", "#2DD4BF", "#FBBF24", "#818CF8",
    "#34D399", "#FB7185", "#38BDF8", "#FCD34D", "#6EE7B7",
]

# --------------------------------------------------------------------------- #
# Page config + premium dark theme
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Sentinel Sync",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    /* ── Base ── */
    .stApp { background-color: #0B0F14; color: #E5E7EB; }
    section[data-testid="stSidebar"] {
        background-color: #0F1419;
        border-right: 1px solid #1F2937;
    }
    h1, h2, h3 { color: #F8FAFC; font-weight: 700; letter-spacing: -0.02em; }

    /* ── Metrics ── */
    div[data-testid="stMetric"] {
        background-color: #131A22;
        border: 1px solid #1F2937;
        border-radius: 12px;
        padding: 14px 18px;
    }

    /* ── Utility classes ── */
    .sentinel-badge {
        display: inline-block; padding: 3px 12px; border-radius: 999px;
        font-size: 12px; font-weight: 700; color: #0B0F14; letter-spacing: 0.02em;
    }
    .sentinel-collision {
        background-color: #2A1416; border: 1px solid #EF4444; border-radius: 10px;
        padding: 14px 18px; color: #FCA5A5; font-weight: 600;
    }
    .sentinel-priority {
        font-size: 13px; color: #9CA3AF; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .sentinel-subtle { color: #9CA3AF; font-size: 13px; }

    /* ── Default button style ── */
    div.stButton > button {
        border-radius: 8px; border: 1px solid #2563EB;
        background-color: #1D2B45; color: #DBEAFE; font-weight: 600;
    }
    div.stButton > button:hover { background-color: #2563EB; color: white; }

    /* ══════════════════════════════════════════════════
       ELEGANT NAVIGATION BAR
       A frosted-glass pill container with animated
       active-tab indicator, no ugly button outlines.
    ══════════════════════════════════════════════════ */
    .nav-wrapper {
        display: flex;
        justify-content: center;
        margin: 0 auto 32px auto;
        max-width: 560px;
    }
    .nav-pill-track {
        display: flex;
        align-items: center;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 999px;
        padding: 5px 6px;
        gap: 2px;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    }
    .nav-btn {
        /* Reset Streamlit button styles completely */
        all: unset !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        padding: 8px 20px !important;
        border-radius: 999px !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        color: #9CA3AF !important;
        transition: color 0.2s ease, background 0.2s ease !important;
        white-space: nowrap !important;
        user-select: none !important;
        line-height: 1 !important;
    }
    .nav-btn:hover {
        color: #E5E7EB !important;
        background: rgba(255,255,255,0.06) !important;
    }
    .nav-btn.active {
        background: linear-gradient(135deg, #2563EB 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 12px rgba(59,130,246,0.45), 0 1px 0 rgba(255,255,255,0.15) inset !important;
    }
    .nav-btn .nav-icon {
        font-size: 15px;
        line-height: 1;
    }

    /* ── Streamlit native button override ONLY inside .st-key-navbar ── */
    .st-key-navbar button {
        all: unset !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        padding: 8px 22px !important;
        border-radius: 999px !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        color: #9CA3AF !important;
        transition: color 0.18s, background 0.18s !important;
        white-space: nowrap !important;
        line-height: 1 !important;
    }
    .st-key-navbar button:hover {
        color: #E5E7EB !important;
        background: rgba(255,255,255,0.06) !important;
    }
    .st-key-navbar button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 12px rgba(59,130,246,0.45) !important;
    }
    .st-key-navbar button[data-testid="stBaseButton-secondary"] {
        background: transparent !important;
        border: none !important;
    }

    /* Wrap the whole navbar container in the track style */
    .st-key-navbar > div > div {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 999px !important;
        padding: 5px 6px !important;
        gap: 2px !important;
        backdrop-filter: blur(12px) !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05) !important;
    }

    /* Hide the default column gap spacers inside navbar */
    .st-key-navbar [data-testid="column"] {
        padding: 0 !important;
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Session state initialization
# --------------------------------------------------------------------------- #
def init_state():
    if "applications" not in st.session_state:
        st.session_state.applications = load_sample_applications()
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = (
            "Python, JavaScript, React, Node.js, SQL, REST APIs, Docker, AWS, "
            "Git, data structures & algorithms, system design fundamentals."
        )
    if "llm" not in st.session_state:
        st.session_state.llm = SentinelLLM()
    if "last_parsed" not in st.session_state:
        st.session_state.last_parsed = None
    if "schedule_suggestion" not in st.session_state:
        st.session_state.schedule_suggestion = None
    if "page" not in st.session_state:
        st.session_state.page = NAV_ITEMS[0]


init_state()
apps: list[Application] = st.session_state.applications
llm: SentinelLLM = st.session_state.llm


def get_app(app_id: str) -> Application | None:
    return next((a for a in apps if a.id == app_id), None)


def save_to_disk():
    with open(DATA_FILE, "w") as f:
        json.dump([a.to_dict() for a in apps], f, indent=2)


def load_from_disk():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            raw = json.load(f)
        st.session_state.applications = [Application.from_dict(d) for d in raw]


def badge(stage: PipelineStage) -> str:
    from models import STAGE_BADGE_COLORS
    color = STAGE_BADGE_COLORS.get(stage, "#6B7280")
    return f'<span class="sentinel-badge" style="background-color:{color};">{stage.value}</span>'


def card_colors(company: str) -> tuple[str, str]:
    h = int(hashlib.md5(company.strip().lower().encode()).hexdigest(), 16)
    idx = h % len(CARD_BACKGROUNDS)
    return CARD_BACKGROUNDS[idx], CARD_ACCENTS[idx]


def fmt(amount: float, app_currency: str) -> str:
    return currency.format_amount(amount, app_currency, st.session_state.display_unit_label)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.markdown("## 🛰️ Sentinel Sync")
st.sidebar.caption("Predictive command center for your application pipeline")

# ── OpenAI API Key + Model selector ──────────────────────────────────────────
st.sidebar.markdown("#### 🔑 AI Configuration")

user_api_key = st.sidebar.text_input(
    "OpenAI API Key",
    value=st.session_state.get("user_api_key", ""),
    type="password",
    placeholder="sk-...",
    help="Paste your OpenAI API key here. It stays in your session only — never stored to disk.",
)

MODEL_OPTIONS = [
    # Groq (free, fast)
    "groq/llama-3.3-70b-versatile",
    "groq/llama-3.1-8b-instant",
    "groq/mixtral-8x7b-32768",
    # Gemini (free tier)
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    # OpenAI (paid)
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-3.5-turbo",
]

PROVIDER_URLS = {
    "groq/":    "https://api.groq.com/openai/v1",
    "gemini":   "https://generativelanguage.googleapis.com/v1beta/openai/",
    "gpt":      "",  # OpenAI default, no base_url needed
}

def _default_base_url(model: str) -> str:
    for prefix, url in PROVIDER_URLS.items():
        if model.startswith(prefix):
            return url
    return ""

def _real_model_name(model: str) -> str:
    """Strip the provider prefix we added for display (groq/llama... -> llama...)."""
    if model.startswith("groq/"):
        return model[len("groq/"):]
    return model

selected_model = st.sidebar.selectbox(
    "Model",
    MODEL_OPTIONS,
    index=MODEL_OPTIONS.index(st.session_state.get("selected_model", "groq/llama-3.3-70b-versatile")),
)

auto_base_url = _default_base_url(selected_model)
user_base_url = st.sidebar.text_input(
    "Base URL (auto-filled)",
    value=auto_base_url,
    disabled=True,
    help="Set automatically based on the selected model.",
)
user_base_url = auto_base_url  # always use the auto value

# Rebuild LLM client if key, model, or base_url changed
key_changed = user_api_key != st.session_state.get("user_api_key", "")
model_changed = selected_model != st.session_state.get("selected_model", "groq/llama-3.3-70b-versatile")
url_changed = user_base_url != st.session_state.get("user_base_url", "")

if key_changed or model_changed or url_changed:
    st.session_state.user_api_key = user_api_key
    st.session_state.selected_model = selected_model
    st.session_state.user_base_url = user_base_url
    st.session_state.llm = SentinelLLM(
        api_key=user_api_key.strip() or None,
        base_url=user_base_url.strip() or None,
        model=_real_model_name(selected_model),
    )
    st.session_state.pop("connection_status", None)
    llm = st.session_state.llm
    st.rerun()

llm = st.session_state.llm

# Test Connection button — makes a real cheap API call to surface the actual error
if st.sidebar.button("🔌 Test Connection", use_container_width=True):
    if not llm.is_live:
        st.session_state.connection_status = (False, llm.last_error or "No API key / client not initialized.")
    else:
        with st.spinner("Testing..."):
            ok, msg = llm.test_connection()
        st.session_state.connection_status = (ok, msg)

# Show connection status
conn = st.session_state.get("connection_status")
if conn:
    ok, msg = conn
    if ok:
        st.sidebar.success(f"✅ {msg}", icon=None)
    else:
        st.sidebar.error(f"❌ {msg}", icon=None)
elif llm.is_live:
    st.sidebar.success("✅ LLM engine: connected", icon=None)
    st.sidebar.caption("Click **Test Connection** to verify your key works.")
else:
    st.sidebar.warning("⚠️ Offline fallback mode", icon=None)
    if not user_api_key.strip():
        provider = "Groq" if selected_model.startswith("groq/") else ("Gemini" if selected_model.startswith("gemini") else "OpenAI")
        st.sidebar.caption(f"Enter your **{provider}** API key above to enable live AI.")
    elif llm.last_error:
        st.sidebar.caption(f"Error: {llm.last_error}")

st.sidebar.divider()

# ── Display currency ──────────────────────────────────────────────────────────
st.session_state.display_unit_label = st.sidebar.selectbox(
    "Display package as",
    options=currency.DISPLAY_UNIT_OPTIONS,
    index=currency.DISPLAY_UNIT_OPTIONS.index(
        st.session_state.get("display_unit_label", "Native Currency")
    ),
)
st.sidebar.caption(
    "Ranking math always compares offers on a normalized USD-equivalent "
    "basis — this dropdown only changes how figures are *displayed*."
)

st.sidebar.divider()
col_a, col_b = st.sidebar.columns(2)
if col_a.button("💾 Save", use_container_width=True):
    save_to_disk()
    st.sidebar.success("Saved.")
if col_b.button("📂 Load", use_container_width=True):
    load_from_disk()
    st.rerun()


# --------------------------------------------------------------------------- #
# Elegant top navigation bar
# --------------------------------------------------------------------------- #
with st.container(key="navbar"):
    # Three equal-width columns, no side spacers, so the CSS pill-track wraps tight
    c1, c2, c3 = st.columns(3, gap="small")
    for col, item in zip([c1, c2, c3], NAV_ITEMS):
        is_active = st.session_state.page == item
        if col.button(
            item,
            key=f"nav_{item}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.page = item
            st.rerun()

page = st.session_state.page


# --------------------------------------------------------------------------- #
# PAGE: Pipeline Dashboard
# --------------------------------------------------------------------------- #
if page == "📊 Pipeline Dashboard":
    st.title("Pipeline Dashboard ↗")
    st.caption(
        "Sorted by Dynamic Priority Score = Package Value × Approval Probability"
    )

    gm = ghost_meter(apps)
    m1, m2, m3 = st.columns(3)
    m1.metric("Active Applications", total_active(apps))
    m2.metric("Average Package Value", fmt(average_package(apps), "USD"))
    m3.metric(
        "Ghost-Meter (At Risk)",
        gm["total_at_risk"],
        delta=f"↑ {gm['ghosted']} ghosted · {gm['going_cold']} cold",
        delta_color="inverse",
    )

    st.divider()

    offers = find_offer_companies(apps)
    ranked = sorted_by_priority(apps)

    if not ranked:
        st.info("No applications yet. Add one from the Ingestion Hub.")

    card_css_rules = []
    for application in ranked:
        bg, accent = card_colors(application.company)
        card_css_rules.append(
            f'.st-key-card_{application.id} {{ '
            f'background-color:{bg} !important; '
            f'border:1px solid {accent}33 !important; '
            f'border-left:4px solid {accent} !important; '
            f'border-radius:14px !important; '
            f'padding:18px 20px 6px 20px !important; '
            f'margin-bottom:14px !important; }}'
        )
    st.markdown(f"<style>{''.join(card_css_rules)}</style>", unsafe_allow_html=True)

    for application in ranked:
        with st.container(key=f"card_{application.id}"):
            top_l, top_r = st.columns([3, 1])
            with top_l:
                st.markdown(
                    f"### {application.company} — {application.title}",
                    help=application.notes or None,
                )
                st.markdown(badge(application.stage), unsafe_allow_html=True)
            with top_r:
                st.markdown(
                    f'<div class="sentinel-priority">Priority Score</div>'
                    f'<div style="font-size:26px;font-weight:800;color:#F8FAFC;">'
                    f'{application.priority_score:,.0f}</div>',
                    unsafe_allow_html=True,
                )

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(
                f'<span class="sentinel-subtle">Package</span><br>'
                f'<b>{fmt(application.salary, application.currency)}</b>',
                unsafe_allow_html=True,
            )
            c2.markdown(
                f'<span class="sentinel-subtle">Approval Probability</span><br>'
                f'<b>{application.match_score:.1f}%</b>',
                unsafe_allow_html=True,
            )
            c3.markdown(
                f'<span class="sentinel-subtle">Last Interaction</span><br>'
                f'<b>{application.last_interaction_date.isoformat()} '
                f'({application.days_since_contact}d ago)</b>',
                unsafe_allow_html=True,
            )
            interview_str = (
                application.interview_datetime.strftime("%b %d, %Y · %I:%M %p")
                if application.interview_datetime
                else "Not scheduled"
            )
            c4.markdown(
                f'<span class="sentinel-subtle">Interview</span><br><b>{interview_str}</b>',
                unsafe_allow_html=True,
            )

            with st.expander("Manage & take action"):
                mc1, mc2, mc3 = st.columns([2, 1, 1])
                new_stage = mc1.selectbox(
                    "Pipeline stage",
                    ALL_STAGES,
                    index=ALL_STAGES.index(application.stage.value),
                    key=f"stage_{application.id}",
                )
                if new_stage != application.stage.value:
                    application.stage = PipelineStage(new_stage)
                    application.last_interaction_date = date.today()
                    st.rerun()

                new_currency = mc2.selectbox(
                    "Currency",
                    currency.SUPPORTED_CURRENCIES,
                    index=currency.SUPPORTED_CURRENCIES.index(application.currency),
                    key=f"currency_{application.id}",
                )
                if new_currency != application.currency:
                    application.currency = new_currency
                    st.rerun()

                if mc3.button("🗑️ Remove", key=f"del_{application.id}"):
                    st.session_state.applications = [a for a in apps if a.id != application.id]
                    st.rerun()

                sc1, sc2 = st.columns(2)
                new_salary = sc1.number_input(
                    f"Package amount ({application.currency})",
                    min_value=0.0,
                    value=float(application.salary),
                    step=1000.0,
                    key=f"salary_{application.id}",
                )
                if new_salary != application.salary:
                    application.salary = new_salary
                    st.rerun()

                new_match = sc2.number_input(
                    "Match %", min_value=0.0, max_value=100.0,
                    value=application.match_score, step=1.0,
                    key=f"match_{application.id}",
                )
                if new_match != application.match_score:
                    application.match_score = new_match
                    st.rerun()

                st.markdown("---")
                st.markdown("**Last-Mile Execution Engine**")

                # Trigger 1: Technical Interview -> Blitz Prep Sheet
                if application.stage == PipelineStage.TECHNICAL_INTERVIEW:
                    if st.button("⚡ Generate 30-Minute Blitz Prep Sheet", key=f"blitz_{application.id}"):
                        with st.spinner("Building prep sheet..."):
                            sheet = llm.generate_blitz_prep(application.company, application.title)
                        st.session_state[f"blitz_out_{application.id}"] = sheet
                        if llm.last_error:
                            st.session_state[f"blitz_err_{application.id}"] = llm.last_error
                        else:
                            st.session_state.pop(f"blitz_err_{application.id}", None)
                    if st.session_state.get(f"blitz_err_{application.id}"):
                        st.warning(f"⚠️ LLM call failed — showing offline fallback.\n\n**Error:** `{st.session_state[f'blitz_err_{application.id}']}`")
                    if st.session_state.get(f"blitz_out_{application.id}"):
                        st.code(st.session_state[f"blitz_out_{application.id}"], language=None)

                # Trigger 2: Ghosted / going cold -> follow-up message
                if application.stage == PipelineStage.GHOSTED or application.is_ghosted_candidate:
                    platform = st.selectbox(
                        "Follow-up tone",
                        ["LinkedIn", "WhatsApp", "Gmail"],
                        key=f"platform_{application.id}",
                    )
                    if st.button("✉️ Generate Follow-Up Message", key=f"followup_{application.id}"):
                        with st.spinner("Drafting follow-up..."):
                            msg = llm.generate_followup_message(
                                application.company, application.title,
                                platform, application.days_since_contact,
                            )
                        st.session_state[f"followup_out_{application.id}"] = msg
                        if llm.last_error:
                            st.session_state[f"followup_err_{application.id}"] = llm.last_error
                        else:
                            st.session_state.pop(f"followup_err_{application.id}", None)
                    if st.session_state.get(f"followup_err_{application.id}"):
                        st.warning(f"⚠️ LLM call failed — showing offline fallback.\n\n**Error:** `{st.session_state[f'followup_err_{application.id}']}`")
                    if st.session_state.get(f"followup_out_{application.id}"):
                        st.code(st.session_state[f"followup_out_{application.id}"], language=None)

                # Trigger 3: mid-stage company while another has an Offer -> leverage email
                if application.stage in INTERVIEW_STAGES and offers:
                    best_offer = max(offers, key=lambda a: a.salary_usd_equivalent)
                    if st.button(
                        f"🎯 Generate Counter-Offer Leverage Email (vs. {best_offer.company} offer)",
                        key=f"counter_{application.id}",
                    ):
                        with st.spinner("Drafting leverage email..."):
                            email = llm.generate_counteroffer_email(
                                application.company, application.title,
                                best_offer.salary_usd_equivalent,
                            )
                        st.session_state[f"counter_out_{application.id}"] = email
                        if llm.last_error:
                            st.session_state[f"counter_err_{application.id}"] = llm.last_error
                        else:
                            st.session_state.pop(f"counter_err_{application.id}", None)
                    if st.session_state.get(f"counter_err_{application.id}"):
                        st.warning(f"⚠️ LLM call failed — showing offline fallback.\n\n**Error:** `{st.session_state[f'counter_err_{application.id}']}`")
                    if st.session_state.get(f"counter_out_{application.id}"):
                        st.code(st.session_state[f"counter_out_{application.id}"], language=None)

                if (
                    application.stage != PipelineStage.TECHNICAL_INTERVIEW
                    and application.stage != PipelineStage.GHOSTED
                    and not application.is_ghosted_candidate
                    and not (application.stage in INTERVIEW_STAGES and offers)
                ):
                    st.caption("No execution triggers active for this application right now.")


# --------------------------------------------------------------------------- #
# PAGE: Ingestion Hub
# --------------------------------------------------------------------------- #
elif page == "📥 Ingestion Hub":
    st.title("Ingestion Hub")
    st.caption(
        "Paste a job description, confirmation email, or log snippet — Sentinel Sync "
        "extracts and scores it, detecting whichever currency it was written in "
        "(₹/Rs/INR/LPA, $/USD, €/EUR, £/GBP)."
    )

    if not llm.is_live:
        st.info(
            "💡 **Offline fallback mode** — results use keyword-overlap matching. "
            "Enter your OpenAI API key in the sidebar for live AI parsing.",
            icon=None,
        )

    st.session_state.resume_text = st.text_area(
        "Your resume / skills snippet (used for Approval Probability matching)",
        value=st.session_state.resume_text,
        height=110,
    )

    raw_text = st.text_area(
        "Raw text to ingest",
        height=200,
        placeholder=(
            "e.g. \"Thank you for applying to the Senior Backend Engineer role at "
            "Northwind Systems. Package: 18 LPA...\" or \"...compensation range: "
            "$150,000 - $180,000...\""
        ),
    )

    if st.button("🔍 Parse & Add to Pipeline", type="primary"):
        if not raw_text.strip():
            st.error("Paste some text first.")
        else:
            with st.spinner("Parsing with Sentinel AI..."):
                parsed = llm.parse_job_posting(raw_text, st.session_state.resume_text)
            st.session_state.last_parsed = parsed
            new_app = Application(
                company=parsed["company"],
                title=parsed["title"],
                salary=parsed["salary"],
                currency=parsed.get("currency", "USD"),
                match_score=parsed["match_score"],
                stage=PipelineStage.APPLIED,
            )
            st.session_state.applications.append(new_app)
            st.success(f"Added **{new_app.company} — {new_app.title}** to the pipeline.")

    if st.session_state.last_parsed:
        p = st.session_state.last_parsed
        st.markdown("#### Last parse result")
        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.metric("Company", p["company"])
        lc2.metric("Detected Currency", p.get("currency", "USD"))
        lc3.metric("Package", fmt(p["salary"], p.get("currency", "USD")))
        lc4.metric("Approval Probability", f"{p['match_score']:.1f}%")
        if p.get("rationale"):
            st.caption(p["rationale"])


# --------------------------------------------------------------------------- #
# PAGE: Schedule Engine
# --------------------------------------------------------------------------- #
elif page == "📅 Schedule Engine":
    st.title("Schedule Engine")
    st.caption("Add or update interview times — collisions within a 2-hour window are flagged automatically.")

    if not apps:
        st.info("No applications yet.")
    else:
        options = {f"{a.company} — {a.title}": a.id for a in apps}
        selected_label = st.selectbox("Application", list(options.keys()))
        selected_id = options[selected_label]
        selected_app = get_app(selected_id)

        default_date = (
            selected_app.interview_datetime.date()
            if selected_app.interview_datetime
            else date.today()
        )
        default_time = (
            selected_app.interview_datetime.time()
            if selected_app.interview_datetime
            else dt_time(10, 0)
        )

        dcol, tcol = st.columns(2)
        new_date = dcol.date_input("Interview date", value=default_date)
        new_time = tcol.time_input("Interview time", value=default_time)
        candidate_dt = datetime.combine(new_date, new_time)

        if st.button("📌 Validate & Schedule", type="primary"):
            is_clear, conflict, suggestion = validate_and_schedule(
                candidate_dt, apps, exclude_id=selected_id
            )
            st.session_state.pop("reschedule_out", None)
            st.session_state.pop("reschedule_err", None)
            st.session_state.pop("reschedule_target", None)
            if is_clear:
                selected_app.interview_datetime = candidate_dt
                if selected_app.stage == PipelineStage.APPLIED:
                    selected_app.stage = PipelineStage.APTITUDE_TEST
                selected_app.last_interaction_date = date.today()
                st.session_state.schedule_suggestion = None
                st.success(
                    f"Scheduled {selected_app.company} for "
                    f"{candidate_dt.strftime('%b %d, %Y · %I:%M %p')}."
                )
            else:
                st.session_state.schedule_suggestion = {
                    "app_id": selected_id,
                    "candidate": candidate_dt,
                    "conflict": conflict,
                    "suggestion": suggestion,
                }

        sug = st.session_state.schedule_suggestion
        if sug and sug["app_id"] == selected_id:
            st.markdown(
                f'<div class="sentinel-collision">⚠️ Scheduling Collision Detected! '
                f'This slot is within 2 hours of your interview with '
                f'<b>{sug["conflict"].company}</b> at '
                f'{sug["conflict"].interview_datetime.strftime("%b %d, %Y · %I:%M %p")}.</div>',
                unsafe_allow_html=True,
            )
            st.write(
                f"**Next available slot:** "
                f"{sug['suggestion'].strftime('%b %d, %Y · %I:%M %p')}"
            )

            col_accept, col_reschedule = st.columns(2)

            with col_accept:
                if st.button("✅ Accept suggested slot", use_container_width=True):
                    app_to_update = get_app(sug["app_id"])
                    app_to_update.interview_datetime = sug["suggestion"]
                    if app_to_update.stage == PipelineStage.APPLIED:
                        app_to_update.stage = PipelineStage.APTITUDE_TEST
                    app_to_update.last_interaction_date = date.today()
                    st.session_state.schedule_suggestion = None
                    st.session_state.pop("reschedule_out", None)
                    st.session_state.pop("reschedule_err", None)
                    st.session_state.pop("reschedule_target", None)
                    st.rerun()

            # The two colliding applications: the one being scheduled now,
            # and the existing one it collides with. Whichever has the
            # LOWER Dynamic Priority Score is the one we ask to move.
            candidate_app = get_app(sug["app_id"])
            conflict_app = sug["conflict"]
            lower_app, higher_app = (
                (candidate_app, conflict_app)
                if candidate_app.priority_score <= conflict_app.priority_score
                else (conflict_app, candidate_app)
            )

            with col_reschedule:
                if st.button(
                    f"✉️ Request Reschedule with {lower_app.company}",
                    use_container_width=True,
                    help=(
                        f"{lower_app.company} has the lower Priority Score "
                        f"({lower_app.priority_score:,.0f} vs. "
                        f"{higher_app.priority_score:,.0f}) — drafts a reschedule "
                        f"request for that interview instead."
                    ),
                ):
                    # The "original" slot we're asking to move is whichever
                    # datetime the lower-priority app currently holds: its
                    # already-scheduled time if it has one, otherwise the
                    # candidate slot just entered for it.
                    original_dt = (
                        lower_app.interview_datetime
                        if lower_app.interview_datetime
                        else sug["candidate"]
                    )
                    with st.spinner("Drafting reschedule request..."):
                        email = llm.generate_reschedule_request(
                            lower_app.company,
                            lower_app.title,
                            original_dt.strftime("%b %d, %Y · %I:%M %p"),
                        )
                    st.session_state["reschedule_out"] = email
                    st.session_state["reschedule_target"] = lower_app.company
                    if llm.last_error:
                        st.session_state["reschedule_err"] = llm.last_error
                    else:
                        st.session_state.pop("reschedule_err", None)

            if st.session_state.get("reschedule_err"):
                st.warning(
                    f"⚠️ LLM call failed — showing offline fallback.\n\n"
                    f"**Error:** `{st.session_state['reschedule_err']}`"
                )
            if st.session_state.get("reschedule_out"):
                st.caption(f"Draft to send to **{st.session_state['reschedule_target']}**:")
                st.code(st.session_state["reschedule_out"], language=None)

        st.divider()
        st.markdown("#### Upcoming interviews")
        scheduled = sorted(
            (a for a in apps if a.interview_datetime is not None),
            key=lambda a: a.interview_datetime,
        )
        if not scheduled:
            st.caption("No interviews scheduled yet.")
        for a in scheduled:
            st.markdown(
                f"- **{a.company}** ({a.title}) — "
                f"{a.interview_datetime.strftime('%b %d, %Y · %I:%M %p')} "
                f"&nbsp;{badge(a.stage)}",
                unsafe_allow_html=True,
            )
