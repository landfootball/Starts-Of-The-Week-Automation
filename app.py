"""
FantasyLand — Starts of the Week Research Tool
Streamlit web app for generating branded matchup graphics.

Run locally:  streamlit run app.py
Hosted:       Deployed via Streamlit Community Cloud
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from io import BytesIO

from PIL import Image

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FantasyLand · Starts of the Week",
    page_icon="🥒",
    layout="wide",
)

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_team_map() -> dict:
    with open(ROOT / "config" / "team_map.json") as f:
        return json.load(f)

@st.cache_data
def load_stats_data() -> dict:
    path = ROOT / "data" / "stats" / "latest.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)

@st.cache_data
def load_odds_data() -> dict:
    path = ROOT / "data" / "odds" / "latest.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)

# ── Stat definitions ───────────────────────────────────────────────────────────
ALL_STATS = {
    "opponent-points-per-game":              {"label": "Points Allowed/G",         "positions": ["QB","RB","WR","TE"], "group": "General"},
    "opponent-yards-per-game":               {"label": "Total Yards Allowed/G",    "positions": ["QB","RB","WR","TE"], "group": "General"},
    "opponent-third-down-conversion-pct":    {"label": "3rd Down Conv % Allowed",  "positions": ["QB","RB","WR","TE"], "group": "General"},
    "opponent-passing-yards-per-game":       {"label": "Pass Yards Allowed/G",     "positions": ["QB","WR","TE"],      "group": "Passing"},
    "opponent-passing-touchdowns-per-game":  {"label": "Pass TDs Allowed/G",       "positions": ["QB","WR","TE"],      "group": "Passing"},
    "opponent-completions-per-game":         {"label": "Completions Allowed/G",    "positions": ["WR","TE"],           "group": "Passing"},
    "opponent-yards-per-pass-attempt":       {"label": "Yards/Pass Attempt Allowed","positions": ["QB"],               "group": "Passing"},
    "opponent-rushing-yards-per-game":       {"label": "Rush Yards Allowed/G",     "positions": ["RB"],                "group": "Rushing"},
    "opponent-rushing-touchdowns-per-game":  {"label": "Rush TDs Allowed/G",       "positions": ["RB"],                "group": "Rushing"},
    "opponent-yards-per-rush-attempt":       {"label": "Yards/Carry Allowed",      "positions": ["RB"],                "group": "Rushing"},
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

# ── Sidebar ────────────────────────────────────────────────────────────────────
team_map = load_team_map()
team_names = sorted(team_map.keys())
stats_data = load_stats_data()
odds_data = load_odds_data()

# Read scrape metadata
_meta = stats_data.get("_meta", {})
data_season = _meta.get("season", int(season) if "season" in dir() else 2025)
data_week = _meta.get("nfl_week")
data_scraped = _meta.get("scraped_at", "unknown")
weeks_label = f"Weeks 1–{data_week}" if data_week else "Full season"

with st.sidebar:
    st.markdown("### Matchup Setup")

    def_team = st.selectbox(
        "Opposing Defense",
        team_names,
        index=team_names.index("Dallas Cowboys") if "Dallas Cowboys" in team_names else 0,
        help="The defense your player is facing",
    )

    off_team = st.selectbox(
        "Offensive Team",
        team_names,
        index=team_names.index("Los Angeles Rams") if "Los Angeles Rams" in team_names else 0,
        help="The team your player plays for",
    )

    position = st.radio("Position", ["QB", "RB", "WR", "TE"], horizontal=True)

    st.divider()

    weeks_back = st.radio("Player Log Window", ["L3W", "L4W"], index=1, horizontal=True)
    weeks_int = int(weeks_back[1])

# ── Team color for dynamic theming ────────────────────────────────────────────
team_info = team_map.get(def_team, {})
primary_color = team_info.get("primary", "#2E7D32")

# ── Custom CSS with team color accent ─────────────────────────────────────────
st.markdown(f"""
<style>
    /* Pill-style stat rows */
    .stat-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #2A2A2A;
    }}
    .stat-label {{
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #999;
        font-weight: 500;
    }}
    .stat-value {{
        font-weight: 700;
        font-size: 16px;
    }}
    .rank-badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        color: white;
        margin-left: 8px;
    }}
    /* Card preview area */
    .card-preview-container {{
        background: #1A1A1A;
        border-radius: 12px;
        padding: 20px;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 200px;
    }}
    /* Section headers */
    .section-header {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: {primary_color};
        font-weight: 700;
        margin: 16px 0 8px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid {primary_color}44;
    }}
    /* Pickle score */
    .pickle-container {{
        background: linear-gradient(135deg, #1A1A1A 0%, #222222 100%);
        border: 1px solid #2A2A2A;
        border-left: 4px solid {primary_color};
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 8px;
    }}
    /* Remove default Streamlit top padding */
    .block-container {{
        padding-top: 1.5rem !important;
    }}
</style>
""", unsafe_allow_html=True)

# ── Page header ────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([6, 1])
with col_h1:
    if data_week == 1:
        week_label = f"{data_season} Season Week 1"
    elif data_week and data_week > 1:
        week_label = f"{data_season} Season Week 1-{data_week}"
    else:
        week_label = f"{data_season} Season"

    if stats_data:
        data_badge = f'<span style="background:#1E3A1E; color:#4CAF50; font-size:11px; font-weight:700; padding:3px 10px; border-radius:20px; letter-spacing:0.5px;">📡 {week_label} · Updated {data_scraped}</span>'
    else:
        data_badge = f'<span style="background:#2A2A1E; color:#888; font-size:11px; font-weight:700; padding:3px 10px; border-radius:20px;">No live data — run weekly update</span>'

    st.markdown(f"""
    <div style="margin-bottom: 6px;">
        <span style="font-size: 26px; font-weight: 800; color: #FFFFFF;">FantasyLand</span>
        <span style="font-size: 26px; font-weight: 300; color: #888888;"> · Starts of the Week</span>
    </div>
    <div style="margin-bottom: 8px;">{data_badge}</div>
    <div style="font-size: 13px; color: #666666; margin-bottom: 16px;">
        {position} matchup · {off_team} vs <span style="color:{primary_color}; font-weight:600;">{def_team}</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Pickle Score ───────────────────────────────────────────────────────────────
if stats_data:
    from pickle_score import calculate_pickle_score
    pickle_result = calculate_pickle_score(
        def_team_name=def_team,
        off_team_name=off_team,
        position=position,
    )
    score = pickle_result["score"]
    label = pickle_result["label"]

    if score >= 8.0:
        score_color = "#2E7D32"
    elif score >= 6.0:
        score_color = "#F57C00"
    elif score >= 4.0:
        score_color = "#B8860B"
    else:
        score_color = "#C62828"

    pcol1, pcol2, pcol3 = st.columns([1, 3, 1])
    with pcol1:
        st.markdown(f"""
        <div style="text-align:center; background:#1A1A1A; border-radius:10px; padding:16px; border: 1px solid #2A2A2A;">
            <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#666; margin-bottom:4px;">Pickle Score</div>
            <div style="font-size:48px; font-weight:900; color:{score_color}; line-height:1;">{score}</div>
            <div style="font-size:11px; color:{score_color}; font-weight:600; margin-top:4px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    with pcol2:
        bd = pickle_result["breakdown"]
        b1, b2, b3 = st.columns(3)
        b1.metric("Defense", f"{bd['defense_score']} / 10", f"{int(bd['defense_weight']*100)}% weight")
        b2.metric("Game Total", f"{bd['game_total_score']} / 10", f"{int(bd['game_total_weight']*100)}% weight")
        b3.metric("Implied Total", f"{bd['implied_total_score']} / 10", f"{int(bd['implied_total_weight']*100)}% weight")

else:
    st.warning("No stats data loaded. Run the weekly update or trigger it from GitHub Actions.")

st.divider()

# ── Main tabs ──────────────────────────────────────────────────────────────────
tab_def, tab_player, tab_odds = st.tabs(["🛡 Defensive Stats Card", "📋 Player Log Card", "📊 Odds Card"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Defensive Stats Card
# ══════════════════════════════════════════════════════════════════════════════
with tab_def:
    if not stats_data:
        st.warning("No stats data available.")
    else:
        left_col, right_col = st.columns([1, 1], gap="large")

        with left_col:
            # Team header
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                <div style="width:4px; height:32px; background:{primary_color}; border-radius:2px;"></div>
                <div>
                    <div style="font-size:18px; font-weight:700; color:#FFFFFF;">{def_team}</div>
                    <div style="font-size:12px; color:#666; text-transform:uppercase; letter-spacing:1px;">{position} Matchup Stats</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Stat toggles grouped by category
            position_slugs = [s for s, meta in ALL_STATS.items() if position in meta["positions"]]
            prefs = load_prefs()
            saved_slugs = prefs.get(f"def_{position}", position_slugs)

            # Group by stat category
            groups_seen = []
            groups = {}
            for slug in position_slugs:
                g = ALL_STATS[slug]["group"]
                if g not in groups:
                    groups[g] = []
                    groups_seen.append(g)
                groups[g].append(slug)

            selected_slugs = []
            for group_name in groups_seen:
                st.markdown(f'<div class="section-header">{group_name}</div>', unsafe_allow_html=True)
                for slug in groups[group_name]:
                    meta = ALL_STATS[slug]
                    team_stat = stats_data.get(def_team, {}).get(slug, {})
                    rank = team_stat.get("rank", "—")
                    val = team_stat.get("value_display", team_stat.get("value", "—"))
                    default = slug in saved_slugs

                    # Color the rank
                    if isinstance(rank, int):
                        if rank <= 10:
                            rank_bg = "#2E7D32"
                        elif rank <= 22:
                            rank_bg = "#F57C00"
                        else:
                            rank_bg = "#C62828"
                        rank_html = f'<span class="rank-badge" style="background:{rank_bg};">{rank}</span>'
                    else:
                        rank_html = f'<span style="color:#555; font-size:12px;">—</span>'

                    col_check, col_info = st.columns([1, 8])
                    with col_check:
                        checked = st.checkbox("", value=default, key=f"def_stat_{slug}", label_visibility="collapsed")
                    with col_info:
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0;">
                            <span style="font-size:13px; color:#CCCCCC;">{meta['label']}</span>
                            <span style="font-size:14px; font-weight:700; color:#FFFFFF;">{val} {rank_html}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    if checked:
                        selected_slugs.append(slug)

            if selected_slugs != saved_slugs:
                prefs[f"def_{position}"] = selected_slugs
                save_prefs(prefs)

            st.markdown("<br>", unsafe_allow_html=True)
            gen_btn = st.button(
                "Generate Card",
                type="primary",
                disabled=not selected_slugs,
                use_container_width=True,
                key="gen_def",
            )

            if gen_btn:
                if not selected_slugs:
                    st.error("Select at least one stat.")
                else:
                    with st.spinner("Generating..."):
                        from generate_def_card import generate_def_card
                        try:
                            safe = def_team.lower().replace(" ", "_")
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
                            st.session_state["def_card_name"] = f"{safe}_def_card.png"
                        except Exception as e:
                            st.error(f"Error: {e}")

        with right_col:
            st.markdown(f"""
            <div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#555; margin-bottom:12px;">Card Preview</div>
            """, unsafe_allow_html=True)

            if "def_card_bytes" in st.session_state:
                st.image(
                    Image.open(BytesIO(st.session_state["def_card_bytes"])),
                    use_column_width=True,
                )
                st.download_button(
                    "Download PNG",
                    st.session_state["def_card_bytes"],
                    file_name=st.session_state.get("def_card_name", "def_card.png"),
                    mime="image/png",
                    use_container_width=True,
                )
            else:
                st.markdown("""
                <div style="background:#1A1A1A; border-radius:12px; border:1px dashed #333;
                            padding:60px 20px; text-align:center; color:#444; font-size:13px;">
                    Select stats and click<br><strong>Generate Card</strong>
                </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Player Log Card
# ══════════════════════════════════════════════════════════════════════════════
with tab_player:
    left_col2, right_col2 = st.columns([1, 1], gap="large")

    with left_col2:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
            <div style="width:4px; height:32px; background:{primary_color}; border-radius:2px;"></div>
            <div>
                <div style="font-size:18px; font-weight:700; color:#FFFFFF;">{def_team}</div>
                <div style="font-size:12px; color:#666; text-transform:uppercase; letter-spacing:1px;">Recent {position} Performances vs this Defense</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(f"Last {weeks_int} weeks · PPR scoring")

        def_abbr = team_map.get(def_team, {}).get("sleeper_id", "")

        if st.button(f"Fetch {position} Logs vs {def_team}", use_container_width=True, key="fetch_logs"):
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
            st.markdown(f'<div class="section-header">Select performances to include</div>', unsafe_allow_html=True)
            selected_lines = []

            for i, log in enumerate(logs):
                fpts_str = f"{log['fpts']:.1f} FPTS"
                if position in ("WR", "TE"):
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['rec']} REC / {log['rec_yd']} YDs / {log['rec_td']} TD — **{fpts_str}**"
                elif position == "RB":
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['rush_att']} CAR / {log['rush_yd']} YDs / {log['rush_td']} TD — **{fpts_str}**"
                elif position == "QB":
                    summary = f"Wk{log['week']} · **{log['name']}** ({log['team']}): {log['pass_cmp']}/{log['pass_att']} / {log['pass_yd']} YDs / {log['pass_td']} TD / {log['pass_int']} INT — **{fpts_str}**"
                else:
                    summary = f"Wk{log['week']} · **{log['name']}**: **{fpts_str}**"

                if st.checkbox(summary, value=True, key=f"log_{i}"):
                    selected_lines.append(log)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Generate Player Log Card", type="primary", key="gen_player_card",
                         disabled=not selected_lines, use_container_width=True):
                with st.spinner("Generating..."):
                    from generate_player_card import generate_player_card
                    try:
                        safe = def_team.lower().replace(" ", "_")
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
                        st.session_state["player_card_name"] = f"{safe}_player_card.png"
                    except Exception as e:
                        st.error(f"Error: {e}")

        elif "player_logs" in st.session_state:
            st.info("No performances found. This is expected in the offseason — data will appear once the NFL season begins.")

    with right_col2:
        st.markdown('<div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#555; margin-bottom:12px;">Card Preview</div>', unsafe_allow_html=True)

        if "player_card_bytes" in st.session_state:
            st.image(Image.open(BytesIO(st.session_state["player_card_bytes"])), use_column_width=True)
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
            <div style="background:#1A1A1A; border-radius:12px; border:1px dashed #333;
                        padding:60px 20px; text-align:center; color:#444; font-size:13px;">
                Fetch logs and click<br><strong>Generate Player Log Card</strong>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Odds Card
