"""
Generates a branded over/under + implied team totals card PNG.

Shows the game total (O/U) and both teams' implied scoring totals,
ranked against all other games this week.

Usage (from Streamlit / other tools):
    from tools.generate_odds_card import generate_odds_card
    path = generate_odds_card(
        off_team_name="Los Angeles Rams",
        season=2025,
    )
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from card_utils import (
    CARD_BG, CARD_BG_ALT, DIVIDER, GRAY_LABEL, GRAY_SUBTITLE, BLACK, WHITE,
    CARD_W, CARD_H, OUTER_PAD,
    load_font, rank_color, ordinal,
    load_team_map, load_team_logo, load_fantasylan_watermark,
    make_card_canvas, draw_pill_badge, draw_divider,
    RANK_GREEN,
)

DATA_PATH = ROOT / "data" / "odds" / "latest.json"
OUTPUT_DIR = ROOT / "output"


def generate_odds_card(
    off_team_name: str,
    season: int = 2025,
    output_path: Path | None = None,
) -> Path:
    """
    Generate the odds / implied totals card.

    Args:
        off_team_name: The OFFENSIVE team (the player's team), e.g. "Los Angeles Rams"
        season: NFL season year
        output_path: Override output file path

    Returns:
        Path to the generated PNG.
    """
    # ── Load data ──────────────────────────────────────────────────────────────
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Odds data not found at {DATA_PATH}. "
            "Run tools/scrape_odds.py first."
        )
    with open(DATA_PATH) as f:
        odds_data = json.load(f)

    team_data = odds_data.get("teams", {}).get(off_team_name)
    if not team_data:
        raise ValueError(f"No odds data found for '{off_team_name}'.")

    opponent_name = team_data.get("opponent", "Opponent")

    # Also pull opponent's implied total
    opp_data = odds_data.get("teams", {}).get(opponent_name, {})

    team_map = load_team_map()
    off_info = team_map.get(off_team_name, {})
    opp_info = team_map.get(opponent_name, {})

    primary_color = off_info.get("primary", "#333333")
    secondary_color = off_info.get("secondary", "#888888")

    # ── Canvas ─────────────────────────────────────────────────────────────────
    img, draw, (cx, cy) = make_card_canvas()

    # ── Both team logos (top area) ─────────────────────────────────────────────
    off_logo = load_team_logo(off_team_name, size=(72, 72))
    opp_logo = load_team_logo(opponent_name, size=(72, 72))

    # Offensive team logo: top right
    off_logo_x = cx + CARD_W - 24 - (off_logo.width if off_logo else 72)
    off_logo_y = cy + 28
    if off_logo:
        img.paste(off_logo, (off_logo_x, off_logo_y), off_logo)

    # ── Header ─────────────────────────────────────────────────────────────────
    header_x = cx + 28
    header_y = cy + 30

    team_font = load_font("tommy", "extrabold", 34)
    draw.text((header_x, header_y), off_team_name, font=team_font, fill=primary_color)

    sub_font = load_font("tommy", "bold", 16)
    draw.text((header_x, header_y + 44), "GAME ODDS & TOTALS", font=sub_font, fill=primary_color)

    divider_y = cy + 108
    draw_divider(draw, cx, divider_y)

    # ── Stats ──────────────────────────────────────────────────────────────────
    value_font = load_font("tommy", "extrabold", 42)
    label_font = load_font("serif", "regular", 14)
    sub2_font = load_font("tommy", "bold", 15)
    badge_font = load_font("tommy", "bold", 15)

    rows = [
        {
            "label": "GAME OVER/UNDER",
            "value": f"{team_data['game_total']}" if team_data.get("game_total") else "N/A",
            "rank": team_data.get("game_total_rank"),
            "context": f"vs {opponent_name}",
        },
        {
            "label": f"{off_team_name.split()[-1].upper()} IMPLIED TOTAL",
            "value": f"{team_data['implied_total']}" if team_data.get("implied_total") else "N/A",
            "rank": team_data.get("implied_total_rank"),
            "context": "points projected to score",
        },
        {
            "label": f"{opponent_name.split()[-1].upper()} IMPLIED TOTAL",
            "value": f"{opp_data.get('implied_total', 'N/A')}",
            "rank": opp_data.get("implied_total_rank"),
            "context": "opponent projected to score",
        },
    ]

    row_start_y = divider_y + 16
    row_height = (CARD_H - (row_start_y - cy) - 100) // 3

    for i, row in enumerate(rows):
        row_y = row_start_y + i * row_height

        if i % 2 == 1:
            draw.rectangle([cx + 1, row_y, cx + CARD_W - 1, row_y + row_height], fill=CARD_BG_ALT)

        # Label
        draw.text((cx + 28, row_y + 16), row["label"].upper(), font=label_font, fill=GRAY_LABEL)

        # Context (small)
        draw.text(
            (cx + 28, row_y + row_height - 26),
            row["context"],
            font=load_font("serif", "regular", 12),
            fill=GRAY_SUBTITLE,
        )

        # Value (large, centred vertically)
        val_str = str(row["value"])
        val_color = primary_color
        draw.text((cx + 28, row_y + 36), val_str, font=value_font, fill=val_color)

        # Rank badge (right)
        rank = row.get("rank")
        if rank:
            badge_text = f"{ordinal(rank)} highest"
            # For game total + off implied: higher = better for fantasy
            badge_col = rank_color(rank)
            badge_x = cx + CARD_W - 28 - (len(badge_text) * 11 + 30)
            badge_y = row_y + (row_height - 30) // 2
            draw_pill_badge(draw, badge_text, badge_x, badge_y, badge_col, badge_font)

        if i < len(rows) - 1:
            draw_divider(draw, cx, row_y + row_height)

    # ── Opponent logo + label at bottom ───────────────────────────────────────
    matchup_y = cy + CARD_H - 90
    draw_divider(draw, cx, matchup_y)

    vs_font = load_font("tommy", "bold", 14)
    draw.text((cx + 28, matchup_y + 10), f"MATCHUP: vs {opponent_name.upper()}", font=vs_font, fill=GRAY_SUBTITLE)

    if opp_logo:
        opp_logo_small = load_team_logo(opponent_name, size=(44, 44))
        if opp_logo_small:
            img.paste(opp_logo_small, (cx + CARD_W - 60, matchup_y + 6), opp_logo_small)

    # ── Footer ─────────────────────────────────────────────────────────────────
    footer_y = cy + CARD_H - 50
    draw_divider(draw, cx, footer_y - 8)

    season_font = load_font("serif", "regular", 13)
    draw.text((cx + 28, footer_y), f"{season} NFL SEASON", font=season_font, fill=GRAY_LABEL)

    watermark = load_fantasylan_watermark(max_width=130)
    if watermark:
        wm_x = cx + CARD_W - watermark.width - 20
        wm_y = footer_y - (watermark.height - 14) // 2
        img.paste(watermark, (wm_x, wm_y), watermark)

    # ── Save ───────────────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        safe_name = off_team_name.lower().replace(" ", "_")
        output_path = OUTPUT_DIR / f"{safe_name}_odds_card_{date.today()}.png"

    img.save(str(output_path), "PNG")
    return output_path
