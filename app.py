"""
FantasyLand — Starts of the Week Research Tool
Bold sports poster aesthetic: Bebas Neue + Barlow Condensed, orange/blue/black/white.
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
    --orange:  #FF3300;
    --blue:    #0033FF;
    --black:   #080808;
    --white:   #F2F0EC;
    --g1:      #111111;
    --g2:      #1A1A1A;
    --g3:      #252525;
    --g4:      #333333;
    --green:   #00C853;
    --yellow:  #FFD600;
    --red:     #FF1744;
}

/* ── Base ─────────────────────────────────────────────────────────────────── */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--black) !important;
    color: var(--white) !important;
}
[data-testid="stHeader"] { display: none !important; }
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--g1) !important;
    border-right: 3px solid var(--blue) !important;
}
[data-testid="stSidebar"] .block-container {
    padding: 28px 20px !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: var(--white) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio > label {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 3px !important;
    text-transform: uppercase !important;
    color: var(--g4) !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background-color: var(--g2) !important;
    border: 1px solid var(--g3) !important;
    border-radius: 0 !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label span {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button {
    background-color: var(--orange) !important;
    color: var(--white) !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 18px !important;
    letter-spacing: 3px !important;
    padding: 12px 28px !important;
    width: 100% !important;
    transition: background 0.12s ease !important;
}
.stButton > button:hover {
    background-color: var(--blue) !important;
    border: none !important;
}
.stButton > button:disabled {
    background-color: var(--g3) !important;
    color: var(--g4) !important;
}
.stDownloadButton > button {
    background-color: transparent !important;
    border: 2px solid var(--blue) !important;
    color: var(--blue) !important;
    border-radius: 0 !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 16px !important;
    letter-spacing: 3px !important;
}
.stDownloadButton > button:hover {
    background-color: var(--blue) !important;
    color: var(--white) !important;
}

/* ── Tabs ────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    background: var(--g1) !important;
    border-bottom: 2px solid var(--g2) !important;
    gap: 0 !important;
    padding: 0 40px !important;
}
[data-testid="stTabs"] button[role="tab"] {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 2.5px !important;
    text-transform: uppercase !important;
    color: var(--g4) !important;
    border-radius: 0 !important;
    padding: 18px 28px !important;
    border-bottom: 3px solid transparent !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: var(--orange) !important;
    border-bottom: 3px solid var(--orange) !important;
    background: transparent !important;
}
[data-testid="stTabs"] [data-testid="stTabContent"] {
    padding: 32px 40px !important;
    background: var(--black) !important;
}

/* ── Metrics ─────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--g2) !important;
    padding: 16px 20px !important;
    border-top: 3px solid var(--blue) !important;
    border-radius: 0 !important;
}
[data-testid="stMetricLabel"] > div {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: var(--g4) !important;
}
[data-testid="stMetricValue"] > div {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 30px !important;
    letter-spacing: 1px !important;
    color: var(--white) !important;
}
[data-testid="stMetricDelta"] svg { display: none !important; }
[data-testid="stMetricDelta"] > div {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    color: var(--g4) !important;
}

/* ── Expander ────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--g1) !important;
    border: 1px solid var(--g2) !important;
    border-radius: 0 !important;
}

/* ── Misc ────────────────────────────────────────────────────────────────── */
hr { border-color: var(--g2) !important; margin: 0 !important; }
.stCaption { font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important; color: var(--g4) !important; }
[data-testid="stImage"] img { border-radius: 0 !important; }
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

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 28px; padding-bottom: 20px; border-bottom: 1px solid #1A1A1A;">
        <div style="font-family:'Bebas Neue',sans-serif; font-size:32px; color:#FF3300; letter-spacing:4px; line-height:1;">FANTASY</div>
        <div style="font-family:'Bebas Neue',sans-serif; font-size:32px; color:#F2F0EC; letter-spacing:4px; line-height:1;">LAND</div>
        <div style="font-family:'Barlow Condensed',sans-serif; font-size:10px; font-weight:700; color:#333; letter-spacing:3px; text-transform:uppercase; margin-top:8px;">Starts of the Week</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("↺  REFRESH DATA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:9px;color:#FF3300;letter-spacing:2px;margin-bottom:4px;">STEP 1 — SET MATCHUP</div>', unsafe_allow_html=True)
    def_team = st.selectbox(
        "DEFENSE TO TARGET",
        team_names,
        index=team_names.index("Dallas Cowboys") if "Dallas Cowboys" in team_names else 0,
    )
    off_team = st.selectbox(
        "PLAYER'S TEAM",
        team_names,
        index=team_names.index("Los Angeles Rams") if "Los Angeles Rams" in team_names else 0,
    )

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:9px;color:#FF3300;letter-spacing:2px;margin-bottom:4px;">STEP 2 — POSITION &amp; WINDOW</div>', unsafe_allow_html=True)
    position = st.radio("POSITION", ["QB", "RB", "WR", "TE"], horizontal=True)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:10px;font-weight:700;color:#333;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">RECENT WEEKS TO USE</div>', unsafe_allow_html=True)
    weeks_back = st.radio("Recent Weeks", ["L3W", "L4W"], index=1, horizontal=True, label_visibility="collapsed")
    weeks_int = int(weeks_back[1])

    # Data badge
    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    if stats_data:
        wk = f"WK {data_week}" if data_week else "FULL SEASON"
        st.markdown(f"""
        <div style="border-top:1px solid #1A1A1A; padding-top:16px;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#2A2A2A;letter-spacing:1px;">{data_season} · {wk}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#2A2A2A;letter-spacing:1px;margin-top:3px;">UPDATED {data_scraped}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#FF1744;border-top:1px solid #1A1A1A;padding-top:16px;">NO DATA — RUN UPDATE</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MARQUEE HEADER
