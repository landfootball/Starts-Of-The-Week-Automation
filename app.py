"""
FantasyLand — Starts of the Week Research Tool
Streamlit web app for generating branded matchup graphics.

Run locally:  streamlit run app.py
Hosted:       Deployed via Streamlit Community Cloud
"""

import json
import os
import sys
from pathlib import Path
from io import BytesIO

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FantasyLand · Starts of the Week",
    page_icon="🥒",
    layout="wide",
)

# ── Load team map ──────────────────────────────────────────────────────────────
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

# ── Stat definitions (slug → display info) ────────────────────────────────────
ALL_STATS = {
    "opponent-points-per-game":          {"label": "Points Allowed/G",     "positions": ["QB","RB","WR","TE"]},
    "opponent-total-yards-per-game":     {"label": "Total Yards Allowed/G","positions": ["QB","RB","WR","TE"]},
    "opponent-passing-yards-per-game":   {"label": "Pass Yards Allowed/G", "positions": ["QB","WR","TE"]},
    "opponent-rushing-yards-per-game":   {"label": "Rush Yards Allowed/G", "positions": ["RB"]},
    "opponent-yards-per-rush-attempt":   {"label": "Yards/Carry Allowed",  "positions": ["RB"]},
    "opponent-passing-touchdowns-per-game":  {"label": "Pass TDs Allowed/G",    "positions": ["QB","WR","TE"]},
    "opponent-rushing-touchdowns-per-game":  {"label": "Rush TDs Allowed/G",    "positions": ["RB"]},
    "opponent-receptions-per-game":          {"label": "Receptions Allowed/G",  "positions": ["WR","TE"]},
    "opponent-passer-rating-allowed":        {"label": "Passer Rating Allowed", "positions": ["QB"]},
    "opponent-third-down-conversion-pct":    {"label": "3rd Down Conv % Allowed","positions": ["QB","RB","WR","TE"]},
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

# ── Helper: image → bytes for preview ─────────────────────────────────────────
def img_to_bytes(img) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ── Header ─────────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_title:
    st.title("FantasyLand · Starts of the Week")
    st.caption("Research tool for weekly matchup graphics")

st.divider()

# ── Sidebar controls ───────────────────────────────────────────────────────────
team_map = load_team_map()
team_names = sorted(team_map.keys())

with st.sidebar:
    st.header("Matchup Setup")

    def_team = st.selectbox(
        "Opposing Defense (the team your player faces)",
        team_names,
        index=team_names.index("Seattle Seahawks") if "Seattle Seahawks" in team_names else 0,
    )

    off_team = st.selectbox(
        "Player's Team (the offensive team)",
        team_names,
        index=team_names.index("Los Angeles Rams") if "Los Angeles Rams" in team_names else 0,
    )

    position = st.radio("Position", ["QB", "RB", "WR", "TE"], horizontal=True)

    st.divider()

    weeks_back = st.radio("Player logs — look back", ["L3W", "L4W"], index=1)
    weeks_int = int(weeks_back[1])

    season = st.number_input("Season year", min_value=2020, max_value=2030, value=2025, step=1)

# ── Pickle Score (always visible) ─────────────────────────────────────────────
stats_data = load_stats_data()
odds_data = load_odds_data()

if stats_data:
    from pickle_score import calculate_pickle_score
    pickle_result = calculate_pickle_score(
        def_team_name=def_team,
        off_team_name=off_team,
        position=position,
    )

    score = pickle_result["score"]
    label = pickle_result["label"]

    # Colour the score card
    if score >= 8.0:
        score_color = "#2E7D32"
    elif score >= 6.0:
        score_color = "#F57C00"
    elif score >= 4.0:
        score_color = "#B8860B"
    else:
        score_color = "#C62828"

    st.markdown(
        f"""
        <div style="
            background: {score_color}18;
            border-left: 6px solid {score_color};
            border-radius: 8px;
            padding: 16px 24px;
            margin-bottom: 24px;
        ">
            <div style="font-size:13px; text-transform:uppercase; letter-spacing:1px; color:{score_color}; font-weight:700;">
                Pickle Score — {position} | {off_team} vs {def_team}
            </div>
            <div style="font-size:52px; font-weight:900; color:{score_color}; line-height:1.1;">
                {score}
            </div>
            <div style="font-size:18px; font-weight:600; color:{score_color};">
                {label}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Pickle Score breakdown"):
        bd = pickle_result["breakdown"]
        cols = st.columns(3)
        cols[0].metric("Defense Score", f"{bd['defense_score']} / 10", f"weight: {int(bd['defense_weight']*100)}%")
        cols[1].metric("Game Total Score", f"{bd['game_total_score']} / 10", f"weight: {int(bd['game_total_weight']*100)}%")
        cols[2].metric("Implied Total Score", f"{bd['implied_total_score']} / 10", f"weight: {int(bd['implied_total_weight']*100)}%")
else:
    st.warning("No stats data loaded yet. Run the weekly update or trigger it manually from GitHub Actions.")

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_def, tab_player, tab_odds = st.tabs(["Defensive Stats Card", "Player Log Card", "Odds Card"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Defensive Stats Card
# ══════════════════════════════════════════════════════════════════════════════
with tab_def:
    st.subheader(f"{def_team} — Defensive Stats")

    if not stats_data:
        st.warning("No stats data available.")
    else:
        # Stat toggles
        st.write("**Select stats to include on the card:**")
        position_slugs = [s for s, meta in ALL_STATS.items() if position in meta["positions"]]

        prefs = load_prefs()
        saved_slugs = prefs.get(f"def_{position}", position_slugs)

        selected_slugs = []
        for slug in position_slugs:
            label_text = ALL_STATS[slug]["label"]
            team_stat = stats_data.get(def_team, {}).get(slug, {})
            rank = team_stat.get("rank", "—")
            val = team_stat.get("value_display", team_stat.get("value", "—"))
            default = slug in saved_slugs

            checked = st.checkbox(
                f"**{label_text}** — {val}  ·  Rank {rank}",
                value=default,
                key=f"def_stat_{slug}",
            )
            if checked:
                selected_slugs.append(slug)

        # Save preferences
        if selected_slugs != saved_slugs:
            prefs[f"def_{position}"] = selected_slugs
            save_prefs(prefs)

        st.divider()

        col_gen, col_prev = st.columns([1, 2])
        with col_gen:
            if st.button("Generate Defensive Stats Card", type="primary", disabled=not selected_slugs):
                if not selected_slugs:
                    st.error("Select at least one stat.")
                else:
                    with st.spinner("Generating card..."):
                        from generate_def_card import generate_def_card
                        try:
                            out_path = generate_def_card(
                                team_name=def_team,
                                position=position,
                                stat_slugs=selected_slugs,
                                season=int(season),
                            )
                            st.session_state["def_card_path"] = str(out_path)
                            st.success(f"Card saved: {out_path.name}")
                        except Exception as e:
                            st.error(f"Error: {e}")

        with col_prev:
            if "def_card_path" in st.session_state:
                st.image(st.session_state["def_card_path"], caption="Defensive Stats Card", use_container_width=True)
                with open(st.session_state["def_card_path"], "rb") as f:
                    st.download_button(
                        "Download PNG",
                        f,
                        file_name=Path(st.session_state["def_card_path"]).name,
                        mime="image/png",
                    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Player Log Card
# ══════════════════════════════════════════════════════════════════════════════
with tab_player:
    st.subheader(f"{def_team} — Recent {position} Performances Against Them")
    st.caption(f"Last {weeks_int} weeks | PPR scoring")

    def_abbr = team_map.get(def_team, {}).get("sleeper_id", "")

    if st.button(f"Fetch {position} Logs vs {def_team}", key="fetch_logs"):
        with st.spinner(f"Pulling data from Sleeper API..."):
            from scrape_player_logs import get_player_logs
            try:
                logs = get_player_logs(
                    def_team_abbr=def_abbr,
                    position=position,
                    weeks=weeks_int,
                    season=int(season),
                )
                st.session_state["player_logs"] = logs
            except Exception as e:
                st.error(f"Error fetching logs: {e}")
                st.session_state["player_logs"] = []

    logs = st.session_state.get("player_logs", [])

    if logs:
        st.write(f"**{len(logs)} performances found.** Select which to include on the card:")

        selected_lines = []
        for i, log in enumerate(logs):
            fpts_str = f"{log['fpts']:.1f} FPTS"

            if position in ("WR", "TE"):
                summary = f"Wk{log['week']} | {log['name']} ({log['team']}): {log['rec']} REC, {log['rec_yd']} YDs, {log['rec_td']} TD — **{fpts_str}**"
            elif position == "RB":
                summary = f"Wk{log['week']} | {log['name']} ({log['team']}): {log['rush_att']} CAR, {log['rush_yd']} YDs, {log['rush_td']} TD — **{fpts_str}**"
            elif position == "QB":
                summary = f"Wk{log['week']} | {log['name']} ({log['team']}): {log['pass_cmp']}/{log['pass_att']}, {log['pass_yd']} YDs, {log['pass_td']} TD, {log['pass_int']} INT — **{fpts_str}**"
            else:
                summary = f"Wk{log['week']} | {log['name']}: **{fpts_str}**"

            if st.checkbox(summary, value=True, key=f"log_{i}"):
                selected_lines.append(log)

        st.divider()

        col_gen2, col_prev2 = st.columns([1, 2])
        with col_gen2:
            if st.button("Generate Player Log Card", type="primary", key="gen_player_card", disabled=not selected_lines):
                with st.spinner("Generating card..."):
                    from generate_player_card import generate_player_card
                    try:
                        out_path = generate_player_card(
                            def_team_name=def_team,
                            position=position,
                            player_lines=selected_lines,
                            season=int(season),
                        )
                        st.session_state["player_card_path"] = str(out_path)
                        st.success(f"Card saved: {out_path.name}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        with col_prev2:
            if "player_card_path" in st.session_state:
                st.image(st.session_state["player_card_path"], caption="Player Log Card", use_container_width=True)
                with open(st.session_state["player_card_path"], "rb") as f:
                    st.download_button(
                        "Download PNG",
                        f,
                        file_name=Path(st.session_state["player_card_path"]).name,
                        mime="image/png",
                        key="dl_player",
                    )
    elif "player_logs" in st.session_state:
        st.info("No performances found matching the criteria for this defense/position/week range.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Odds Card
# ══════════════════════════════════════════════════════════════════════════════
with tab_odds:
    st.subheader(f"{off_team} — Game Odds & Implied Totals")

    if not odds_data:
        st.warning("No odds data available. Run tools/scrape_odds.py or wait for Wednesday's automated update.")
    else:
        team_odds = odds_data.get("teams", {}).get(off_team)
        opp_odds = odds_data.get("teams", {}).get(def_team)

        if team_odds:
            cols = st.columns(3)
            cols[0].metric(
                "Game Over/Under",
                f"{team_odds.get('game_total', '—')}",
                f"#{team_odds.get('game_total_rank', '—')} highest this week",
            )
            cols[1].metric(
                f"{off_team.split()[-1]} Implied Total",
                f"{team_odds.get('implied_total', '—')}",
                f"#{team_odds.get('implied_total_rank', '—')} highest this week",
            )
            if opp_odds:
                cols[2].metric(
                    f"{def_team.split()[-1]} Implied Total",
                    f"{opp_odds.get('implied_total', '—')}",
                    f"#{opp_odds.get('implied_total_rank', '—')} highest this week",
                )

            st.divider()

            col_gen3, col_prev3 = st.columns([1, 2])
            with col_gen3:
                if st.button("Generate Odds Card", type="primary", key="gen_odds"):
                    with st.spinner("Generating card..."):
                        from generate_odds_card import generate_odds_card
                        try:
                            out_path = generate_odds_card(
                                off_team_name=off_team,
                                season=int(season),
                            )
                            st.session_state["odds_card_path"] = str(out_path)
                            st.success(f"Card saved: {out_path.name}")
                        except Exception as e:
                            st.error(f"Error: {e}")

            with col_prev3:
                if "odds_card_path" in st.session_state:
                    st.image(st.session_state["odds_card_path"], caption="Odds Card", use_container_width=True)
                    with open(st.session_state["odds_card_path"], "rb") as f:
                        st.download_button(
                            "Download PNG",
                            f,
                            file_name=Path(st.session_state["odds_card_path"]).name,
                            mime="image/png",
                            key="dl_odds",
                        )
        else:
            st.info(f"No odds data found for {off_team} this week.")

# ══════════════════════════════════════════════════════════════════════════════
# Upload all generated cards to Google Drive
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("Upload to Google Drive")
st.caption("Uploads all generated PNGs from this session to your Google Drive root")

if st.button("Upload All Cards to Google Drive", type="secondary"):
    from upload_to_gdrive import upload_all_outputs
    with st.spinner("Uploading..."):
        try:
            results = upload_all_outputs()
            for r in results:
                if r.get("url"):
                    st.success(f"{r['file']} → [View in Drive]({r['url']})")
                else:
                    st.error(f"{r['file']} failed: {r.get('error', 'unknown error')}")
        except FileNotFoundError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Upload error: {e}")
