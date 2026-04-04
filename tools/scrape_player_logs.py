"""
Fetches recent player game logs from the Sleeper API.
Returns all players of the specified position who faced the target defense
in the last N weeks, sorted by FPTS descending.

No API key required — Sleeper's API is free and public.

Usage (CLI):
    python tools/scrape_player_logs.py --team SEA --position WR --weeks 4

Usage (from Streamlit / other tools):
    from tools.scrape_player_logs import get_player_logs
    logs = get_player_logs(def_team_abbr="SEA", position="WR", weeks=4, season=2025)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
TEAM_MAP_PATH = ROOT / "config" / "team_map.json"

SLEEPER_BASE = "https://api.sleeper.app/v1"

# PPR scoring weights (standard PPR)
SCORING = {
    "pass_yd": 0.04,
    "pass_td": 4.0,
    "pass_int": -2.0,
    "rush_yd": 0.1,
    "rush_td": 6.0,
    "rec": 1.0,        # PPR
    "rec_yd": 0.1,
    "rec_td": 6.0,
    "fumbles_lost": -2.0,
    "two_pt_conversions": 2.0,
}

# Minimum FPTS threshold to be considered "notable"
MIN_FPTS = {
    "QB": 10.0,
    "RB": 5.0,
    "WR": 5.0,
    "TE": 4.0,
}


def _load_team_map() -> dict:
    with open(TEAM_MAP_PATH) as f:
        return json.load(f)


def _abbr_to_canonical(abbr: str) -> str | None:
    """Convert Sleeper team abbreviation to canonical team name."""
    team_map = _load_team_map()
    for canonical, info in team_map.items():
        if info["sleeper_id"] == abbr:
            return canonical
    return None


def _canonical_to_abbr(canonical: str) -> str | None:
    """Convert canonical team name to Sleeper abbreviation."""
    team_map = _load_team_map()
    info = team_map.get(canonical)
    return info["sleeper_id"] if info else None


def _calculate_fpts(stats: dict) -> float:
    """Calculate PPR fantasy points from a Sleeper stats dict."""
    total = 0.0
    for stat_key, weight in SCORING.items():
        total += stats.get(stat_key, 0) * weight
    return round(total, 2)


def _get_nfl_state() -> dict:
    """Get current NFL state (season, week) from Sleeper."""
    resp = requests.get(f"{SLEEPER_BASE}/state/nfl", timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_matchups(season: int, week: int) -> list[dict]:
    """Get all matchup data for a given NFL week."""
    url = f"{SLEEPER_BASE}/schedule/nfl/regular/{season}/{week}"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json() or []


def _get_player_stats(season: int, week: int) -> dict:
    """Get all player stats for a given NFL week. Returns {player_id: stats_dict}."""
    url = f"{SLEEPER_BASE}/stats/nfl/regular/{season}/{week}"
    resp = requests.get(url, timeout=15)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json() or {}


def _get_all_players() -> dict:
    """
    Get full player database from Sleeper. Cached in .tmp/ to avoid repeated large downloads.
    Returns {player_id: {name, position, team, ...}}.
    """
    cache_path = ROOT / ".tmp" / "sleeper_players.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        # Use cache if less than 7 days old
        import os
        age_days = (time.time() - os.path.getmtime(cache_path)) / 86400
        if age_days < 7:
            with open(cache_path) as f:
                return json.load(f)

    print("  Downloading Sleeper player database (one-time, ~5MB) ...", end=" ", flush=True)
    resp = requests.get(f"{SLEEPER_BASE}/players/nfl", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    with open(cache_path, "w") as f:
        json.dump(data, f)
    print("OK")
    return data


def _find_games_vs_defense(matchups: list[dict], def_team_abbr: str) -> list[str]:
    """
    Find the opponent team abbreviations that played against the target defense.
    Returns list of offensive team abbreviations (teams that faced def_team_abbr).
    """
    offensive_teams = []
    for game in matchups:
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        if home == def_team_abbr:
            offensive_teams.append(away)
        elif away == def_team_abbr:
            offensive_teams.append(home)
    return offensive_teams


def get_player_logs(
    def_team_abbr: str,
    position: str,
    weeks: int = 4,
    season: int | None = None,
    min_fpts: float | None = None,
) -> list[dict]:
    """
    Fetch player game logs for players who faced the target defense in recent weeks.

    Args:
        def_team_abbr: Sleeper team abbreviation for the DEFENSIVE team (e.g. "SEA")
        position: "QB", "RB", "WR", or "TE"
        weeks: Number of recent weeks to look back
        season: NFL season year. Defaults to current season from Sleeper state.
        min_fpts: Minimum FPTS to include. Defaults to position threshold.

    Returns:
        List of player log dicts, sorted by FPTS descending:
        [
          {
            "name": "Justin Jefferson",
            "team": "MIN",
            "position": "WR",
            "week": 12,
            "rec": 6, "rec_yd": 112, "rec_td": 1,
            "rush_att": 0, "rush_yd": 0, "rush_td": 0,
            "pass_yd": 0, "pass_td": 0, "pass_int": 0,
            "pass_cmp": 0, "pass_att": 0,
            "fpts": 26.2,
          },
          ...
        ]
    """
    if min_fpts is None:
        min_fpts = MIN_FPTS.get(position, 5.0)

    # Get current season/week
    nfl_state = _get_nfl_state()
    if season is None:
        season = nfl_state.get("season", 2025)
        try:
            season = int(season)
        except (TypeError, ValueError):
            season = 2025

    current_week = nfl_state.get("week", 1)
    try:
        current_week = int(current_week)
    except (TypeError, ValueError):
        current_week = 1

    # Weeks to check: last N completed weeks
    start_week = max(1, current_week - weeks)
    week_range = list(range(start_week, current_week))

    if not week_range:
        return []

    # Load player database
    all_players = _get_all_players()

    results = []

    for week in week_range:
        print(f"  Fetching week {week} data ...", end=" ", flush=True)
        try:
            matchups = _get_matchups(season, week)
            player_stats = _get_player_stats(season, week)
        except Exception as e:
            print(f"FAILED ({e})")
            continue

        # Find which teams played against our defense this week
        off_teams = _find_games_vs_defense(matchups, def_team_abbr)
        if not off_teams:
            print(f"skipped (no game found for {def_team_abbr})")
            continue

        print(f"OK (opponent teams: {', '.join(off_teams)})")

        # Find players from those offensive teams at the target position
        for player_id, stats in player_stats.items():
            player_info = all_players.get(player_id, {})
            p_team = player_info.get("team", "")
            p_pos = player_info.get("position", "")
            p_name = player_info.get("full_name") or player_info.get("last_name", "Unknown")

            if p_team not in off_teams:
                continue
            if p_pos != position:
                continue

            fpts = _calculate_fpts(stats)
            if fpts < min_fpts:
                continue

            results.append({
                "name": p_name,
                "team": p_team,
                "position": p_pos,
                "week": week,
                # Receiving
                "rec": int(stats.get("rec", 0)),
                "rec_yd": int(stats.get("rec_yd", 0)),
                "rec_td": int(stats.get("rec_td", 0)),
                # Rushing
                "rush_att": int(stats.get("rush_att", 0)),
                "rush_yd": int(stats.get("rush_yd", 0)),
                "rush_td": int(stats.get("rush_td", 0)),
                # Passing
                "pass_cmp": int(stats.get("pass_cmp", 0)),
                "pass_att": int(stats.get("pass_att", 0)),
                "pass_yd": int(stats.get("pass_yd", 0)),
                "pass_td": int(stats.get("pass_td", 0)),
                "pass_int": int(stats.get("pass_int", 0)),
                "fpts": fpts,
            })

        time.sleep(0.5)  # polite delay

    # Sort by FPTS descending
    results.sort(key=lambda x: x["fpts"], reverse=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch player logs vs a defense from Sleeper")
    parser.add_argument("--team", required=True, help="Defensive team abbreviation (e.g. SEA)")
    parser.add_argument("--position", required=True, choices=["QB", "RB", "WR", "TE"])
    parser.add_argument("--weeks", type=int, default=4)
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--min-fpts", type=float, default=None)
    args = parser.parse_args()

    print(f"=== Player Logs: {args.position}s vs {args.team} (last {args.weeks} weeks) ===")
    logs = get_player_logs(
        def_team_abbr=args.team,
        position=args.position,
        weeks=args.weeks,
        season=args.season,
        min_fpts=args.min_fpts,
    )

    print(f"\n{len(logs)} notable performances found:\n")
    for log in logs:
        print(f"  Week {log['week']} | {log['name']} ({log['team']}) — {log['fpts']} FPTS")


if __name__ == "__main__":
    main()
