"""
Calculates the Pickle Score — a proprietary matchup quality metric (1.0–10.0).

Combines:
  - Defense factor (50%): How exploitable is the opposing defense for this position?
  - Game total factor (25%): How high is the game over/under this week?
  - Implied team total factor (25%): How many points is the player's team projected to score?

Higher score = better matchup for fantasy.

Labels:
  8.0–10.0: "Pickles says MUST-START 🥒"
  6.0–7.9:  "Pickles says SOLID START"
  4.0–5.9:  "Pickles says PROCEED WITH CAUTION"
  1.0–3.9:  "Pickles says YOU'RE IN A PICKLE — sit him"

Usage:
    from tools.pickle_score import calculate_pickle_score

    result = calculate_pickle_score(
        def_team_name="Seattle Seahawks",
        off_team_name="Los Angeles Rams",
        position="QB",
    )
    print(result["score"], result["label"])
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
STATS_PATH = ROOT / "data" / "stats" / "latest.json"
ODDS_PATH = ROOT / "data" / "odds" / "latest.json"

# ── Position-relevant stat slugs ───────────────────────────────────────────────
POSITION_STATS: dict[str, list[str]] = {
    "QB": [
        "opponent-passing-yards-per-game",
        "opponent-passing-touchdowns-per-game",
        "opponent-passer-rating-allowed",
        "opponent-points-per-game",
        "opponent-total-yards-per-game",
    ],
    "RB": [
        "opponent-rushing-yards-per-game",
        "opponent-yards-per-rush-attempt",
        "opponent-rushing-touchdowns-per-game",
        "opponent-points-per-game",
    ],
    "WR": [
        "opponent-passing-yards-per-game",
        "opponent-passing-touchdowns-per-game",
        "opponent-receptions-per-game",
        "opponent-points-per-game",
        "opponent-total-yards-per-game",
    ],
    "TE": [
        "opponent-passing-yards-per-game",
        "opponent-passing-touchdowns-per-game",
        "opponent-receptions-per-game",
        "opponent-points-per-game",
    ],
}

# Weights for each factor (must sum to 1.0)
WEIGHTS = {
    "defense": 0.50,
    "game_total": 0.25,
    "implied_total": 0.25,
}

TOTAL_TEAMS = 32   # denominator for rank normalization


def _rank_to_score(rank: int, total: int = TOTAL_TEAMS, higher_is_better: bool = True) -> float:
    """
    Convert a rank (1 = most allowed) to a 0–10 score.
    For defensive stats where higher rank (more allowed) is better for fantasy:
      rank 1 = 10.0, rank 32 = 0.0
    """
    if higher_is_better:
        # rank 1 = best matchup = 10
        return round(10.0 * (total - rank) / (total - 1), 2)
    else:
        # rank 1 = worst matchup = 0
        return round(10.0 * (rank - 1) / (total - 1), 2)


def _defense_score(def_team_name: str, position: str, stats_data: dict) -> float:
    """
    Calculate the defense factor score (0–10) for a given team/position.
    Averages the rank-to-score across all position-relevant stats.
    """
    team_stats = stats_data.get(def_team_name, {})
    relevant_slugs = POSITION_STATS.get(position, [])

    scores = []
    for slug in relevant_slugs:
        stat = team_stats.get(slug)
        if stat:
            rank = stat["rank"]
            higher_better = stat.get("higher_is_better", True)
            scores.append(_rank_to_score(rank, higher_is_better=higher_better))

    if not scores:
        return 5.0  # neutral fallback

    return round(sum(scores) / len(scores), 2)


def _game_total_score(off_team_name: str, odds_data: dict) -> float:
    """
    Score (0–10) based on where this game's total ranks among all games this week.
    Highest O/U game = 10, lowest = 0.
    """
    team_data = odds_data.get("teams", {}).get(off_team_name)
    if not team_data or not team_data.get("game_total_rank"):
        return 5.0  # neutral fallback

    rank = team_data["game_total_rank"]
    total_games = len(odds_data.get("games", []))
    if total_games == 0:
        return 5.0

    # rank 1 = highest total = 10
    return round(10.0 * (total_games - rank) / max(total_games - 1, 1), 2)


def _implied_total_score(off_team_name: str, odds_data: dict) -> float:
    """
    Score (0–10) based on the offensive team's implied scoring total rank.
    Highest implied score = 10.
    """
    team_data = odds_data.get("teams", {}).get(off_team_name)
    if not team_data or not team_data.get("implied_total_rank"):
        return 5.0

    rank = team_data["implied_total_rank"]
    total_teams = len(odds_data.get("teams", {}))
    if total_teams == 0:
        return 5.0

    # rank 1 = highest implied total = 10
    return round(10.0 * (total_teams - rank) / max(total_teams - 1, 1), 2)


def _get_label(score: float) -> str:
    if score >= 8.0:
        return "Pickles says MUST-START 🥒"
    elif score >= 6.0:
        return "Pickles says SOLID START"
    elif score >= 4.0:
        return "Pickles says PROCEED WITH CAUTION"
    else:
        return "Pickles says YOU'RE IN A PICKLE — sit him"


def calculate_pickle_score(
    def_team_name: str,
    off_team_name: str,
    position: str,
    weights: dict | None = None,
) -> dict:
    """
    Calculate the Pickle Score for a specific player matchup.

    Args:
        def_team_name: The defensive team (opponent), e.g. "Seattle Seahawks"
        off_team_name: The offensive team (player's team), e.g. "Los Angeles Rams"
        position: "QB", "RB", "WR", or "TE"
        weights: Optional override for scoring weights dict.

    Returns:
        {
          "score": 8.3,
          "label": "Pickles says MUST-START 🥒",
          "breakdown": {
            "defense_score": 9.1,
            "game_total_score": 7.5,
            "implied_total_score": 8.0,
            "defense_weight": 0.50,
            ...
          }
        }
    """
    w = weights or WEIGHTS

    # Load data
    stats_data: dict = {}
    if STATS_PATH.exists():
        with open(STATS_PATH) as f:
            stats_data = json.load(f)

    odds_data: dict = {}
    if ODDS_PATH.exists():
        with open(ODDS_PATH) as f:
            odds_data = json.load(f)

    # Calculate component scores
    def_score = _defense_score(def_team_name, position, stats_data)
    game_total_score = _game_total_score(off_team_name, odds_data)
    implied_score = _implied_total_score(off_team_name, odds_data)

    # Weighted composite
    raw = (
        def_score * w["defense"]
        + game_total_score * w["game_total"]
        + implied_score * w["implied_total"]
    )

    # Clamp to 1.0–10.0
    score = round(max(1.0, min(10.0, raw)), 1)
    label = _get_label(score)

    return {
        "score": score,
        "label": label,
        "breakdown": {
            "defense_score": def_score,
            "game_total_score": game_total_score,
            "implied_total_score": implied_score,
            "defense_weight": w["defense"],
            "game_total_weight": w["game_total"],
            "implied_total_weight": w["implied_total"],
        },
    }
