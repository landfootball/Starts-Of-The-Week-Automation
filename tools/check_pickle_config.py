"""
Validates that the Pickle Score configuration is aligned with scraped data.

Usage:
    python tools/check_pickle_config.py

Exits non-zero only if ALL core slugs for ALL positions are completely absent
(i.e. data/stats/latest.json is empty or missing entirely).
Missing individual slugs print warnings but do not fail — they fall back to 5.0.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
STATS_PATH = ROOT / "data" / "stats" / "latest.json"
ODDS_PATH = ROOT / "data" / "odds" / "latest.json"

sys.path.insert(0, str(ROOT / "tools"))
from pickle_score import POSITION_DEFENSE_WEIGHTS, NEGATIVE_FACTOR_SLUGS


def main() -> int:
    print("=== Pickle Score Config Check ===\n")
    exit_code = 0

    # ── Stats data ─────────────────────────────────────────────────────────────
    if not STATS_PATH.exists():
        print("WARNING: data/stats/latest.json not found — run weekly scrape first.\n")
        stats_data = {}
    else:
        with open(STATS_PATH) as f:
            stats_data = json.load(f)
        meta = stats_data.get("_meta", {})
        print(
            f"Stats data : season={meta.get('season', '?')}, "
            f"week={meta.get('nfl_week', '?')}, "
            f"type={meta.get('season_type', '?')}, "
            f"scraped={meta.get('scraped_at', '?')}\n"
        )

    # Gather all slugs present across any team
    all_slugs: set[str] = set()
    for team, v in stats_data.items():
        if team != "_meta" and isinstance(v, dict):
            all_slugs.update(v.keys())

    # Check per position
    total_checked = 0
    total_missing = 0

    for pos, slug_weights in POSITION_DEFENSE_WEIGHTS.items():
        print(f"[{pos}]")
        for slug, weight in slug_weights.items():
            total_checked += 1
            flag = " NEG" if slug in NEGATIVE_FACTOR_SLUGS else "    "
            if slug in all_slugs:
                print(f"  ✓{flag} {slug} ({int(weight * 100)}%)")
            else:
                print(f"  ✗{flag} {slug} ({int(weight * 100)}%)  ← MISSING")
                total_missing += 1
        print()

    # ── Odds data ──────────────────────────────────────────────────────────────
    if not ODDS_PATH.exists():
        print("INFO: data/odds/latest.json not found — expected during offseason.\n")
    else:
        with open(ODDS_PATH) as f:
            odds_data = json.load(f)
        n_games = len(odds_data.get("games", []))
        n_teams = len(odds_data.get("teams", {}))
        print(f"Odds data  : {n_games} game(s), {n_teams} team(s)\n")

    # ── Summary ────────────────────────────────────────────────────────────────
    present = total_checked - total_missing
    print(f"Summary: {present}/{total_checked} defense-bundle slugs present across all positions.")

    if total_checked > 0 and total_missing == total_checked:
        print("ERROR: No configured slugs found in data — run scrape first.")
        exit_code = 1
    elif total_missing > 0:
        print(
            f"WARNING: {total_missing} slug(s) missing. "
            "These positions will use a neutral 5.0 fallback for missing stats."
        )
    else:
        print("All configured slugs present. ✓")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
