"""
Generates a branded defensive stats card PNG for a given NFL team.

Usage (CLI):
    python tools/generate_def_card.py \
        --team "Seattle Seahawks" \
        --position WR \
        --stats "opponent-passing-yards-per-game,opponent-passing-touchdowns-per-game,opponent-points-per-game" \
        --season 2025 \
        --output output/seahawks_def_card.png

Usage (from Streamlit / other tools):
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

from PIL import Image, ImageDraw

# Allow import from sibling tools/
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from card_utils import (
    CARD_BG, CARD_BG_ALT, DIVIDER, GRAY_LABEL, GRAY_SUBTITLE, BLACK, WHITE,
    CARD_W, CARD_H, OUTER_PAD,
    load_font, hex_to_rgb, rank_color, ordinal,
    load_team_map, load_team_logo, load_fantasylan_watermark,
    make_card_canvas, draw_pill_badge, draw_divider,
)

DATA_PATH = ROOT / "data" / "stats" / "latest.json"
OUTPUT_DIR = ROOT / "output"


def generate_def_card(
    team_name: str,
    position: str,
    stat_slugs: list[str],
    season: int = 2025,
    output_path: Path | None = None,
) -> Path:
    """
    Generate the defensive stats PNG card.

    Args:
        team_name: Full team name, e.g. "Seattle Seahawks"
        position: "QB", "RB", "WR", or "TE"
        stat_slugs: List of stat slug strings to display (in order)
        season: NFL season year
        output_path: Override output file path

    Returns:
        Path to the generated PNG file.
    """
    # ── Load data ──────────────────────────────────────────────────────────────
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Stats data not found at {DATA_PATH}. "
            "Run tools/scrape_teamrankings.py first."
        )
    with open(DATA_PATH) as f:
        all_stats = json.load(f)

    team_stats = all_stats.get(team_name)
    if not team_stats:
        raise ValueError(f"Team '{team_name}' not found in stats data.")

    team_map = load_team_map()
    team_info = team_map.get(team_name, {})
    primary_color = team_info.get("primary", "#333333")
    abbreviation = team_info.get("abbreviation", "")

    # Filter to requested slugs, preserving order, skipping missing
    rows: list[dict] = []
    for slug in stat_slugs:
        stat = team_stats.get(slug)
        if stat:
            rows.append(stat)

    if not rows:
        raise ValueError(f"No matching stats found for slugs: {stat_slugs}")

    # ── Canvas ─────────────────────────────────────────────────────────────────
    img, draw, (cx, cy) = make_card_canvas()

    # ── Team logo (top right) ──────────────────────────────────────────────────
    logo = load_team_logo(team_name, size=(96, 96))
    logo_x = cx + CARD_W - 24 - (logo.width if logo else 80)
    logo_y = cy + 28
    if logo:
        img.paste(logo, (logo_x, logo_y), logo)

    # ── Header ─────────────────────────────────────────────────────────────────
    header_x = cx + 28
    header_y = cy + 30

    # Team name
    team_font = load_font("tommy", "extrabold", 38)
    draw.text((header_x, header_y), team_name, font=team_font, fill=primary_color)

    # Subtitle: "ALL CATEGORIES" or position-specific
    sub_label = "ALL CATEGORIES" if not position else f"{position} MATCHUP STATS"
    sub_font = load_font("tommy", "bold", 15)
    sub_y = header_y + 46
    draw.text((header_x, sub_y), sub_label, font=sub_font, fill=primary_color)

    # Divider below header
    divider_y = cy + 108
    draw_divider(draw, cx, divider_y)

    # ── Stat rows ──────────────────────────────────────────────────────────────
    row_start_y = divider_y + 8
    row_height = (CARD_H - (row_start_y - cy) - 80) // max(len(rows), 1)
    row_height = min(row_height, 72)  # cap height so rows don't get too tall
    row_height = max(row_height, 52)  # floor so they don't collapse

    label_font = load_font("serif", "regular", 14)
    value_font = load_font("tommy", "bold", 28)
    badge_font = load_font("tommy", "bold", 14)

    for i, stat in enumerate(rows):
        row_y = row_start_y + i * row_height

        # Alternating row background
        if i % 2 == 1:
            row_rect = [cx + 1, row_y, cx + CARD_W - 1, row_y + row_height]
            draw.rectangle(row_rect, fill=CARD_BG_ALT)

        # Stat label (left, vertically centred in row)
        label_text = stat["label"].upper()
        label_y = row_y + (row_height - 16) // 2
        draw.text((cx + 28, label_y), label_text, font=label_font, fill=GRAY_LABEL)

        # Rank badge (right side)
        rank = stat["rank"]
        badge_text = ordinal(rank)
        badge_color = rank_color(rank)

        # Value (centre-right, coloured by rank)
        value_text = stat.get("value_display", str(stat["value"]))
        # Value colour: use rank colour for good ranks, black for bad
        value_color = badge_color if rank <= 10 else (GRAY_SUBTITLE if rank <= 22 else BLACK)

        # Measure value text width to right-align before badge
        bbox = draw.textbbox((0, 0), value_text, font=value_font)
        val_w = bbox[2] - bbox[0]

        badge_w_est = len(badge_text) * 12 + 30  # rough estimate
        value_x = cx + CARD_W - 28 - badge_w_est - 16 - val_w
        value_y = row_y + (row_height - 34) // 2

        draw.text((value_x, value_y), value_text, font=value_font, fill=value_color)

        # Draw badge to the right of value
        badge_x = cx + CARD_W - 28 - badge_w_est
        badge_y = row_y + (row_height - 28) // 2
        draw_pill_badge(draw, badge_text, badge_x, badge_y, badge_color, badge_font)

        # Row divider (except after last row)
        if i < len(rows) - 1:
            draw_divider(draw, cx, row_y + row_height)

    # ── Footer ─────────────────────────────────────────────────────────────────
    footer_y = cy + CARD_H - 50
    draw_divider(draw, cx, footer_y - 8)

    season_font = load_font("serif", "regular", 13)
    draw.text(
        (cx + 28, footer_y),
        f"{season} NFL SEASON",
        font=season_font,
        fill=GRAY_LABEL,
    )

    # FantasyLand watermark (bottom right)
    watermark = load_fantasylan_watermark(max_width=130)
    if watermark:
        wm_x = cx + CARD_W - watermark.width - 20
        wm_y = footer_y - (watermark.height - 14) // 2
        img.paste(watermark, (wm_x, wm_y), watermark)

    # ── Save ───────────────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        safe_name = team_name.lower().replace(" ", "_")
        output_path = OUTPUT_DIR / f"{safe_name}_def_card_{date.today()}.png"

    img.save(str(output_path), "PNG")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a defensive stats card PNG")
    parser.add_argument("--team", required=True, help='Team name, e.g. "Seattle Seahawks"')
    parser.add_argument("--position", default="WR", choices=["QB", "RB", "WR", "TE"])
    parser.add_argument(
        "--stats",
        default="",
        help="Comma-separated stat slugs to display. Defaults to all position-relevant stats.",
    )
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    if args.stats:
        slugs = [s.strip() for s in args.stats.split(",")]
    else:
        # Default: all stats relevant to this position
        from scrape_teamrankings import STATS
        slugs = [s for s, meta in STATS.items() if args.position in meta["positions"]]

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