# ══════════════════════════════════════════════════════════════════════════════
team_info     = team_map.get(def_team, {})
primary_color = team_info.get("primary", "#FF3300")
ticker_text   = f"STARTS OF THE WEEK  ·  {off_team.upper()} VS {def_team.upper()}  ·  {position} MATCHUP  ·  "

st.markdown(f"""
<div style="background:#FF3300;height:56px;overflow:hidden;display:flex;align-items:center;">
    <div id="marquee-inner" style="
        display:inline-block;
        white-space:nowrap;
        animation:ticker 24s linear infinite;
        font-family:'Bebas Neue',sans-serif;
        font-size:36px;
        color:white;
        letter-spacing:5px;
        line-height:1;
    ">{ticker_text * 6}</div>
</div>
<style>
@keyframes ticker {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MATCHUP TITLE + PICKLE SCORE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="padding:28px 40px 0 40px;">
    <div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:24px;">
        <span style="font-family:'Bebas Neue',sans-serif;font-size:52px;color:#F2F0EC;letter-spacing:2px;line-height:1;">{off_team.upper()}</span>
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:700;color:#333;letter-spacing:4px;">VS</span>
        <span style="font-family:'Bebas Neue',sans-serif;font-size:52px;color:{primary_color};letter-spacing:2px;line-height:1;">{def_team.upper()} DEF</span>
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:900;letter-spacing:3px;background:#1A1A1A;color:#555;padding:6px 14px;margin-left:4px;">{position}</span>
    </div>
</div>
""", unsafe_allow_html=True)

