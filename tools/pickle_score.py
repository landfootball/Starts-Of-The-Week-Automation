"""
Calculates the Pickle Score — a proprietary matchup quality metric (1.0–10.0).

Components and weights:
  - Fantasy Points Allowed (position-specific FPA slug):          40%
  - Defense Bundle (weighted average of position-relevant slugs): 30%
  - Implied Team Total (team's projected score this week):        20%
  - Game O/U (game over/under rank this week):                    10%

Final formula:
  score = clamp(1.0, 10.0, 0.40*FPA + 0.30*DEF + 0.20*IMPLIED + 0.10*OU)

Labels (matchup quality only):
  9.0–10.0: "GOAT MATCHUP"
  7.8–8.9:  "GREAT MATCHUP"
  6.2–7.7:  "SOLID MATCHUP"
  4.8–6.1:  "NEUTRAL MATCHUP"
  3.5–4.7:  "TOUGH MATCHUP"  (sub-label: "You're in a Pickle")
  1.0–3.4:  "BRUTAL MATCHUP"

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
ODDS_PATH  = ROOT / "data" / "odds" / "latest.json"
FPA_PATH   = ROOT / "data" / "fpa" / "latest.json"

# ── Top-level component weights (must sum to 1.0) ──────────────────────────────
PICKLE_WEIGHTS = {
    "fantasy_points_allowed": 0.40,
    "defense_bundle": 0.30,
    "implied_total": 0.20,
    "game_total": 0.10,
}

# ── Per-position defense bundle slug weights (each set sums to 1.0) ────────────
POSITION_DEFENSE_WEIGHTS: dict[str, dict[str, float]] = {
    "QB": {
        "opponent-passing-yards-per-game":      0.30,
        "opponent-passing-touchdowns-per-game": 0.30,
        "opponent-yards-per-pass-attempt":      0.20,
        "sacks-per-game":                       0.10,
        "interceptions-per-game":               0.10,
    },
    "RB": {
        "opponent-rushing-yards-per-game":      0.30,
        "opponent-rushing-touchdowns-per-game": 0.25,
        "opponent-yards-per-rush-attempt":      0.20,
        "opponent-red-zone-scoring-pct":        0.15,
        "opponent-points-per-game":             0.10,
    },
    "WR": {
        "opponent-passing-yards-per-game":      0.30,
        "opponent-passing-touchdowns-per-game": 0.30,
        "opponent-completions-per-game":        0.20,
        "opponent-red-zone-scoring-pct":        0.10,
        "opponent-third-down-conversion-pct":   0.10,
    },
    "TE": {
        "opponent-passing-yards-per-game":      0.30,
        "opponent-passing-touchdowns-per-game": 0.30,
        "opponent-completions-per-game":        0.20,
        "opponent-red-zone-scoring-pct":        0.10,
        "opponent-third-down-conversion-pct":   0.10,
    },
}

# Slugs where the defense doing MORE is WORSE for the fantasy player.
# Higher sacks/INTs forced = bad for opposing QB. Override higher_is_better=False.
NEGATIVE_FACTOR_SLUGS: frozenset[str] = frozenset({"sacks-per-game", "interceptions-per-game"})

TOTAL_TEAMS = 32


# ── Low-level helpers ──────────────────────────────────────────────────────────

def _rank_to_score(rank: int | float, total: int = TOTAL_TEAMS, higher_is_better: bool = True) -> float:
    """
    Convert a rank (1–total) to a 0–10 score.
    higher_is_better=True:  rank 1 = 10.0 (best matchup), rank total = 0.0
    higher_is_better=False: rank 1 = 0.0  (worst matchup), rank total = 10.0
    """
    rank = max(1, min(total, int(rank)))  # clamp defensively
    if higher_is_better:
        return round(10.0 * (total - rank) / max(total - 1, 1), 2)
    else:
        return round(10.0 * (rank - 1) / max(total - 1, 1), 2)


# ── Component scorers ──────────────────────────────────────────────────────────

def calculate_defense_bundle_score(
    def_team_name: str, position: str, stats_data: dict
) -> tuple[float, dict]:
    """
    Weighted average of position-relevant defensive stat scores (0–10).
    Renormalizes by used weights only when slugs are missing.
    Returns (score, diagnostics_dict).
    """
    slug_weights = POSITION_DEFENSE_WEIGHTS.get(position, {})
    team_stats = stats_data.get(def_team_name, {})

    used_weight = 0.0
    weighted_sum = 0.0
    slugs_used: list[str] = []
    slugs_missing: list[str] = []

    for slug, weight in slug_weights.items():
        stat = team_stats.get(slug)
        if not stat or "rank" not in stat:
            slugs_missing.append(slug)
            continue

        # Negative factors override the stat payload's higher_is_better
        if slug in NEGATIVE_FACTOR_SLUGS:
            hib = False
        else:
            hib = stat.get("higher_is_better", True)

        sub_score = _rank_to_score(stat["rank"], higher_is_better=hib)
        weighted_sum += sub_score * weight
        used_weight += weight
        slugs_used.append(slug)

    if used_weight == 0.0:
        return 5.0, {"slugs_used": [], "slugs_missing": list(slug_weights.keys())}

    # Renormalize so missing slugs don't dilute the result
    score = round(weighted_sum / used_weight, 2)
    return score, {"slugs_used": slugs_used, "slugs_missing": slugs_missing}


def calculate_fantasy_points_allowed_score(
    def_team_name: str, position: str, fpa_data: dict
) -> float:
    """
    Score (0–10) based on FPA rank from FantasyPros (full PPR).

    Ranking convention (matches user's convention and FantasyPros):
      Rank 1  = most points allowed = BEST matchup  → score 10.0
      Rank 32 = fewest points allowed = WORST matchup → score 0.0

    Falls back to 5.0 (neutral) when data is absent — expected in offseason.
    """
    team_data = fpa_data.get(def_team_name, {})
    pos_data = team_data.get(position) if isinstance(team_data, dict) else None

    if not pos_data or "rank" not in pos_data:
        return 5.0

    # Rank 1 = most points allowed = BEST matchup = score 10.0
    # _rank_to_score with higher_is_better=True: rank 1 → 10.0, rank 32 → 0.0
    return _rank_to_score(pos_data["rank"], higher_is_better=True)


def _game_total_score(off_team_name: str, odds_data: dict) -> float:
    """Score (0–10) based on game O/U rank. Returns 5.0 if data absent (offseason)."""
    if not odds_data:
        return 5.0
    team_data = odds_data.get("teams", {}).get(off_team_name)
    if not team_data or not team_data.get("game_total_rank"):
        return 5.0
    rank = team_data["game_total_rank"]
    total_games = len(odds_data.get("games", []))
    if total_games == 0:
        return 5.0
    return round(10.0 * (total_games - rank) / max(total_games - 1, 1), 2)


def _implied_total_score(off_team_name: str, odds_data: dict) -> float:
    """Score (0–10) based on implied team total rank. Returns 5.0 if data absent (offseason)."""
    if not odds_data:
        return 5.0
    team_data = odds_data.get("teams", {}).get(off_team_name)
    if not team_data or not team_data.get("implied_total_rank"):
        return 5.0
    rank = team_data["implied_total_rank"]
    total_teams = len(odds_data.get("teams", {}))
    if total_teams == 0:
        return 5.0
    return round(10.0 * (total_teams - rank) / max(total_teams - 1, 1), 2)


def _get_label(score: float) -> str:
    if score >= 9.0:
        return "Pickles says GOAT MATCHUP"
    elif score >= 7.8:
        return "Pickles says GREAT MATCHUP"
    elif score >= 6.2:
        return "Pickles says SOLID MATCHUP"
    elif score >= 4.8:
        return "Pickles says NEUTRAL MATCHUP"
    elif score >= 3.5:
        return "Pickles says TOUGH MATCHUP"
    else:
        return "Pickles says BRUTAL MATCHUP"


def _get_sublabel(score: float) -> str | None:
    """Returns a sub-label for TOUGH MATCHUP only, None otherwise."""
    if 3.5 <= score < 4.8:
        return "You're in a Pickle"
    return None


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_position_stats(stats_data: dict) -> list[str]:
    """
    Check that slugs in POSITION_DEFENSE_WEIGHTS exist in scraped data.
    Returns a list of warning strings for any missing slugs.
    Called at startup or after data refresh.
    """
    warnings: list[str] = []
    all_slugs: set[str] = set()
    for team, team_stats in stats_data.items():
        if team == "_meta" or not isinstance(team_stats, dict):
            continue
        all_slugs.update(team_stats.keys())

    for position, slug_weights in POSITION_DEFENSE_WEIGHTS.items():
        for slug in slug_weights:
            if slug not in all_slugs:
                warnings.append(
                    f"Pickle Score ({position}): slug '{slug}' not found in scraped data"
                )
    return warnings


# ── Public API ─────────────────────────────────────────────────────────────────

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
        weights: Optional override for top-level PICKLE_WEIGHTS dict.

    Returns:
        {
          "score": 7.2,
          "label": "SOLID MATCHUP",
          "sublabel": None,          # "You're in a Pickle" for TOUGH MATCHUP only
          "breakdown": {
            "fantasy_points_allowed_score": 5.0,
            "defense_bundle_score": 8.1,
            "implied_total_score": 7.5,
            "game_total_score": 6.0,
            "fantasy_points_allowed_weight": 0.40,
            "defense_bundle_weight": 0.30,
            "implied_total_weight": 0.20,
            "game_total_weight": 0.10,
            "stats_used": {"slugs_used": [...], "slugs_missing": [...]},
          }
        }
    """
    w = weights or PICKLE_WEIGHTS

    stats_data: dict = {}
    if STATS_PATH.exists():
        with open(STATS_PATH) as f:
            stats_data = json.load(f)

    odds_data: dict = {}
    if ODDS_PATH.exists():
        with open(ODDS_PATH) as f:
            odds_data = json.load(f)

    fpa_data: dict = {}
    if FPA_PATH.exists():
        with open(FPA_PATH) as f:
            fpa_data = json.load(f)

    fpa_score = calculate_fantasy_points_allowed_score(def_team_name, position, fpa_data)
    def_score, stats_diag = calculate_defense_bundle_score(def_team_name, position, stats_data)
    implied_score = _implied_total_score(off_team_name, odds_data)
    game_score = _game_total_score(off_team_name, odds_data)

    raw = (
        fpa_score    * w["fantasy_points_allowed"]
        + def_score  * w["defense_bundle"]
        + implied_score * w["implied_total"]
        + game_score * w["game_total"]
    )

    score = round(max(1.0, min(10.0, raw)), 1)
    label    = _get_label(score)
    sublabel = _get_sublabel(score)

    return {
        "score": score,
        "label": label,
        "sublabel": sublabel,
        "breakdown": {
            "fantasy_points_allowed_score": fpa_score,
            "defense_bundle_score": def_score,
            "implied_total_score": implied_score,
            "game_total_score": game_score,
            "fantasy_points_allowed_weight": w["fantasy_points_allowed"],
            "defense_bundle_weight": w["defense_bundle"],
            "implied_total_weight": w["implied_total"],
            "game_total_weight": w["game_total"],
            "stats_used": stats_diag,
        },
    }


# ── CLI entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    SAMPLE_MATCHUPS = [
        ("Dallas Cowboys",   "Los Angeles Rams", "QB"),
        ("Dallas Cowboys",   "Los Angeles Rams", "RB"),
        ("Dallas Cowboys",   "Los Angeles Rams", "WR"),
        ("Dallas Cowboys",   "Los Angeles Rams", "TE"),
    ]

    print("=== Pickle Score Sample Output ===\n")
    for def_t, off_t, pos in SAMPLE_MATCHUPS:
        result = calculate_pickle_score(def_t, off_t, pos)
        bd = result["breakdown"]
        print(f"{pos}: {off_t} vs {def_t} DEF")
        print(f"  Score : {result['score']}  |  {result['label']}")
        print(
            f"  FPA={bd['fantasy_points_allowed_score']} ({int(bd['fantasy_points_allowed_weight']*100)}%)  "
            f"DEF={bd['defense_bundle_score']} ({int(bd['defense_bundle_weight']*100)}%)  "
            f"Implied={bd['implied_total_score']} ({int(bd['implied_total_weight']*100)}%)  "
            f"OU={bd['game_total_score']} ({int(bd['game_total_weight']*100)}%)"
        )
        used = bd["stats_used"]["slugs_used"]
        missing = bd["stats_used"]["slugs_missing"]
        print(f"  DEF slugs: {len(used)} used, {len(missing)} missing", end="")
        if missing:
            print(f" {missing}", end="")
        print("\n")
