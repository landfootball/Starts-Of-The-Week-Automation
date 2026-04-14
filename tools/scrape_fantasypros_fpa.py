"""
Scrapes FFToday Fantasy Points Allowed (FPA) — full PPR scoring.

Source: https://www.fftoday.com/stats/fantasystats.php
        ?Season=2025&GameWeek=Season&PosID={pid}&Side=Allowed&LeagueID=107644

LeagueID=107644 = FFToday PPR (confirmed via their dropdown).

Table ranking convention (matches user's convention):
  Rank 1 = most fantasy points allowed = BEST matchup to target
  Rank 32 = fewest fantasy points allowed = WORST matchup

All 32 teams are present in static HTML — no JavaScript required.

Saves to data/fpa/latest.json keyed by canonical team name:
{
  "Dallas Cowboys": {
    "QB": {"avg": 26.7, "rank": 1},
    "RB": {"avg": ...},
    ...
  },
  ...
  "_meta": {"scraped_at": "...", "scoring": "PPR", "source": "..."}
}

Usage:
    python tools/scrape_fantasypros_fpa.py
"""

import json
import re
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "fpa"
TEAM_MAP_PATH = ROOT / "config" / "team_map.json"

BASE_URL = (
    "https://www.fftoday.com/stats/fantasystats.php"
    "?Season={season}&GameWeek=Season&PosID={pid}&Side=Allowed&LeagueID=107644"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.fftoday.com/",
}

# FFToday PosID values
POSITIONS = {
    "QB": 10,
    "RB": 20,
    "WR": 30,
    "TE": 40,
}

# FFToday uses "Cowboys vs. QB" style team names — extract the city/name before " vs."
_VS_RE = re.compile(r"^\d+\.\s*(.+?)\s+vs\.\s+", re.IGNORECASE)


def _build_name_map() -> dict:
    """
    Build lookup from FFToday display name (lowercase) → canonical name.
    FFToday uses shortened names like "Cowboys", "Bears", etc.
    We match against the last word(s) of canonical names.
    """
    with open(TEAM_MAP_PATH) as f:
        team_map = json.load(f)

    name_map: dict = {}
    for canonical in team_map:
        # Full canonical name
        name_map[canonical.lower()] = canonical
        # Last word (e.g. "Cowboys", "Bears", "Patriots")
        last = canonical.split()[-1]
        name_map[last.lower()] = canonical
        # Two-word suffix for teams like "49ers", "Chiefs"
        if len(canonical.split()) >= 2:
            two = " ".join(canonical.split()[-2:])
            name_map[two.lower()] = canonical

    return name_map


def _fetch_position(position: str, season: int) -> list[dict]:
    """
    Scrape FPA for a single position. Returns list of {team_raw, rank, avg, games}.
    """
    pid = POSITIONS[position]
    url = BASE_URL.format(season=season, pid=pid)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    tables = soup.find_all("table")

    # Find the data table: look for the table with 30+ rows of consistent column count
    # Column count varies by position (QB=12, RB/WR/TE=10) — always last col = FPts/G
    data_table = None
    dominant_col_count = 0
    for t in tables:
        rows = t.find_all("tr")
        from collections import Counter
        counts = Counter(len(r.find_all("td")) for r in rows if r.find_all("td"))
        if not counts:
            continue
        most_common_count, most_common_freq = counts.most_common(1)[0]
        if most_common_freq >= 30 and most_common_count >= 8:
            data_table = t
            dominant_col_count = most_common_count
            break

    if not data_table:
        raise ValueError(f"Could not find FPA data table for {position} on FFToday")

    results = []
    for row in data_table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) != dominant_col_count:
            continue
        team_raw = cols[0].get_text(strip=True)
        # Skip header rows
        if not team_raw or team_raw.lower().startswith("team"):
            continue

        # Extract rank and team name: "1.Cowboys vs. QB" → rank=1, team="Cowboys"
        rank_match = re.match(r"^(\d+)\.", team_raw)
        if not rank_match:
            continue
        rank = int(rank_match.group(1))

        vs_match = _VS_RE.match(team_raw)
        team_name = vs_match.group(1).strip() if vs_match else team_raw.split(".")[1].strip()

        games_text = cols[1].get_text(strip=True)
        fpts_per_game_text = cols[-1].get_text(strip=True)  # FPts/G is always last column

        try:
            games = int(games_text)
        except ValueError:
            games = 17

        try:
            avg = float(fpts_per_game_text.replace(",", ""))
        except ValueError:
            avg = None

        if avg is not None:
            results.append({
                "team_raw": team_name,
                "rank": rank,
                "avg": avg,
                "games": games,
            })

    return results


def scrape_fpa(season: int = 2025) -> dict:
    """
    Scrape FPA for all 4 positions from FFToday (full PPR).
    Returns output dict keyed by canonical team name.
    """
    name_map = _build_name_map()

    # Initialise with all teams
    with open(TEAM_MAP_PATH) as f:
        team_map = json.load(f)
    output: dict = {team: {} for team in team_map}

    for position, pid in POSITIONS.items():
        print(f"  Fetching {position} FPA (PPR)...", end=" ", flush=True)
        try:
            rows = _fetch_position(position, season)
        except Exception as e:
            print(f"FAILED ({e})")
            continue

        matched = 0
        unmatched = []
        for row in rows:
            team_lower = row["team_raw"].lower()
            canonical = name_map.get(team_lower)

            if not canonical:
                # Try partial match
                for key, can_val in name_map.items():
                    if key in team_lower or team_lower in key:
                        canonical = can_val
                        break

            if not canonical:
                unmatched.append(row["team_raw"])
                continue

            output[canonical][position] = {
                "avg": row["avg"],
                "rank": row["rank"],
                "games": row["games"],
            }
            matched += 1

        print(f"OK ({matched}/32 matched)")
        if unmatched:
            print(f"    Unmatched: {unmatched}")

        time.sleep(1.0)  # polite delay

    output["_meta"] = {
        "scraped_at": date.today().isoformat(),
        "season": season,
        "scoring": "PPR",
        "source": "fftoday.com (LeagueID=107644)",
    }

    return output


def main() -> None:
    print("=== FFToday FPA Scraper (PPR) ===")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Detect current season from stats data if available
    stats_path = ROOT / "data" / "stats" / "latest.json"
    season = 2025
    if stats_path.exists():
        with open(stats_path) as f:
            meta = json.load(f).get("_meta", {})
        season = meta.get("season", 2025)

    print(f"Season: {season}\n")
    data = scrape_fpa(season=season)

    out_path = DATA_DIR / "latest.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved {out_path}")

    # Sanity print — first team with data
    sample = {k: v for k, v in data.items() if k != "_meta" and v}
    if sample:
        first = next(iter(sample))
        print(f"\nSample — {first}:")
        for pos, vals in sample[first].items():
            print(f"  {pos}: avg={vals['avg']} rank={vals['rank']}")


if __name__ == "__main__":
    main()