if stats_data:
    from pickle_score import calculate_pickle_score, validate_position_stats

    slug_warnings = validate_position_stats(stats_data)
    if slug_warnings:
        with st.expander("⚠ Data warnings", expanded=False):
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

    clean_label = label.replace("🥒","").replace("Pickles says ","").strip().upper()
    bar_pct     = int((score / 10) * 100)

    # Component rows for the breakdown panel
    components = [
        ("FPA",       bd["fantasy_points_allowed_score"], 40),
        ("DEFENSE",   bd["defense_bundle_score"],         30),
        ("IMPLIED",   bd["implied_total_score"],          20),
        ("GAME O/U",  bd["game_total_score"],             10),
    ]
    comp_html = ""
    for cname, cval, cw in components:
        cbar = int((cval / 10) * 100)
        comp_html += f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:11px;">
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;letter-spacing:2px;color:#444;width:70px;">{cname}</div>
            <div style="flex:1;background:#1E1E1E;height:3px;position:relative;">
                <div style="position:absolute;left:0;top:0;bottom:0;width:{cbar}%;background:{sc};"></div>
            </div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:700;color:#F2F0EC;width:32px;text-align:right;">{cval}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#333;width:28px;text-align:right;">{cw}%</div>
        </div>"""

    st.markdown(f"""
    <div style="background:{sb};border-left:6px solid {sc};border-top:1px solid {sc}22;border-right:1px solid {sc}11;border-bottom:1px solid {sc}11;padding:28px 36px;margin:0 40px 8px 40px;display:flex;align-items:stretch;gap:40px;">
        <div style="min-width:120px;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:108px;color:{sc};line-height:1;letter-spacing:-3px;">{score}</div>
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;letter-spacing:3px;color:#333;text-transform:uppercase;margin-top:-6px;">Pickle Score</div>
        </div>
        <div style="width:1px;background:#1E1E1E;"></div>
        <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:44px;color:{sc};letter-spacing:3px;line-height:1;margin-bottom:20px;">{clean_label}</div>
            <div style="background:#1E1E1E;height:6px;width:100%;position:relative;margin-bottom:6px;">
                <div style="position:absolute;left:0;top:0;bottom:0;width:{bar_pct}%;background:{sc};"></div>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#2A2A2A;letter-spacing:1px;">IN A PICKLE</span>
                <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#2A2A2A;letter-spacing:1px;">MUST START</span>
            </div>
        </div>
        <div style="width:1px;background:#1E1E1E;"></div>
        <div style="min-width:260px;display:flex;flex-direction:column;justify-content:center;">{comp_html}</div>
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="margin:0 40px;padding:24px;background:#1A1A1A;border-left:4px solid #FF1744;">
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:700;letter-spacing:2px;color:#FF1744;">NO STATS DATA — RUN WEEKLY UPDATE OR TRIGGER GITHUB ACTIONS</span>
    </div>
    """, unsafe_allow_html=True)

# Spacer before tabs
st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_def, tab_player, tab_odds = st.tabs([
    "🛡  DEFENSIVE STATS CARD",
    "📋  PLAYER LOG CARD",
    "📊  ODDS CARD",
])

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
                <div style="font-family:'Bebas Neue',sans-serif;font-size:34px;color:#F2F0EC;letter-spacing:2px;line-height:1;">{def_team.upper()}</div>
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;color:#333;letter-spacing:3px;text-transform:uppercase;margin-top:4px;">{position} MATCHUP STATS</div>
            </div>
            """, unsafe_allow_html=True)

            position_slugs = [s for s, m in ALL_STATS.items() if position in m["positions"]]
            prefs       = load_prefs()
            saved_slugs = prefs.get(f"def_{position}", position_slugs)

            groups_seen: list = []
            groups: dict = {}
            for slug in position_slugs:
                g = ALL_STATS[slug]["group"]
                if g not in groups:
                    groups[g] = []
                    groups_seen.append(g)
                groups[g].append(slug)

            selected_slugs: list = []
            for group_name in groups_seen:
                st.markdown(f"""
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;
                     letter-spacing:3px;color:#FF3300;text-transform:uppercase;
                     margin:22px 0 8px 0;padding-bottom:6px;border-bottom:1px solid #FF330033;">{group_name}</div>
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
                        rank_html = f'<span style="background:{rc}15;color:{rc};font-family:IBM Plex Mono;font-size:11px;font-weight:700;padding:3px 8px;border:1px solid {rc}33;">#{rank}</span>'
                    else:
                        rank_html = '<span style="color:#2A2A2A;font-size:12px;">—</span>'

                    col_check, col_info = st.columns([1, 10])
                    with col_check:
                        checked = st.checkbox(meta["label"], value=default, key=f"def_stat_{slug}", label_visibility="collapsed")
                    with col_info:
                        st.markdown(f"""
                        <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #111;">
                            <span style="font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:600;color:#AAA;letter-spacing:0.5px;">{meta['label']}</span>
                            <div style="display:flex;align-items:center;gap:10px;">
                                <span style="font-family:'IBM Plex Mono',monospace;font-size:15px;font-weight:700;color:#F2F0EC;">{val}</span>
                                {rank_html}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    if checked:
                        selected_slugs.append(slug)

            if selected_slugs != saved_slugs:
                prefs[f"def_{position}"] = selected_slugs
                save_prefs(prefs)

            st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
            st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:9px;color:#FF3300;letter-spacing:2px;margin-bottom:6px;">STEP 3 — GENERATE</div>', unsafe_allow_html=True)
            gen_btn = st.button(
                "GENERATE CARD",
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
            st.markdown('<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:10px;font-weight:700;letter-spacing:3px;color:#2A2A2A;text-transform:uppercase;margin-bottom:16px;">CARD PREVIEW</div>', unsafe_allow_html=True)
            if "def_card_bytes" in st.session_state:
                st.image(st.session_state["def_card_bytes"], use_column_width="always")
                st.download_button(
                    "DOWNLOAD PNG",
                    st.session_state["def_card_bytes"],
                    file_name=st.session_state.get("def_card_name", "def_card.png"),
                    mime="image/png",
                    use_container_width=True,
                )
            else:
                st.markdown("""
                <div style="border:1px dashed #1E1E1E;padding:80px 20px;text-align:center;
                     color:#1E1E1E;font-family:'Barlow Condensed',sans-serif;font-size:12px;
                     font-weight:700;letter-spacing:2px;text-transform:uppercase;">
                    SELECT STATS<br>THEN GENERATE
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
            <div style="font-family:'Bebas Neue',sans-serif;font-size:34px;color:#F2F0EC;letter-spacing:2px;line-height:1;">{def_team.upper()}</div>
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;color:#333;letter-spacing:3px;text-transform:uppercase;margin-top:4px;">RECENT {position} PERFORMANCES VS THIS DEFENSE</div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"Last {weeks_int} weeks · PPR scoring")
        def_abbr = team_map.get(def_team, {}).get("sleeper_id", "")

        if st.button(f"FETCH {position} LOGS VS {def_team.split()[-1].upper()}", use_container_width=True, key="fetch_logs"):
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
            st.markdown('<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:10px;font-weight:700;letter-spacing:3px;color:#FF3300;text-transform:uppercase;margin:20px 0 8px 0;padding-bottom:6px;border-bottom:1px solid #FF330033;">SELECT PERFORMANCES</div>', unsafe_allow_html=True)
            selected_lines = []
            for i, log in enumerate(logs):
                fpts_str = f"{log['fpts']:.1f}"
                if position in ("WR", "TE"):
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['rec']} REC / {log['rec_yd']} YDs / {log['rec_td']} TD — **{fpts_str} FPTS**"
                elif position == "RB":
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['rush_att']} CAR / {log['rush_yd']} YDs / {log['rush_td']} TD — **{fpts_str} FPTS**"
                elif position == "QB":
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['pass_cmp']}/{log['pass_att']} / {log['pass_yd']} YDs / {log['pass_td']} TD / {log['pass_int']} INT — **{fpts_str} FPTS**"
                else:
                    summary = f"Wk{log['week']} · **{log['name']}**: **{fpts_str} FPTS**"
                if st.checkbox(summary, value=True, key=f"log_{i}"):
                    selected_lines.append(log)

            st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
            if st.button("GENERATE PLAYER LOG CARD", key="gen_player_card", disabled=not selected_lines, use_container_width=True):
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
        st.markdown('<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:10px;font-weight:700;letter-spacing:3px;color:#2A2A2A;text-transform:uppercase;margin-bottom:16px;">CARD PREVIEW</div>', unsafe_allow_html=True)
        if "player_card_bytes" in st.session_state:
            st.image(st.session_state["player_card_bytes"], use_column_width="always")
            st.download_button(
                "DOWNLOAD PNG",
                st.session_state["player_card_bytes"],
                file_name=st.session_state.get("player_card_name", "player_card.png"),
                mime="image/png",
                key="dl_player",
                use_container_width=True,
            )
        else:
            st.markdown("""
            <div style="border:1px dashed #1E1E1E;padding:80px 20px;text-align:center;
                 color:#1E1E1E;font-family:'Barlow Condensed',sans-serif;font-size:12px;
                 font-weight:700;letter-spacing:2px;text-transform:uppercase;">
                FETCH LOGS THEN<br>GENERATE CARD
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
            <div style="font-family:'Bebas Neue',sans-serif;font-size:34px;color:#F2F0EC;letter-spacing:2px;line-height:1;">{off_team.upper()}</div>
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;color:#333;letter-spacing:3px;text-transform:uppercase;margin-top:4px;">GAME ODDS & IMPLIED TOTALS</div>
        </div>
        """, unsafe_allow_html=True)

        if not odds_data:
            st.info("No odds data yet. Available during NFL season — auto-updates Tuesday & Wednesday midnight Sydney.")
        else:
            team_odds = odds_data.get("teams", {}).get(off_team)
            opp_odds  = odds_data.get("teams", {}).get(def_team)
            if team_odds:
                c1, c2, c3 = st.columns(3)
                c1.metric("GAME O/U", f"{team_odds.get('game_total','—')}", f"#{team_odds.get('game_total_rank','—')} highest")
                c2.metric(f"{off_team.split()[-1].upper()} IMPLIED", f"{team_odds.get('implied_total','—')}", f"#{team_odds.get('implied_total_rank','—')} highest")
                if opp_odds:
                    c3.metric(f"{def_team.split()[-1].upper()} IMPLIED", f"{opp_odds.get('implied_total','—')}", f"#{opp_odds.get('implied_total_rank','—')} highest")

                st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
                if st.button("GENERATE ODDS CARD", key="gen_odds", use_container_width=True):
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
        st.markdown('<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:10px;font-weight:700;letter-spacing:3px;color:#2A2A2A;text-transform:uppercase;margin-bottom:16px;">CARD PREVIEW</div>', unsafe_allow_html=True)
        if "odds_card_bytes" in st.session_state:
            st.image(st.session_state["odds_card_bytes"], use_container_width=True)
            st.download_button(
                "DOWNLOAD PNG",
                st.session_state["odds_card_bytes"],
                file_name=st.session_state.get("odds_card_name", "odds_card.png"),
                mime="image/png",
                key="dl_odds",
                use_container_width=True,
            )
        else:
            st.markdown("""
            <div style="border:1px dashed #1E1E1E;padding:80px 20px;text-align:center;
                 color:#1E1E1E;font-family:'Barlow Condensed',sans-serif;font-size:12px;
                 font-weight:700;letter-spacing:2px;text-transform:uppercase;">
                GENERATE ODDS CARD<br>WHEN ODDS AVAILABLE
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div style="padding:0 40px;">', unsafe_allow_html=True)
st.divider()

_CARD_PAIRS = [
    ("def_card_bytes",    "def_card_name"),
    ("player_card_bytes", "player_card_name"),
    ("odds_card_bytes",   "odds_card_name"),
]
cards_ready = [(bk, nk) for bk, nk in _CARD_PAIRS if bk in st.session_state]

upload_col, _ = st.columns([1, 2])
with upload_col:
    if cards_ready:
        st.caption(f"{len(cards_ready)} card(s) ready to upload")
    if st.button("UPLOAD ALL TO GOOGLE DRIVE", use_container_width=True, disabled=not cards_ready):
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