# ══════════════════════════════════════════════════════════════════════════════
with tab_odds:
    left_col3, right_col3 = st.columns([1, 1], gap="large")

    with left_col3:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
            <div style="width:4px; height:32px; background:{primary_color}; border-radius:2px;"></div>
            <div>
                <div style="font-size:18px; font-weight:700; color:#FFFFFF;">{off_team}</div>
                <div style="font-size:12px; color:#666; text-transform:uppercase; letter-spacing:1px;">Game Odds & Implied Totals</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not odds_data:
            st.info("No odds data yet. Odds are only available during the NFL season — the automated update runs every Tuesday and Wednesday at midnight Sydney time.")
        else:
            team_odds = odds_data.get("teams", {}).get(off_team)
            opp_odds = odds_data.get("teams", {}).get(def_team)

            if team_odds:
                c1, c2, c3 = st.columns(3)
                c1.metric("Game O/U", f"{team_odds.get('game_total', '—')}", f"#{team_odds.get('game_total_rank', '—')} highest")
                c2.metric(f"{off_team.split()[-1]} Implied", f"{team_odds.get('implied_total', '—')}", f"#{team_odds.get('implied_total_rank', '—')} highest")
                if opp_odds:
                    c3.metric(f"{def_team.split()[-1]} Implied", f"{opp_odds.get('implied_total', '—')}", f"#{opp_odds.get('implied_total_rank', '—')} highest")

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Generate Odds Card", type="primary", key="gen_odds", use_container_width=True):
                    with st.spinner("Generating..."):
                        from generate_odds_card import generate_odds_card
                        try:
                            safe = off_team.lower().replace(" ", "_")
                            tmp_path = Path(tempfile.gettempdir()) / f"{safe}_odds_card.png"
                            generate_odds_card(
                                off_team_name=off_team,
                                season=data_season,
                                output_path=tmp_path,
                            )
                            buf = BytesIO()
                            Image.open(tmp_path).save(buf, format="PNG")
                            st.session_state["odds_card_bytes"] = buf.getvalue()
                            st.session_state["odds_card_name"] = f"{safe}_odds_card.png"
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info(f"No odds found for {off_team} this week. This is expected in the offseason.")

    with right_col3:
        st.markdown('<div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#555; margin-bottom:12px;">Card Preview</div>', unsafe_allow_html=True)

        if "odds_card_bytes" in st.session_state:
            st.image(Image.open(BytesIO(st.session_state["odds_card_bytes"])), use_column_width=True)
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
            <div style="background:#1A1A1A; border-radius:12px; border:1px dashed #333;
                        padding:60px 20px; text-align:center; color:#444; font-size:13px;">
                Click <strong>Generate Odds Card</strong><br>when odds are available
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Google Drive upload
# ══════════════════════════════════════════════════════════════════════════════
st.divider()

card_keys = ["def_card_bytes", "player_card_bytes", "odds_card_bytes"]
cards_ready = [k for k in card_keys if k in st.session_state]

upload_col, _ = st.columns([1, 2])
with upload_col:
    if cards_ready:
        st.caption(f"{len(cards_ready)} card(s) ready to upload")
    if st.button("Upload All Cards to Google Drive", type="secondary", use_container_width=True, disabled=not cards_ready):
        from upload_to_gdrive import upload_all_outputs
        with st.spinner("Uploading..."):
            try:
                results = upload_all_outputs()
                for r in results:
                    if r.get("url"):
                        st.success(f"{r['file']} → [View in Drive]({r['url']})")
                    else:
                        st.error(f"{r['file']} failed: {r.get('error', 'unknown')}")
            except FileNotFoundError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Upload error: {e}")
