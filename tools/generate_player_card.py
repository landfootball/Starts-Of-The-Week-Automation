"""
Generates a branded player log card PNG.

Shows recent player performances against a specific defense,
formatted as: "Name: X REC, X YDs, X TD | X.X FPTS"

Usage (from Streamlit / other tools):
    from tools.generate_player_card import generate_player_card

    player_lines = [
        {"name": "Justin Jefferson", "rec": 6, "rec_yd": 112, "rec_td": 1, "fpts": 26.2},
        {"name": "Amon-Ra St. Brown", "rec": 8, "rec_yd": 88, "rec_td": 0, "fpts": 16.8},
    ]
    path = generate_player_card(
        def_team_name="Seattle Seahawks",
        position="WR",
        player_lines=player_lines,
        season=2025,
    )
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from card_utils import (
    CARD_BG, CARD_BG_ALT, DIVIDER, GRAY_LABEL, GRAY_SUBTITLE, BLACK, WHITE,
    CARD_W, CARD_H, OUTER_PAD,
    load_font, hex_to_rgb, rank_color, ordinal,
    load_team_map, load_team_logo, load_fantasylan_watermark,
    make_card_canvas, draw_pill_badge, draw_divider,
    RANK_GREEN,
)

OUTPUT_DIR = ROOT / "output"

# FPTS colours
FPTS_GREEN = RANK_GREEN      # solid scorer
FPTS_YELLOW = "#B8860B"     # neutral (dark gold — readable on cream)
FPTS_RED = "#C62828"        # bust

def _fpts_color(fpts: float, position: str) -> str:
    """Return colour for FPTS value based on position thresholds."""
    thresholds = {
        "QB":  (20.0, 12.0),
        "RB":  (15.0, 8.0),
        "WR":  (15.0, 8.0),
        "TE":  (12.0, 6.0),
    }
    good, bad = thresholds.get(position, (15.0, 8.0))
    if fpts >= good:
        return FPTS_GREEN
    elif fpts >= bad:
        return FPTS_YELLOW
    else:
        return FPTS_RED


def _format_line(line: dict, position: str) -> tuple[str, str]:
    """
    Format a player stat line into two strings:
      prefix: "Justin Jefferson: 6 REC, 112 YDs, 1 TD"
      fpts:   "26.2 FPTS"
    """
    name = line.get("name", "Unknown")

    if position in ("WR", "TE"):
        rec = int(line.get("rec", 0))
        yds = int(line.get("rec_yd", 0))
        td = int(line.get("rec_td", 0))
        prefix = f"{name}: {rec} REC, {yds} YDs, {td} TD"
    elif position == "RB":
        att = int(line.get("rush_att", 0))
        yds = int(line.get("rush_yd", 0))
        td = int(line.get("rush_td", 0))
        rec = int(line.get("rec", 0))
        rec_yd = int(line.get("rec_yd", 0))
        if rec > 0:
            prefix = f"{name}: {att} CAR, {yds} YDs, {td} TD | {rec} REC, {rec_yd} YDs"
        else:
            prefix = f"{name}: {att} CAR, {yds} YDs, {td} TD"
    elif position == "QB":
        cmp = int(line.get("pass_cmp", 0))
        att = int(line.get("pass_att", 0))
        yds = int(line.get("pass_yd", 0))
        td = int(line.get("pass_td", 0))
        ints = int(line.get("pass_int", 0))
        prefix = f"{name}: {cmp}/{att}, {yds} YDs, {td} TD, {ints} INT"
    else:
        prefix = name

    fpts_val = line.get("fpts", 0.0)
    fpts_str = f"{fpts_val:.1f} FPTS"
    return prefix, fpts_str


def generate_player_card(
    def_team_name: str,
    position: str,
    player_lines: list[dict],
    season: int = 2025,
    output_path: Path | None = None,
) -> Path:
    """
    Generate the player log card PNG.

    Args:
        def_team_name: The defensive team, e.g. "Seattle Seahawks"
        position: "QB", "RB", "WR", or "TE"
        player_lines: List of dicts with player stats (keyed by standard stat names)
        season: NFL season year
        output_path: Override output file path

    Returns:
        Path to the generated PNG.
    """
    team_map = load_team_map()
    team_info = team_map.get(def_team_name, {})
    primary_color = team_info.get("primary", "#333333")

    # ── Canvas ─────────────────────────────────────────────────────────────────
    img, draw, (cx, cy) = make_card_canvas()

    # ── Team logo (top right) ──────────────────────────────────────────────────
    logo = load_team_logo(def_team_name, size=(96, 96))
    logo_x = cx + CARD_W - 24 - (logo.width if logo else 80)
    logo_y = cy + 28
    if logo:
        img.paste(logo, (logo_x, logo_y), logo)

    # ── Header ─────────────────────────────────────────────────────────────────
    header_x = cx + 28
    header_y = cy + 30

    # e.g. "Seattle Seahawks" in primary colour
    team_font = load_font("tommy", "extrabold", 34)
    draw.text((header_x, header_y), def_team_name, font=team_font, fill=primary_color)

    # Subtitle: "Defense vs WRs"
    sub_font = load_font("tommy", "bold", 17)
    sub_text = f"Defense vs {position}s"
    sub_y = header_y + 44
    draw.text((header_x, sub_y), sub_text, font=sub_font, fill=primary_color)

    divider_y = cy + 108
    draw_divider(draw, cx, divider_y)

    # ── Player rows ────────────────────────────────────────────────────────────
    row_start_y = divider_y + 12
    n_rows = len(player_lines)
    row_height = min(
        (CARD_H - (row_start_y - cy) - 80) // max(n_rows, 1),
        80,
    )
    row_height = max(row_height, 56)

    line_font = load_font("tommy", "bold", 18)
    fpts_font = load_font("tommy", "extrabold", 18)

    for i, line in enumerate(player_lines):
        row_y = row_start_y + i * row_height

        # Alternating background
        if i % 2 == 1:
            draw.rectangle([cx + 1, row_y, cx + CARD_W - 1, row_y + row_height], fill=CARD_BG_ALT)

        prefix, fpts_str = _format_line(line, position)
        fpts_val = line.get("fpts", 0.0)
        fpts_col = _fpts_color(fpts_val, position)

        text_y = row_y + (row_height - 22) // 2

        # Measure FPTS portion for right-alignment
        separator = " | "
        sep_font = load_font("tommy", "bold", 18)

        # Draw stat prefix (black)
        draw.text((cx + 28, text_y), prefix, font=line_font, fill=BLACK)

        # Draw " | " separator
        prefix_bbox = draw.textbbox((0, 0), prefix, font=line_font)
        prefix_w = prefix_bbox[2] - prefix_bbox[0]
        sep_x = cx + 28 + prefix_w
        draw.text((sep_x, text_y), separator, font=sep_font, fill=GRAY_SUBTITLE)

        sep_bbox = draw.textbbox((0, 0), separator, font=sep_font)
        sep_w = sep_bbox[2] - sep_bbox[0]

        # Draw FPTS value in colour
        draw.text((sep_x + sep_w, text_y), fpts_str, font=fpts_font, fill=fpts_col)

        if i < n_rows - 1:
            draw_divider(draw, cx, row_y + row_height)

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
        safe_name = def_team_name.lower().replace(" ", "_")
        output_path = OUTPUT_DIR / f"{safe_name}_player_card_{date.today()}.png"

    img.save(str(output_path), "PNG")
    return output_path
