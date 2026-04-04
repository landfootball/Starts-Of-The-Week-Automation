"""
Generates a branded defensive stats card PNG.

Usage (from Streamlit):
    from tools.generate_def_card import generate_def_card
    path = generate_def_card(
        team_name="Seattle Seahawks",
        position="WR",
        stat_slugs=["opponent-passing-yards-per-game", "opponent-points-per-game"],
        season=2025,
    )
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from card_utils import (
    CARD_W, OUTER_PAD, SCALE,
    CARD_BG_ALT, DIVIDER, GRAY_LABEL, GRAY_SUBTITLE, BLACK,
    load_font, rank_color, ordinal,
    load_team_map, load_team_logo, load_fantasylan_watermark,
    make_card_canvas, draw_pill_badge, draw_divider,
)

DATA_PATH = ROOT / "data" / "stats" / "latest.json"
OUTPUT_DIR = ROOT / "output"

# Layout constants (logical px, will be × SCALE internally via load_font)
HEADER_H   = 120 * SCALE   # team name + subtitle + gap
DIVIDER_Y_OFFSET = 108 * SCALE
ROW_H      = 80 * SCALE    # height of each stat row
FOOTER_H   = 60 * SCALE    # season label + watermark


def generate_def_card(
    team_name: str,
    position: str,
    stat_slugs: list[str],
    season: int = 2025,
    output_path: Path | None = None,
) -> Path:

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Stats data not found at {DATA_PATH}. Run tools/scrape_teamrankings.py first."
        )
    with open(DATA_PATH) as f:
        all_stats = json.load(f)

    # Read metadata written by the scraper
    meta = all_stats.get("_meta", {})
    nfl_week = meta.get("nfl_week")
    data_season = meta.get("season", season)

    team_stats = all_stats.get(team_name)
    if not team_stats:
        raise ValueError(f"Team '{team_name}' not found in stats data.")

    team_map = load_team_map()
    team_info = team_map.get(team_name, {})
    primary_color = team_info.get("primary", "#333333")

    # Filter to requested slugs with data
    rows = [team_stats[slug] for slug in stat_slugs if slug in team_stats]
    if not rows:
        raise ValueError(f"No matching stats found for slugs: {stat_slugs}")

    # ── Dynamic card height ────────────────────────────────────────────────────
    n = len(rows)
    card_h = DIVIDER_Y_OFFSET + (n * ROW_H) + FOOTER_H + (20 * SCALE)

    img, draw, (cx, cy) = make_card_canvas(card_h)

    # ── Team color accent bar (top of card) ───────────────────────────────────
    CARD_RADIUS = 24 * SCALE
    BAR_H = 8 * SCALE
    draw.rounded_rectangle(
        [cx, cy, cx + CARD_W, cy + CARD_RADIUS + BAR_H],
        radius=CARD_RADIUS,
        fill=primary_color,
        corners=(True, True, False, False),
    )
    # Restore cream below the visible bar
    from card_utils import CARD_BG
    draw.rectangle(
        [cx, cy + BAR_H, cx + CARD_W, cy + CARD_RADIUS + BAR_H],
        fill=CARD_BG,
    )

    # ── Team logo (top right) ──────────────────────────────────────────────────
    logo = load_team_logo(team_name, size=(88, 88))
    if logo:
        logo_x = cx + CARD_W - (20 * SCALE) - logo.width
        logo_y = cy + (24 * SCALE)
        img.paste(logo, (logo_x, logo_y), logo)

    # ── Header ─────────────────────────────────────────────────────────────────
    hx = cx + (28 * SCALE)
    hy = cy + (28 * SCALE)

    team_font = load_font("tommy", "extrabold", 34)
    draw.text((hx, hy), team_name, font=team_font, fill=primary_color)

    sub_font = load_font("tommy", "bold", 13)
    sub_text = f"{position} MATCHUP STATS"
    draw.text((hx, hy + (44 * SCALE)), sub_text, font=sub_font, fill=primary_color)

    div_y = cy + DIVIDER_Y_OFFSET
    draw_divider(draw, cx, div_y)

    # ── Stat rows ──────────────────────────────────────────────────────────────
    label_font = load_font("serif", "regular", 13)
    value_font = load_font("tommy", "bold", 26)
    badge_font = load_font("tommy", "bold", 13)

    row_start = div_y + (8 * SCALE)

    for i, stat in enumerate(rows):
        ry = row_start + i * ROW_H

        if i % 2 == 1:
            draw.rectangle(
                [cx + SCALE, ry, cx + CARD_W - SCALE, ry + ROW_H],
                fill=CARD_BG_ALT,
            )

        # Label
        label_text = stat["label"].upper()
        label_y = ry + (ROW_H - (16 * SCALE)) // 2
        draw.text((cx + (28 * SCALE), label_y), label_text, font=label_font, fill=GRAY_LABEL)

        rank = stat["rank"]
        badge_color = rank_color(rank)
        badge_text = ordinal(rank)
        value_text = stat.get("value_display", str(stat["value"]))
        value_color = badge_color

        # Measure value text
        vbbox = draw.textbbox((0, 0), value_text, font=value_font)
        val_w = vbbox[2] - vbbox[0]

        # Measure badge
        bbbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        badge_content_w = bbbox[2] - bbbox[0]
        badge_pill_w = badge_content_w + (28 * SCALE)

        right_pad = 28 * SCALE
        gap = 12 * SCALE

        badge_x = cx + CARD_W - right_pad - badge_pill_w
        badge_y = ry + (ROW_H - (28 * SCALE)) // 2

        value_x = badge_x - gap - val_w
        value_y = ry + (ROW_H - (32 * SCALE)) // 2

        draw.text((value_x, value_y), value_text, font=value_font, fill=value_color)
        draw_pill_badge(draw, badge_text, badge_x, badge_y, badge_color, badge_font)

        if i < n - 1:
            draw_divider(draw, cx, ry + ROW_H)

    # ── Footer ─────────────────────────────────────────────────────────────────
    footer_y = cy + card_h - FOOTER_H
    draw_divider(draw, cx, footer_y)

    season_font = load_font("serif", "regular", 11)
    if nfl_week:
        footer_text = f"WEEKS 1–{nfl_week} · {data_season} NFL SEASON"
    else:
        footer_text = f"{season} NFL SEASON"
    draw.text(
        (cx + (28 * SCALE), footer_y + (12 * SCALE)),
        footer_text,
        font=season_font,
        fill=GRAY_LABEL,
    )

    watermark = load_fantasylan_watermark(max_width=110)
    if watermark:
        wm_x = cx + CARD_W - watermark.width - (20 * SCALE)
        wm_y = footer_y + (FOOTER_H - watermark.height) // 2
        img.paste(watermark, (wm_x, wm_y), watermark)

    # ── Save ───────────────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        safe = team_name.lower().replace(" ", "_")
        output_path = OUTPUT_DIR / f"{safe}_def_card_{date.today()}.png"

    img.save(str(output_path), "PNG")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", required=True)
    parser.add_argument("--position", default="WR", choices=["QB", "RB", "WR", "TE"])
    parser.add_argument("--stats", default="")
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    if args.stats:
        slugs = [s.strip() for s in args.stats.split(",")]
    else:
        from scrape_teamrankings import STATS
        slugs = [s for s, m in STATS.items() if args.position in m["positions"]]

    out = generate_def_card(
        team_name=args.team,
        position=args.position,
        stat_slugs=slugs,
        season=args.season,
        output_path=Path(args.output) if args.output else None,
    )
    print(f"Generated: {out}")


if __name__ == "__main__":
    main()
