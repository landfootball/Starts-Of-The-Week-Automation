"""
Fetches current NFL game odds from The Odds API.
Extracts:
  - Game over/under (total) for each matchup
  - Implied team point totals for each team
  - Rankings among all games this week

Saves to data/odds/latest.json.

Usage:
    python tools/scrape_odds.py

Requires:
    ODDS_API_KEY in .env (or Streamlit secrets in production)
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "odds"
TEAM_MAP_PATH = ROOT / "config" / "team_map.json"

load_dotenv(ROOT / ".env")

# ── The Odds API config ────────────────────────────────────────────────────────
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_BASE = "https://api.the-odds-api.com/v4"
SPORT = "americanfootball_nfl"
REGIONS = "us"
MARKETS = "totals,h2h"       # totals = game O/U; h2h for implied totals calculation
ALT_MARKETS = "team_totals"  # direct implied team totals market

# ── Preferred bookmaker ────────────────────────────────────────────────────────
# Set ODDS_BOOKMAKER in .env (or GitHub secret) to pin to a specific sportsbook.
# Common Odds API keys: fanduel, draftkings, betmgm, caesars, williamhill_us,
#                       novig, pointsbetus, betrivers, unibet_us
# If not set or the book isn't found for a game, falls back to any available book.
PREFERRED_BOOKMAKER = os.getenv("ODDS_BOOKMAKER", "fanduel")


# ── TeamRankings name → canonical team name lookup ────────────────────────────
def _load_team_map() -> dict:
    with open(TEAM_MAP_PATH) as f:
        return json.load(f)


def _build_abbrev_lookup(team_map: dict) -> dict[str, str]:
    """sleeper_id/abbreviation → canonical team name"""
    lookup = {}
    for canonical, info in team_map.items():
        lookup[info["sleeper_id"]] = canonical
        lookup[info["abbreviation"]] = canonical
    return lookup


def _match_team_name(name: str, team_map: dict) -> str | None:
    """Match an Odds API team name string to a canonical team name."""
    name_lower = name.lower()
    for canonical in team_map:
        # Try city/nickname match
        parts = canonical.lower().split()
        if any(p in name_lower for p in parts[-2:]):  # last 1-2 words of team name
            return canonical
        if canonical.lower() in name_lower or name_lower in canonical.lower():
            return canonical
    return None


def fetch_game_odds(api_key: str) -> list[dict]:
    """Fetch game totals from The Odds API."""
    url = f"{ODDS_BASE}/sports/{SPORT}/odds"
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": "american",
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_team_totals(api_key: str) -> list[dict]:
    """Fetch team total (implied score) markets from The Odds API."""
    url = f"{ODDS_BASE}/sports/{SPORT}/odds"
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": ALT_MARKETS,
        "oddsFormat": "american",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        # team_totals market may not always be available — fall back gracefully
        return []


def _sorted_bookmakers(game: dict) -> list[dict]:
    """Return bookmakers list with preferred book first, others after."""
    books = game.get("bookmakers", [])
    preferred = [b for b in books if b.get("key") == PREFERRED_BOOKMAKER]
    others    = [b for b in books if b.get("key") != PREFERRED_BOOKMAKER]
    return preferred + others


def _extract_game_total(game: dict) -> float | None:
    """Pull the over/under total from a game's bookmakers data, preferring PREFERRED_BOOKMAKER."""
    for bookmaker in _sorted_bookmakers(game):
        for market in bookmaker.get("markets", []):
            if market["key"] == "totals":
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == "Over":
                        return float(outcome.get("point", 0))
    return None


def _extract_team_totals_from_h2h(game: dict) -> tuple[float | None, float | None]:
    """
    Derive implied team totals from h2h moneylines + game total.
    Formula: implied_home = total * (away_win_prob / (home_win_prob + away_win_prob))
    This is an approximation — direct team_totals market is more accurate when available.
    """
    game_total = _extract_game_total(game)
    if not game_total:
        return None, None

    # Try to find h2h odds
    for bookmaker in _sorted_bookmakers(game):
        for market in bookmaker.get("markets", []):
            if market["key"] == "h2h":
                outcomes = market.get("outcomes", [])
                if len(outcomes) >= 2:
                    # Convert American odds to implied probability
                    def american_to_prob(odds: int) -> float:
                        if odds > 0:
                            return 100 / (odds + 100)
                        else:
                            return abs(odds) / (abs(odds) + 100)

                    home_team = game["home_team"]
                    away_team = game["away_team"]
                    probs = {}
                    for o in outcomes:
                        try:
                            probs[o["name"]] = american_to_prob(int(o["price"]))
                        except (KeyError, ValueError):
                            pass

                    if home_team in probs and away_team in probs:
                        total_prob = probs[home_team] + probs[away_team]
                        home_share = probs[home_team] / total_prob
                        away_share = probs[away_team] / total_prob
                        # Higher moneyline prob = better team = scores more
                        home_implied = round(game_total * home_share, 1)
                        away_implied = round(game_total * away_share, 1)
                        return home_implied, away_implied
    return None, None


