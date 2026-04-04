"""
Scrapes TeamRankings.com for NFL defensive stats (opponent-facing).
Fetches all stat pages, extracts rank + value for all 32 teams,
and saves to data/stats/latest.json.

Usage:
    python tools/scrape_teamrankings.py
"""

import json
import time
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "stats"
TEAM_MAP_PATH = ROOT / "config" / "team_map.json"

# ── Stats to scrape ────────────────────────────────────────────────────────────
STATS = {
    "opponent-points-per-game": {
        "label": "Points Allowed/G",
        "positions": ["QB", "RB", "WR", "TE"],
        "higher_is_better": True,   # higher rank = more allowed = better matchup
    },
    "opponent-total-yards-per-game": {
        "label": "Total Yards Allowed/G",
        "positions": ["QB", "RB", "WR", "TE"],
        "higher_is_better": True,
    },
    "opponent-passing-yards-per-game": {
        "label": "Pass Yards Allowed/G",
        "positions": ["QB", "WR", "TE"],
        "higher_is_better": True,
    },
    "opponent-rushing-yards-per-game": {
        "label": "Rush Yards Allowed/G",
        "positions": ["RB"],
        "higher_is_better": True,
    },
    "opponent-yards-per-rush-attempt": {
        "label": "Yards/Carry Allowed",
        "positions": ["RB"],
        "higher_is_better": True,
    },
    "opponent-passing-touchdowns-per-game": {
        "label": "Pass TDs Allowed/G",
        "positions": ["QB", "WR", "TE"],
        "higher_is_better": True,
    },
    "opponent-rushing-touchdowns-per-game": {
        "label": "Rush TDs Allowed/G",
        "positions": ["RB"],
        "higher_is_better": True,
    },
    "opponent-receptions-per-game": {
        "label": "Receptions Allowed/G",
        "positions": ["WR", "TE"],
        "higher_is_better": True,
    },
    "opponent-passer-rating-allowed": {
        "label": "Passer Rating Allowed",
        "positions": ["QB"],
        "higher_is_better": True,
    },
    "opponent-third-down-conversion-pct": {
        "label": "3rd Down Conv % Allowed",
        "positions": ["QB", "RB", "WR", "TE"],
        "higher_is_better": True,
    },
}

BASE_URL = "https://www.teamrankings.com/nfl/stat/{slug}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# TeamRankings team name → canonical team name mapping
# TeamRankings sometimes uses shortened names
TEAMRANKINGS_NAME_MAP: dict[str, str] = {}


def _build_tr_name_map() -> None:
    """Build a reverse lookup from TeamRankings display name to canonical name."""
    with open(TEAM_MAP_PATH) as f:
        team_map = json.load(f)
    for canonical, info in team_map.items():
        TEAMRANKINGS_NAME_MAP[info["teamrankings"].lower()] = canonical


def _fetch_stat_page(slug: str) -> list[dict]:
    """
    Fetch a single TeamRankings stat page and return a list of:
      {team_tr_name, rank, value}
    """
    url = BASE_URL.format(slug=slug)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # The main data table has class "tr-table datatable scrollable"
    table = soup.find("table", {"class": re.compile(r"tr-table")})
    if not table:
        raise ValueError(f"Could not find data table on {url}")

    rows = table.find("tbody").find_all("tr")
    results = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        rank_text = cols[0].get_text(strip=True)
        team_text = cols[1].get_text(strip=True)
        value_text = cols[2].get_text(strip=True)

        # rank might be "1" or "1st" — strip non-numeric
        rank_clean = re.sub(r"[^\d]", "", rank_text)
        if not rank_clean:
            continue

        # value might be "231.1" or "47.0%" — keep as string for now
        value_clean = value_text.replace(",", "").strip()

        results.append({
            "team_tr": team_text.strip(),
            "rank": int(rank_clean),
            "value": value_clean,
        })

    return results


def _parse_value(value_str: str) -> float:
    """Convert value string to float, stripping % signs etc."""
    cleaned = value_str.replace("%", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def scrape_all_stats() -> dict:
    """
    Scrape all stats for all 32 teams.

    Returns:
        {
          "Arizona Cardinals": {
            "opponent-points-per-game": {"label": "...", "value": 24.1, "rank": 3, "higher_is_better": True},
            ...
          },
          ...
        }
    """
    _build_tr_name_map()

    # Initialise output keyed by canonical team name
    with open(TEAM_MAP_PATH) as f:
        team_map = json.load(f)
    output: dict = {team: {} for team in team_map}

    for slug, meta in STATS.items():
        print(f"  Fetching: {slug} ...", end=" ", flush=True)
        try:
            rows = _fetch_stat_page(slug)
        except Exception as e:
            print(f"FAILED ({e})")
            continue

        matched = 0
        for row in rows:
            tr_name = row["team_tr"].lower()
            # Try exact match first
            canonical = TEAMRANKINGS_NAME_MAP.get(tr_name)
            # Try partial match if exact fails
            if not canonical:
                for tr_key, can_val in TEAMRANKINGS_NAME_MAP.items():
                    if tr_key in tr_name or tr_name in tr_key:
                        canonical = can_val
                        break
            if not canonical:
                continue

            output[canonical][slug] = {
                "label": meta["label"],
                "value": _parse_value(row["value"]),
                "value_display": row["value"],
                "rank": row["rank"],
                "higher_is_better": meta["higher_is_better"],
                "positions": meta["positions"],
            }
            matched += 1

        print(f"OK ({matched} teams)")
        time.sleep(1.2)  # polite delay between requests

    return output


def main() -> None:
    print("=== TeamRankings Scraper ===")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = scrape_all_stats()

    out_path = DATA_DIR / "latest.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    # Count how many stats were populated
    total = sum(len(v) for v in data.values())
    print(f"\nSaved {out_path}")
    print(f"Stats populated: {total} ({total // 32} stats × 32 teams)")


if __name__ == "__main__":
    main()
