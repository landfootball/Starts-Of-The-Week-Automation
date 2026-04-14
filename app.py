"""
FantasyLand — Starts of the Week Research Tool
Calm, confident dark interface. Bebas Neue + Barlow Condensed + IBM Plex Mono.
"""

import json
import re
import sys
import tempfile
from pathlib import Path
from io import BytesIO

from PIL import Image
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))

st.set_page_config(
    page_title="FantasyLand · Starts of the Week",
    page_icon="🥒",
    layout="wide",
)

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:ital,wght@0,400;0,600;0,700;0,900;1,700&family=IBM+Plex+Mono:wght@400;700&display=swap');

:root {
    --orange:    #FF3300;
    --blue:      #0033FF;
    --black:     #0A0A0A;
    --white:     #F0EDE8;
    --g1:        #111111;
    --g2:        #1A1A1A;
    --g3:        #252525;
    --g4:        #3A3A3A;
    --g5:        #888888;
    --green:     #00C853;
    --yellow:    #FFD600;
    --red:       #FF1744;
    --sp-xs:     8px;
    --sp-sm:     12px;
    --sp-md:     16px;
    --sp-lg:     24px;
    --sp-xl:     32px;
    --sp-2xl:    48px;
    --page-pad:  40px;
}

/* ── Base ───────────────────────────────────────────────────────────────── */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--black) !important;
    color: var(--white) !important;
}
[data-testid="stHeader"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--g1) !important;
    border-right: 2px solid var(--g2) !important;
}
[data-testid="stSidebar"] .block-container { padding: 32px 24px !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: var(--white) !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio > label {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: var(--g5) !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background-color: var(--g2) !important;
    border: 1px solid var(--g3) !important;
    border-radius: 2px !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    color: var(--white) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label span {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 15px !important;
    font-weight: 600 !important;
}

/* ── Primary button (orange CTA) ─────────────────────────────────────────── */
.stButton > button {
    background-color: var(--orange) !important;
    color: var(--white) !important;
    border: none !important;
    border-radius: 2px !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 12px 24px !important;
    width: 100% !important;
    transition: background 0.12s ease !important;
}
.stButton > button:hover { background-color: #CC2900 !important; }
.stButton > button:disabled {
    background-color: var(--g3) !important;
    color: var(--g4) !important;
}

/* Secondary button (refresh — ghost style via data-testid workaround) */
[data-testid="stSidebar"] .stButton > button.secondary-btn {
    background-color: transparent !important;
    border: 1px solid var(--g3) !important;
    color: var(--g5) !important;
    font-size: 13px !important;
    letter-spacing: 1px !important;
    padding: 8px 16px !important;
}

/* ── Download button ─────────────────────────────────────────────────────── */
.stDownloadButton > button {
    background-color: transparent !important;
    border: 1px solid var(--g3) !important;
    color: var(--g5) !important;
    border-radius: 2px !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
}
.stDownloadButton > button:hover {
    border-color: var(--white) !important;
    color: var(--white) !important;
}

/* ── Tabs ────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    background: var(--g1) !important;
    border-bottom: 1px solid var(--g2) !important;
    gap: 0 !important;
    padding: 0 var(--page-pad) !important;
}
[data-testid="stTabs"] button[role="tab"] {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    color: var(--g4) !important;
    border-radius: 0 !important;
    padding: 16px 24px !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: var(--white) !important;
    border-bottom: 2px solid var(--orange) !important;
    background: transparent !important;
}
[data-testid="stTabs"] [data-testid="stTabContent"] {
    padding: var(--sp-xl) var(--page-pad) !important;
    background: var(--black) !important;
}

/* ── Metrics ─────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--g2) !important;
    padding: var(--sp-md) var(--sp-lg) !important;
    border-top: 2px solid var(--g3) !important;
    border-radius: 2px !important;
}
[data-testid="stMetricLabel"] > div {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    color: var(--g5) !important;
}
[data-testid="stMetricValue"] > div {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 32px !important;
    letter-spacing: 1px !important;
    color: var(--white) !important;
}
[data-testid="stMetricDelta"] svg { display: none !important; }
[data-testid="stMetricDelta"] > div {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    color: var(--g5) !important;
}

/* ── Expander ────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--g1) !important;
    border: 1px solid var(--g2) !important;
    border-radius: 2px !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    color: var(--g5) !important;
}

/* ── Misc ────────────────────────────────────────────────────────────────── */
hr { border-color: var(--g2) !important; margin: 0 !important; }
.stCaption { font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important; color: var(--g4) !important; }
[data-testid="stImage"] img { border-radius: 2px !important; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--black); }
::-webkit-scrollbar-thumb { background: var(--g3); }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def load_team_map() -> dict:
    with open(ROOT / "config" / "team_map.json") as f:
        return json.load(f)

@st.cache_data
def load_stats_data(mtime: float = 0) -> dict:
    path = ROOT / "data" / "stats" / "latest.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)

@st.cache_data
def load_odds_data(mtime: float = 0) -> dict:
    path = ROOT / "data" / "odds" / "latest.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)

def _file_mtime(rel_path: str) -> float:
    p = ROOT / rel_path
    return p.stat().st_mtime if p.exists() else 0.0

ALL_STATS = {
    "opponent-points-per-game":              {"label": "Points Allowed/G",          "positions": ["QB","RB","WR","TE"], "group": "General"},
    "opponent-yards-per-game":               {"label": "Total Yards Allowed/G",     "positions": ["QB","RB","WR","TE"], "group": "General"},
    "opponent-third-down-conversion-pct":    {"label": "3rd Down Conv% Allowed",    "positions": ["QB","RB","WR","TE"], "group": "General"},
    "opponent-passing-yards-per-game":       {"label": "Pass Yards Allowed/G",      "positions": ["QB","WR","TE"],      "group": "Passing"},
    "opponent-passing-touchdowns-per-game":  {"label": "Pass TDs Allowed/G",        "positions": ["QB","WR","TE"],      "group": "Passing"},
    "opponent-completions-per-game":         {"label": "Completions Allowed/G",     "positions": ["WR","TE"],           "group": "Passing"},
    "opponent-yards-per-pass-attempt":       {"label": "Yds/Pass Attempt Allowed",  "positions": ["QB"],                "group": "Passing"},
    "opponent-rushing-yards-per-game":       {"label": "Rush Yards Allowed/G",      "positions": ["RB"],                "group": "Rushing"},
    "opponent-rushing-touchdowns-per-game":  {"label": "Rush TDs Allowed/G",        "positions": ["RB"],                "group": "Rushing"},
    "opponent-yards-per-rush-attempt":       {"label": "Yards/Carry Allowed",       "positions": ["RB"],                "group": "Rushing"},
}

PREFS_PATH = ROOT / "config" / "stat_preferences.json"

def load_prefs() -> dict:
    if PREFS_PATH.exists():
        with open(PREFS_PATH) as f:
            return json.load(f)
    return {}

def save_prefs(prefs: dict) -> None:
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PREFS_PATH, "w") as f:
        json.dump(prefs, f, indent=2)

team_map     = load_team_map()
team_names   = sorted(team_map.keys())
stats_data   = load_stats_data(mtime=_file_mtime("data/stats/latest.json"))
odds_data    = load_odds_data(mtime=_file_mtime("data/odds/latest.json"))
_meta        = stats_data.get("_meta", {})
data_season  = _meta.get("season", 2025)
data_week    = _meta.get("nfl_week")
data_scraped = _meta.get("scraped_at", "unknown")


# ── Pickle Score reason bullets ───────────────────────────────────────────────
def _pickle_reasons(position: str, bd: dict, def_team: str, off_team: str) -> list:
    pos_label = {"QB": "QBs", "RB": "RBs", "WR": "WRs", "TE": "TEs"}.get(position, position)
    def_nick  = def_team.split()[-1]
    off_nick  = off_team.split()[-1]
    fpa       = bd["fantasy_points_allowed_score"]
    def_s     = bd["defense_bundle_score"]
    imp       = bd["implied_total_score"]

    r = []
    if fpa >= 7.0:
        r.append(f"{def_nick} has been one of the most generous defenses vs {pos_label} this season")
    elif fpa >= 4.0:
        r.append(f"{def_nick} is middle of the pack for {pos_label} fantasy points allowed")
    else:
        r.append(f"{def_nick} has held {pos_label} to below-average fantasy production this season")

    if def_s >= 7.0:
        r.append(f"Weak across key {position} metrics — yards, TDs, and conversion rate")
    elif def_s >= 4.0:
        r.append(f"Average {position} defensive profile — no glaring strength or weakness")
    else:
        r.append(f"Strong {position} defensive stats across yards, TDs, and conversion rate")

    if imp >= 7.0:
        r.append(f"{off_nick} has a high projected score this week — game script favours volume")
    elif imp >= 4.0:
        r.append(f"Projected team total for {off_nick} is around the week's average")
    else:
        r.append(f"Low implied total for {off_nick} — tougher game environment this week")

    return r


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom:24px;padding-bottom:20px;border-bottom:1px solid #1A1A1A;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:28px;color:#FF3300;letter-spacing:3px;line-height:1.1;">Fantasy<br><span style="color:#F0EDE8;">Land</span></div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#3A3A3A;letter-spacing:1.5px;margin-top:6px;text-transform:uppercase;">Starts of the Week</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#FF3300;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 6px 0;">Step 1 — Matchup</p>', unsafe_allow_html=True)
    def_team = st.selectbox(
        "Defense to target",
        team_names,
        index=team_names.index("Dallas Cowboys") if "Dallas Cowboys" in team_names else 0,
        label_visibility="visible",
    )
    off_team = st.selectbox(
        "Player's team",
        team_names,
        index=team_names.index("Los Angeles Rams") if "Los Angeles Rams" in team_names else 0,
        label_visibility="visible",
    )

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#FF3300;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 6px 0;">Step 2 — Position</p>', unsafe_allow_html=True)
    position = st.radio("Position", ["QB", "RB", "WR", "TE"], horizontal=True)

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#3A3A3A;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 6px 0;">Recent weeks to use</p>', unsafe_allow_html=True)
    weeks_back = st.radio("Recent weeks", ["L3W", "L4W"], index=1, horizontal=True, label_visibility="collapsed")
    weeks_int = int(weeks_back[1])

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    if stats_data:
        wk_label = f"Wk {data_week}" if data_week else "Full season"
        st.markdown(f"""
        <div style="border-top:1px solid #1A1A1A;padding-top:16px;margin-bottom:16px;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#3A3A3A;line-height:1.8;">{data_season} · {wk_label}<br>Updated {data_scraped}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#FF1744;border-top:1px solid #1A1A1A;padding-top:16px;margin-bottom:16px;">No data — run weekly update</div>', unsafe_allow_html=True)

    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STATIC PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
team_info     = team_map.get(def_team, {})
primary_color = team_info.get("primary", "#FF3300")
off_nick      = off_team.split()[-1]
def_nick      = def_team.split()[-1]
wk_chip       = f"Wk {data_week}" if data_week else "Full Season"

st.markdown(f"""
<div style="padding:28px var(--page-pad) 20px var(--page-pad);border-bottom:1px solid #1A1A1A;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
    <div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;">
        <span style="font-family:'Bebas Neue',sans-serif;font-size:42px;color:#F0EDE8;letter-spacing:2px;line-height:1;">{off_team.split()[-1]}</span>
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:600;color:#3A3A3A;letter-spacing:3px;">vs</span>
        <span style="font-family:'Bebas Neue',sans-serif;font-size:42px;color:{primary_color};letter-spacing:2px;line-height:1;">{def_team.split()[-1]} Def</span>
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;letter-spacing:2px;background:#1A1A1A;color:#888;padding:5px 12px;border-radius:2px;">{position}</span>
    </div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#3A3A3A;background:#111;padding:5px 10px;border-radius:2px;border:1px solid #1A1A1A;">{data_season} · {wk_chip}</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#3A3A3A;background:#111;padding:5px 10px;border-radius:2px;border:1px solid #1A1A1A;">Updated {data_scraped}</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PICKLE SCORE PANEL
# ══════════════════════════════════════════════════════════════════════════════
if stats_data:
    from pickle_score import calculate_pickle_score, validate_position_stats

    slug_warnings = validate_position_stats(stats_data)
    if slug_warnings:
        with st.expander("Data warnings", expanded=False):
            for w in slug_warnings:
                st.warning(w)

    pickle_result = calculate_pickle_score(
        def_team_name=def_team,
        off_team_name=off_team,
        position=position,
    )
    score = pickle_result["score"]
    label = pickle_result["label"]
    bd    = pickle_result["breakdown"]

    if score >= 8.0:
        sc, sb = "#00C853", "#001508"
    elif score >= 6.0:
        sc, sb = "#FF3300", "#140500"
    elif score >= 4.0:
        sc, sb = "#FFD600", "#141100"
    else:
        sc, sb = "#FF1744", "#140007"

    clean_label = label.replace("🥒", "").replace("Pickles says ", "").strip()
    bar_pct     = int((score / 10) * 100)
    reasons     = _pickle_reasons(position, bd, def_team, off_team)

    reason_html = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;">'
        f'<span style="color:{sc};font-size:16px;line-height:1.3;flex-shrink:0;">→</span>'
        f'<span style="font-family:\'Barlow Condensed\',sans-serif;font-size:16px;font-weight:600;color:#C0BDB8;line-height:1.4;">{r}</span>'
        f'</div>'
        for r in reasons
    )

    st.markdown(f"""
    <div style="background:{sb};border-left:5px solid {sc};padding:28px 36px;margin:24px var(--page-pad) 0 var(--page-pad);display:flex;align-items:stretch;gap:36px;">
        <div style="min-width:110px;display:flex;flex-direction:column;justify-content:center;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:96px;color:{sc};line-height:0.9;letter-spacing:-2px;">{score}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#3A3A3A;letter-spacing:1.5px;text-transform:uppercase;margin-top:8px;">Pickle Score</div>
        </div>
        <div style="width:1px;background:#1E1E1E;"></div>
        <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:16px;">
            <div>
                <div style="font-family:'Bebas Neue',sans-serif;font-size:36px;color:{sc};letter-spacing:2px;line-height:1;">{clean_label}</div>
                <div style="background:#1E1E1E;height:4px;width:100%;border-radius:2px;margin-top:10px;position:relative;">
                    <div style="position:absolute;left:0;top:0;bottom:0;width:{bar_pct}%;background:{sc};border-radius:2px;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:5px;">
                    <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#2A2A2A;">In a Pickle</span>
                    <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#2A2A2A;">Must Start</span>
                </div>
            </div>
            <div>{reason_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Collapsible breakdown
    components = [
        ("Fantasy Pts Allowed",  bd["fantasy_points_allowed_score"], 40),
        ("Defense Bundle",       bd["defense_bundle_score"],         30),
        ("Implied Total",        bd["implied_total_score"],          20),
        ("Game O/U",             bd["game_total_score"],             10),
    ]
    comp_rows = "".join(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;color:#888;width:160px;">{cname}</div>'
        f'<div style="flex:1;background:#1E1E1E;height:3px;border-radius:2px;position:relative;"><div style="position:absolute;left:0;top:0;bottom:0;width:{int((cval/10)*100)}%;background:{sc};border-radius:2px;"></div></div>'
        f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:13px;font-weight:700;color:#F0EDE8;width:36px;text-align:right;">{cval}</div>'
        f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#3A3A3A;width:30px;text-align:right;">{cw}%</div>'
        f'</div>'
        for cname, cval, cw in components
    )

    st.markdown('<div style="margin:0 40px;">', unsafe_allow_html=True)
    with st.expander("Scoring breakdown", expanded=False):
        st.markdown(f'<div style="padding:8px 0;">{comp_rows}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="margin:24px 40px 0 40px;padding:20px 24px;background:#1A1A1A;border-left:3px solid #FF1744;border-radius:2px;">
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:700;color:#FF1744;letter-spacing:1px;">No stats data — run weekly update or trigger GitHub Actions</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_pickle, tab_def, tab_player, tab_odds = st.tabs([
    "Pickle Score Card",
    "Defensive Stats Card",
    "Player Log Card",
    "Odds Card",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 0 — Pickle Score Card
# ─────────────────────────────────────────────────────────────────────────────
with tab_pickle:
    if not stats_data:
        st.warning("No stats data available — run weekly update first.")
    else:
        left_pkl, right_pkl = st.columns([1, 1], gap="large")

        with left_pkl:
            st.markdown(f"""
            <div style="margin-bottom:20px;">
                <div style="font-family:'Bebas Neue',sans-serif;font-size:30px;color:#F0EDE8;letter-spacing:2px;line-height:1;">{off_team.split()[-1]} vs {def_team.split()[-1]}</div>
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:600;color:#888;letter-spacing:1px;margin-top:4px;">Generate a shareable Pickle Score card for this {position} matchup</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Generate Pickle Score Card", use_container_width=True, key="gen_pickle"):
                with st.spinner("Generating..."):
                    from generate_pickle_card import generate_pickle_card
                    try:
                        reasons = _pickle_reasons(position, bd, def_team, off_team)
                        safe_def = re.sub(r"[^\w\-]", "_", def_team.lower())
                        safe_off = re.sub(r"[^\w\-]", "_", off_team.lower())
                        tmp_path = Path(tempfile.gettempdir()) / f"{safe_off}_vs_{safe_def}_{position}_pickle.png"
                        generate_pickle_card(
                            def_team_name=def_team,
                            off_team_name=off_team,
                            position=position,
                            score=score,
                            verdict=clean_label,
                            reasons=reasons,
                            season=data_season,
                            nfl_week=data_week,
                            output_path=tmp_path,
                        )
                        buf = BytesIO()
                        Image.open(tmp_path).save(buf, format="PNG")
                        st.session_state["pickle_card_bytes"] = buf.getvalue()
                        st.session_state["pickle_card_name"]  = f"{safe_off}_vs_{safe_def}_{position}_pickle.png"
                    except Exception as e:
                        st.error(f"Error: {e}")

        with right_pkl:
            if "pickle_card_bytes" in st.session_state:
                st.image(st.session_state["pickle_card_bytes"], use_column_width="always")
                st.download_button(
                    "Download PNG",
                    st.session_state["pickle_card_bytes"],
                    file_name=st.session_state.get("pickle_card_name", "pickle_card.png"),
                    mime="image/png",
                    key="dl_pickle",
                    use_container_width=True,
                )
            else:
                st.markdown("""
                <div style="border:1px dashed #252525;border-radius:2px;padding:60px 20px;text-align:center;">
                    <div style="font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:600;color:#3A3A3A;letter-spacing:1px;">Generate your Pickle Score card above</div>
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#252525;margin-top:8px;">Preview will appear here</div>
                </div>
                """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Defensive Stats Card
# ─────────────────────────────────────────────────────────────────────────────
with tab_def:
    if not stats_data:
        st.warning("No stats data available.")
    else:
        left_col, right_col = st.columns([1, 1], gap="large")

        with left_col:
            st.markdown(f"""
            <div style="margin-bottom:20px;">
                <div style="font-family:'Bebas Neue',sans-serif;font-size:30px;color:#F0EDE8;letter-spacing:2px;line-height:1;">{def_team}</div>
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:600;color:#888;letter-spacing:1px;margin-top:4px;">{position} matchup stats — select the stats to include on your card</div>
            </div>
            """, unsafe_allow_html=True)

            position_slugs = [s for s, m in ALL_STATS.items() if position in m["positions"]]
            prefs          = load_prefs()
            saved_slugs    = prefs.get(f"def_{position}", position_slugs)

            groups_seen: list = []
            groups: dict      = {}
            for slug in position_slugs:
                g = ALL_STATS[slug]["group"]
                if g not in groups:
                    groups[g] = []
                    groups_seen.append(g)
                groups[g].append(slug)

            selected_slugs: list = []
            for group_name in groups_seen:
                st.markdown(f"""
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;letter-spacing:1.5px;color:#3A3A3A;text-transform:uppercase;margin:20px 0 6px 0;padding-bottom:6px;border-bottom:1px solid #1A1A1A;">{group_name}</div>
                """, unsafe_allow_html=True)

                for slug in groups[group_name]:
                    meta      = ALL_STATS[slug]
                    team_stat = stats_data.get(def_team, {}).get(slug, {})
                    rank      = team_stat.get("rank", "—")
                    val       = team_stat.get("value_display", team_stat.get("value", "—"))
                    default   = slug in saved_slugs

                    if isinstance(rank, int):
                        if rank <= 10:
                            rc = "#00C853"
                        elif rank <= 22:
                            rc = "#FFD600"
                        else:
                            rc = "#FF1744"
                        rank_html = f'<span style="background:{rc}18;color:{rc};font-family:\'IBM Plex Mono\',monospace;font-size:11px;font-weight:700;padding:3px 8px;border-radius:2px;border:1px solid {rc}33;">#{rank}</span>'
                    else:
                        rank_html = '<span style="color:#2A2A2A;font-size:12px;">—</span>'

                    col_check, col_info = st.columns([1, 10])
                    with col_check:
                        checked = st.checkbox(meta["label"], value=default, key=f"def_stat_{slug}", label_visibility="collapsed")
                    with col_info:
                        st.markdown(f"""
                        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid #111;">
                            <span style="font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:600;color:#B0ADA8;letter-spacing:0.3px;">{meta['label']}</span>
                            <div style="display:flex;align-items:center;gap:10px;">
                                <span style="font-family:'IBM Plex Mono',monospace;font-size:15px;font-weight:700;color:#F0EDE8;">{val}</span>
                                {rank_html}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    if checked:
                        selected_slugs.append(slug)

            if selected_slugs != saved_slugs:
                prefs[f"def_{position}"] = selected_slugs
                save_prefs(prefs)

            st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
            gen_btn = st.button(
                "Generate Defensive Card",
                disabled=not selected_slugs,
                use_container_width=True,
                key="gen_def",
            )
            if gen_btn:
                with st.spinner("Generating..."):
                    from generate_def_card import generate_def_card
                    try:
                        safe     = re.sub(r"[^\w\-]", "_", def_team.lower())
                        tmp_path = Path(tempfile.gettempdir()) / f"{safe}_def_card.png"
                        generate_def_card(
                            team_name=def_team,
                            position=position,
                            stat_slugs=selected_slugs,
                            season=data_season,
                            output_path=tmp_path,
                        )
                        buf = BytesIO()
                        Image.open(tmp_path).save(buf, format="PNG")
                        st.session_state["def_card_bytes"] = buf.getvalue()
                        st.session_state["def_card_name"]  = f"{safe}_def_card.png"
                    except Exception as e:
                        st.error(f"Error: {e}")

        with right_col:
            if "def_card_bytes" in st.session_state:
                st.image(st.session_state["def_card_bytes"], use_column_width="always")
                st.download_button(
                    "Download PNG",
                    st.session_state["def_card_bytes"],
                    file_name=st.session_state.get("def_card_name", "def_card.png"),
                    mime="image/png",
                    use_container_width=True,
                )
            else:
                st.markdown("""
                <div style="border:1px dashed #252525;border-radius:2px;padding:60px 20px;text-align:center;">
                    <div style="font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:600;color:#3A3A3A;letter-spacing:1px;">Select stats, then generate your card</div>
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#252525;margin-top:8px;">Preview will appear here</div>
                </div>
                """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Player Log Card
# ─────────────────────────────────────────────────────────────────────────────
with tab_player:
    left_col2, right_col2 = st.columns([1, 1], gap="large")

    with left_col2:
        st.markdown(f"""
        <div style="margin-bottom:20px;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:30px;color:#F0EDE8;letter-spacing:2px;line-height:1;">{def_team}</div>
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:600;color:#888;letter-spacing:1px;margin-top:4px;">Recent {position} performances against this defense — last {weeks_int} weeks, PPR scoring</div>
        </div>
        """, unsafe_allow_html=True)

        def_abbr = team_map.get(def_team, {}).get("sleeper_id", "")

        if st.button(f"Fetch {position} logs vs {def_team.split()[-1]}", use_container_width=True, key="fetch_logs"):
            with st.spinner("Pulling from Sleeper API..."):
                from scrape_player_logs import get_player_logs
                try:
                    logs = get_player_logs(
                        def_team_abbr=def_abbr,
                        position=position,
                        weeks=weeks_int,
                        season=data_season,
                    )
                    st.session_state["player_logs"] = logs
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state["player_logs"] = []

        logs = st.session_state.get("player_logs", [])

        if logs:
            st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#3A3A3A;letter-spacing:1.5px;text-transform:uppercase;margin:20px 0 6px 0;padding-bottom:6px;border-bottom:1px solid #1A1A1A;">Select performances to include</div>', unsafe_allow_html=True)
            selected_lines = []
            for i, log in enumerate(logs):
                fpts_str = f"{log['fpts']:.1f}"
                if position in ("WR", "TE"):
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['rec']} rec / {log['rec_yd']} yds / {log['rec_td']} TD — **{fpts_str} pts**"
                elif position == "RB":
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['rush_att']} car / {log['rush_yd']} yds / {log['rush_td']} TD — **{fpts_str} pts**"
                elif position == "QB":
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['pass_cmp']}/{log['pass_att']}, {log['pass_yd']} yds, {log['pass_td']} TD, {log['pass_int']} INT — **{fpts_str} pts**"
                else:
                    summary = f"Wk{log['week']} · **{log['name']}**: **{fpts_str} pts**"
                if st.checkbox(summary, value=True, key=f"log_{i}"):
                    selected_lines.append(log)

            st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
            if st.button("Generate Player Log Card", key="gen_player_card", disabled=not selected_lines, use_container_width=True):
                with st.spinner("Generating..."):
                    from generate_player_card import generate_player_card
                    try:
                        safe     = re.sub(r"[^\w\-]", "_", def_team.lower())
                        tmp_path = Path(tempfile.gettempdir()) / f"{safe}_player_card.png"
                        generate_player_card(
                            def_team_name=def_team,
                            position=position,
                            player_lines=selected_lines,
                            season=data_season,
                            output_path=tmp_path,
                        )
                        buf = BytesIO()
                        Image.open(tmp_path).save(buf, format="PNG")
                        st.session_state["player_card_bytes"] = buf.getvalue()
                        st.session_state["player_card_name"]  = f"{safe}_player_card.png"
                    except Exception as e:
                        st.error(f"Error: {e}")

        elif "player_logs" in st.session_state:
            st.info("No performances found. Expected in offseason — data appears once the NFL season begins.")

    with right_col2:
        if "player_card_bytes" in st.session_state:
            st.image(st.session_state["player_card_bytes"], use_column_width="always")
            st.download_button(
                "Download PNG",
                st.session_state["player_card_bytes"],
                file_name=st.session_state.get("player_card_name", "player_card.png"),
                mime="image/png",
                key="dl_player",
                use_container_width=True,
            )
        else:
            st.markdown("""
            <div style="border:1px dashed #252525;border-radius:2px;padding:60px 20px;text-align:center;">
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:600;color:#3A3A3A;letter-spacing:1px;">Fetch logs, then generate your card</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#252525;margin-top:8px;">Preview will appear here</div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Odds Card
# ─────────────────────────────────────────────────────────────────────────────
with tab_odds:
    left_col3, right_col3 = st.columns([1, 1], gap="large")

    with left_col3:
        st.markdown(f"""
        <div style="margin-bottom:20px;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:30px;color:#F0EDE8;letter-spacing:2px;line-height:1;">{off_team}</div>
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:600;color:#888;letter-spacing:1px;margin-top:4px;">Game odds and implied team totals</div>
        </div>
        """, unsafe_allow_html=True)

        if not odds_data:
            st.info("No odds data yet. Available during the NFL season — auto-updates Tuesday and Wednesday midnight Sydney time.")
        else:
            team_odds = odds_data.get("teams", {}).get(off_team)
            opp_odds  = odds_data.get("teams", {}).get(def_team)
            if team_odds:
                c1, c2, c3 = st.columns(3)
                c1.metric("Game O/U", f"{team_odds.get('game_total','—')}", f"#{team_odds.get('game_total_rank','—')} highest")
                c2.metric(f"{off_team.split()[-1]} implied", f"{team_odds.get('implied_total','—')}", f"#{team_odds.get('implied_total_rank','—')} highest")
                if opp_odds:
                    c3.metric(f"{def_team.split()[-1]} implied", f"{opp_odds.get('implied_total','—')}", f"#{opp_odds.get('implied_total_rank','—')} highest")

                st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
                if st.button("Generate Odds Card", key="gen_odds", use_container_width=True):
                    with st.spinner("Generating..."):
                        from generate_odds_card import generate_odds_card
                        try:
                            safe     = re.sub(r"[^\w\-]", "_", off_team.lower())
                            tmp_path = Path(tempfile.gettempdir()) / f"{safe}_odds_card.png"
                            generate_odds_card(
                                off_team_name=off_team,
                                season=data_season,
                                output_path=tmp_path,
                            )
                            buf = BytesIO()
                            Image.open(tmp_path).save(buf, format="PNG")
                            st.session_state["odds_card_bytes"] = buf.getvalue()
                            st.session_state["odds_card_name"]  = f"{safe}_odds_card.png"
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info(f"No odds for {off_team} this week. Expected in offseason.")

    with right_col3:
        if "odds_card_bytes" in st.session_state:
            st.image(st.session_state["odds_card_bytes"], use_column_width="always")
            st.download_button(
                "Download PNG",
                st.session_state["odds_card_bytes"],
                file_name=st.session_state.get("odds_card_name", "odds_card.png"),
                mime="image/png",
                key="dl_odds",
                use_container_width=True,
            )
        else:
            st.markdown("""
            <div style="border:1px dashed #252525;border-radius:2px;padding:60px 20px;text-align:center;">
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:600;color:#3A3A3A;letter-spacing:1px;">Generate your odds card above</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#252525;margin-top:8px;">Preview will appear here</div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div style="padding:0 40px;">', unsafe_allow_html=True)
st.divider()

_CARD_PAIRS = [
    ("pickle_card_bytes", "pickle_card_name"),
    ("def_card_bytes",    "def_card_name"),
    ("player_card_bytes", "player_card_name"),
    ("odds_card_bytes",   "odds_card_name"),
]
cards_ready = [(bk, nk) for bk, nk in _CARD_PAIRS if bk in st.session_state]

upload_col, _ = st.columns([1, 2])
with upload_col:
    if cards_ready:
        st.caption(f"{len(cards_ready)} card(s) ready to upload")
    if st.button("Upload all to Google Drive", use_container_width=True, disabled=not cards_ready):
        from upload_to_gdrive import upload_bytes as _upload_bytes
        with st.spinner("Uploading..."):
            for bytes_key, name_key in cards_ready:
                data      = st.session_state[bytes_key]
                file_name = st.session_state.get(name_key, bytes_key.replace("_bytes", ".png"))
                try:
                    url = _upload_bytes(file_name, data)
                    st.success(f"{file_name} → [View in Drive]({url})")
                except FileNotFoundError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"{file_name} failed: {e}")

st.markdown('</div>', unsafe_allow_html=True)