def _extract_direct_team_totals(game: dict) -> dict[str, float]:
    """Extract implied totals from the team_totals market (more accurate), preferring PREFERRED_BOOKMAKER."""
    totals = {}
    for bookmaker in _sorted_bookmakers(game):
        for market in bookmaker.get("markets", []):
            if market["key"] == "team_totals":
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == "Over":
                        team = outcome.get("description", "")
                        totals[team] = float(outcome.get("point", 0))
    return totals


def build_odds_data(api_key: str, team_map: dict) -> dict:
    """
    Fetch and process all odds data.

    Returns:
        {
          "games": [
            {
              "home_team": "Kansas City Chiefs",
              "away_team": "Las Vegas Raiders",
              "game_total": 51.5,
              "game_total_rank": 1,
              "home_implied": 28.2,
              "away_implied": 23.3,
            }
          ],
          "teams": {
            "Kansas City Chiefs": {
              "implied_total": 28.2,
              "implied_total_rank": 1,
              "game_total": 51.5,
              "game_total_rank": 1,
              "opponent": "Las Vegas Raiders"
            }
          }
        }
    """
    print("  Fetching game odds ...", end=" ", flush=True)
    games_raw = fetch_game_odds(api_key)
    print(f"OK ({len(games_raw)} games)")

    print("  Fetching team totals ...", end=" ", flush=True)
    team_totals_raw = fetch_team_totals(api_key)
    # Build a lookup: event_id → direct team totals
    direct_totals: dict[str, dict] = {}
    for g in team_totals_raw:
        event_id = g.get("id", "")
        direct = _extract_direct_team_totals(g)
        if direct:
            direct_totals[event_id] = direct
    print(f"OK ({len(direct_totals)} games with team totals)")

    processed_games = []
    for g in games_raw:
        home_canonical = _match_team_name(g["home_team"], team_map)
        away_canonical = _match_team_name(g["away_team"], team_map)

        if not home_canonical or not away_canonical:
            continue

        game_total = _extract_game_total(g)
        if not game_total:
            continue

        event_id = g.get("id", "")
        direct = direct_totals.get(event_id, {})

        # Try direct team totals first, fall back to h2h derivation
        if direct:
            # Match direct totals to home/away
            home_implied = None
            away_implied = None
            for team_name, total in direct.items():
                if _match_team_name(team_name, team_map) == home_canonical:
                    home_implied = total
                elif _match_team_name(team_name, team_map) == away_canonical:
                    away_implied = total
        else:
            home_implied, away_implied = _extract_team_totals_from_h2h(g)

        processed_games.append({
            "home_team": home_canonical,
            "away_team": away_canonical,
            "game_total": game_total,
            "home_implied": home_implied,
            "away_implied": away_implied,
        })

    # Rank games by game total (descending — highest O/U = rank 1)
    sorted_by_total = sorted(processed_games, key=lambda x: x["game_total"], reverse=True)
    for i, g in enumerate(sorted_by_total, 1):
        g["game_total_rank"] = i

    # Collect all team implied totals for ranking
    team_implied: list[tuple[str, float, str]] = []  # (team, implied, opponent)
    for g in processed_games:
        if g["home_implied"] is not None:
            team_implied.append((g["home_team"], g["home_implied"], g["away_team"]))
        if g["away_implied"] is not None:
            team_implied.append((g["away_team"], g["away_implied"], g["home_team"]))

    team_implied.sort(key=lambda x: x[1], reverse=True)

    # Build teams dict
    teams: dict = {}
    for rank, (team, implied, opponent) in enumerate(team_implied, 1):
        # Find this team's game total and rank
        game_total_val = None
        game_total_rank = None
        for g in processed_games:
            if team in (g["home_team"], g["away_team"]):
                game_total_val = g["game_total"]
                game_total_rank = g["game_total_rank"]
                break
        teams[team] = {
            "implied_total": implied,
            "implied_total_rank": rank,
            "game_total": game_total_val,
            "game_total_rank": game_total_rank,
            "opponent": opponent,
        }

    return {
        "games": processed_games,
        "teams": teams,
        "_meta": {"bookmaker": PREFERRED_BOOKMAKER},
    }


def main() -> None:
    print("=== Odds Scraper ===")

    if not ODDS_API_KEY:
        print("ERROR: ODDS_API_KEY not set in .env")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    team_map = _load_team_map()

    data = build_odds_data(ODDS_API_KEY, team_map)

    out_path = DATA_DIR / "latest.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved {out_path}")
    print(f"Games processed: {len(data['games'])}")
    print(f"Teams with implied totals: {len(data['teams'])}")


if __name__ == "__main__":
    main()
