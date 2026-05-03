"""
Game Odds card — matches clean_flat_v1 design system.

Same visual language as generate_def_card.py:
  - Dark neutral surfaces, no team color bleed into panels
  - Team color: radial glow, top rule, eyebrow chip border, logo circle, accent bars
  - Rank pills: green/yellow/red only
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from card_utils import (
    CARD_W, OUTER_PAD, SCALE,
    WHITE,
    load_font, rank_color, rank_bg_color, ordinal, hex_to_rgb,
    load_team_map, load_fantasylan_watermark,
    draw_rank_pill, draw_logo_circle,
    build_token_map, draw_radial_glow,
)
from PIL import Image, ImageDraw

DATA_PATH  = ROOT / "data" / "odds" / "latest.json"
OUTPUT_DIR = ROOT / "output"
STYLE_VERSION = "clean_flat_v1"

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS — identical to def card
# ─────────────────────────────────────────────────────────────────────────────
C_PAGE      = "#0a0a0a"
C_CARD      = "#111111"
C_PANEL     = None          # clean_flat_v1: NO panel fill
C_DIVIDER   = "#333333"
C_HEADER_SEP= "#222222"
C_TAG_BG    = "#1a1a1a"
C_NAME      = "#ffffff"
C_LABEL     = "#e0e0e0"
C_VALUE     = "#ffffff"
C_SUBTITLE  = "#7a7a7a"
C_FOOTER    = "#7a7a7a"

assert STYLE_VERSION == "clean_flat_v1" and C_PANEL is None, \
    "Panel fill must be None in clean_flat_v1"

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT — logical px; ×SCALE = rendered pixels
# ─────────────────────────────────────────────────────────────────────────────
HEADER_H          = 190
TITLE_TOP_PAD     =  28
TITLE_LINE_HEIGHT =  52
SUBTITLE_Y_OFFSET =  16

STATS_PAD_V =  24
ROW_H       =  66
FOOTER_H    =  54
BOX_MARGIN  =  14
BOX_RADIUS  =  10
SIDE_PAD    =  18

LOGO_OD = 118
LOGO_ID = 112
LOGO_SZ =  76

PILL_W  =  68
PILL_H  =  24
PILL_L  = (CARD_W // SCALE) - BOX_MARGIN - 8 - PILL_W
VALUE_R = PILL_L - 14

SZ_EYEBROW  = 11
SZ_NAME_MAX = 46
SZ_NAME_MIN = 18
SZ_NAME_STEP=  2
SZ_SUBTITLE = 10
SZ_LABEL    = 13
SZ_VALUE    = 22
SZ_RANK     = 12
SZ_FOOTER   = 12

# ─────────────────────────────────────────────────────────────────────────────
# ACCENT SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
GLOW_RADIUS    = 340
GLOW_MAX_ALPHA =  22
TOP_RULE_H     =   2

ROW_LEFT_ACCENT_MODE = "all_rows"   # "all_rows" | "none"
ROW_BAR_W            =   3
ROW_BAR_ALPHA        =  90
ROW_BAR_HEIGHT_RATIO =  0.52
ROW_BAR_TO_LABEL_GAP =  10

assert ROW_LEFT_ACCENT_MODE in ("all_rows", "none"), \
    f"ROW_LEFT_ACCENT_MODE must be 'all_rows' or 'none', got {ROW_LEFT_ACCENT_MODE!r}"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _logo_cx(ox):
    return ox + ((CARD_W // SCALE) - BOX_MARGIN - LOGO_OD // 2) * SCALE

def _logo_cy(oy):
    return oy + (HEADER_H // 2 + 2) * SCALE

def _fit_name(draw, text: str, max_w_px: int):
    size = SZ_NAME_MAX
    while size >= SZ_NAME_MIN:
        font = load_font("rubik", "black", size)
        bb = draw.textbbox((0, 0), text, font=font)
        if (bb[2] - bb[0]) <= max_w_px:
            return font
        size -= SZ_NAME_STEP
    return load_font("rubik", "black", SZ_NAME_MIN)


# ─────────────────────────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_odds_card(
    off_team_name: str,
    season: int = 2025,
    output_path: Path | None = None,
) -> Path:

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Odds data not found at {DATA_PATH}. Run tools/scrape_odds.py first."
        )
    with open(DATA_PATH) as f:
        odds_data = json.load(f)

    team_data = odds_data.get("teams", {}).get(off_team_name)
    if not team_data:
        raise ValueError(f"No odds data found for '{off_team_name}'.")

    nfl_week = odds_data.get("_meta", {}).get("nfl_week")

    raw_rows = [
        {"label": "Game Total (O/U)",   "value": team_data.get("game_total"),    "rank": team_data.get("game_total_rank")},
        {"label": "Team Implied Total", "value": team_data.get("implied_total"),  "rank": team_data.get("implied_total_rank")},
        {"label": "Spread",             "value": team_data.get("spread"),          "rank": team_data.get("spread_rank")},
        {"label": "Moneyline",          "value": team_data.get("moneyline"),       "rank": team_data.get("moneyline_rank")},
    ]
    rows = [r for r in raw_rows if r["value"] not in (None, "N/A", "None", "")]
    for r in rows:
        r["value"] = str(r["value"])
    n = len(rows)
    if n == 0:
        raise ValueError(f"No valid odds rows for '{off_team_name}'.")

    team_map     = load_team_map()
    tokens       = build_token_map(off_team_name, team_map)
    team_primary = tokens["team_primary"]

    # Canvas
    card_h_l = HEADER_H + STATS_PAD_V + n * ROW_H + STATS_PAD_V + FOOTER_H
    card_h   = card_h_l * SCALE
    img_w    = CARD_W + OUTER_PAD * 2
    img_h    = card_h + OUTER_PAD * 2

    img  = Image.new("RGB", (img_w, img_h), C_PAGE)
    draw = ImageDraw.Draw(img)
    ox, oy = OUTER_PAD, OUTER_PAD

    # Card body
    draw.rounded_rectangle(
        [ox, oy, ox + CARD_W, oy + card_h],
        radius=BOX_RADIUS * SCALE, fill=C_CARD,
    )

    # Radial glow
    img = draw_radial_glow(
        img, ox + int(CARD_W * 0.75), oy,
        radius=GLOW_RADIUS * SCALE,
        color_hex=team_primary,
        max_alpha=GLOW_MAX_ALPHA,
    )
    draw = ImageDraw.Draw(img)

    # Top rule
    tr, tg, tb = hex_to_rgb(team_primary)
    rule_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rule_draw  = ImageDraw.Draw(rule_layer)
    rule_draw.rectangle(
        [ox, oy, ox + CARD_W, oy + TOP_RULE_H * SCALE],
        fill=(tr, tg, tb, 217),
    )
    img  = Image.alpha_composite(img.convert("RGBA"), rule_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Pixel anchors
    logo_cx    = _logo_cx(ox)
    logo_cy    = _logo_cy(oy)
    logo_left  = logo_cx - LOGO_OD // 2 * SCALE
    name_x     = ox + SIDE_PAD * SCALE
    name_max_w = logo_left - name_x - 10 * SCALE
    box_x0     = ox + BOX_MARGIN * SCALE
    box_x1     = ox + ((CARD_W // SCALE) - BOX_MARGIN) * SCALE
    box_top    = oy + HEADER_H * SCALE
    footer_top = box_top + (STATS_PAD_V + n * ROW_H + STATS_PAD_V) * SCALE
    px_pill_l  = ox + PILL_L * SCALE
    px_value_r = ox + VALUE_R * SCALE
    rows_top   = box_top + STATS_PAD_V * SCALE

    # Eyebrow chip
    ew_font  = load_font("rubik", "semibold", SZ_EYEBROW)
    ew_text  = "GAME ODDS"
    ewbb     = draw.textbbox((0, 0), ew_text, font=ew_font)
    ew_pad_x, ew_pad_y = 12 * SCALE, 6 * SCALE
    ew_w  = (ewbb[2] - ewbb[0]) + ew_pad_x * 2
    ew_h  = (ewbb[3] - ewbb[1]) + ew_pad_y * 2
    ew_x  = box_x1 - ew_w
    ew_y  = oy + TITLE_TOP_PAD * SCALE
    chip_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    chip_draw  = ImageDraw.Draw(chip_layer)
    chip_draw.rounded_rectangle(
        [ew_x, ew_y, ew_x + ew_w, ew_y + ew_h],
        radius=5 * SCALE, fill=(*hex_to_rgb(C_TAG_BG), 255),
        outline=(*hex_to_rgb(team_primary), 128), width=SCALE,
    )
    img  = Image.alpha_composite(img.convert("RGBA"), chip_layer).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((ew_x + ew_pad_x, ew_y + ew_pad_y - ewbb[1]), ew_text, font=ew_font, fill=WHITE)

    # Team name
    parts  = off_team_name.upper().split()
    line1  = " ".join(parts[:-1]) if len(parts) >= 2 else parts[0]
    line2  = parts[-1]            if len(parts) >= 2 else ""
    check  = load_font("rubik", "black", SZ_NAME_MAX)
    longest   = max([line1] + ([line2] if line2 else []),
                    key=lambda t: draw.textbbox((0, 0), t, font=check)[2])
    name_font = _fit_name(draw, longest, name_max_w)

    title_y = oy + TITLE_TOP_PAD * SCALE
    l1bb    = draw.textbbox((0, 0), line1, font=name_font)
    draw.text((name_x, title_y - l1bb[1]), line1, font=name_font, fill=C_NAME)
    if line2:
        line2_y = title_y + TITLE_LINE_HEIGHT * SCALE
        l2bb    = draw.textbbox((0, 0), line2, font=name_font)
        draw.text((name_x, line2_y - l2bb[1]), line2, font=name_font, fill=C_NAME)
        last_title_bottom = line2_y + (l2bb[3] - l2bb[1])
    else:
        last_title_bottom = title_y + (l1bb[3] - l1bb[1])

    sub_y    = last_title_bottom + SUBTITLE_Y_OFFSET * SCALE
    sub_font = load_font("rubik", "medium", SZ_SUBTITLE)
    week_label = f"WEEK {nfl_week}" if nfl_week else "CURRENT WEEK"
    sub_text   = f"BETTING LINES  \u2022  {week_label}"
    sub_bb   = draw.textbbox((0, 0), sub_text, font=sub_font)
    draw.text((name_x, sub_y - sub_bb[1]), sub_text, font=sub_font, fill=C_SUBTITLE)

    # Header separator
    draw.rectangle([ox, box_top - SCALE, ox + CARD_W, box_top], fill=C_HEADER_SEP)

    # Logo circle
    draw_logo_circle(img, draw, off_team_name, logo_cx, logo_cy, team_primary,
                     outer_d=LOGO_OD, inner_d=LOGO_ID, logo_size=LOGO_SZ)

    # Stat rows
    label_font = load_font("rubik", "semibold", SZ_LABEL)
    value_font = load_font("rubik", "black",    SZ_VALUE, italic=True)
    rank_font  = load_font("rubik", "bold",     SZ_RANK)

    bar_h_px = int(ROW_H * SCALE * ROW_BAR_HEIGHT_RATIO)

    for i, row in enumerate(rows):
        row_top = rows_top + i * ROW_H * SCALE
        row_cy  = row_top + ROW_H * SCALE // 2

        # Left accent bar — every row, identical specs
        if ROW_LEFT_ACCENT_MODE == "all_rows":
            bar_top   = row_cy - bar_h_px // 2
            bar_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            bar_draw  = ImageDraw.Draw(bar_layer)
            bar_draw.rectangle(
                [box_x0, bar_top, box_x0 + ROW_BAR_W * SCALE, bar_top + bar_h_px],
                fill=(tr, tg, tb, ROW_BAR_ALPHA),
            )
            img  = Image.alpha_composite(img.convert("RGBA"), bar_layer).convert("RGB")
            draw = ImageDraw.Draw(img)

        # Label
        label_x = box_x0 + (ROW_BAR_W + ROW_BAR_TO_LABEL_GAP) * SCALE
        lbbox   = draw.textbbox((0, 0), row["label"], font=label_font)
        lh      = lbbox[3] - lbbox[1]
        draw.text((label_x, row_cy - lh // 2 - lbbox[1]), row["label"], font=label_font, fill=C_LABEL)

        # Rank pill
        rank = row.get("rank")
        if rank:
            pill_y = row_cy - PILL_H * SCALE // 2
            draw_rank_pill(draw, ordinal(rank), px_pill_l, pill_y, rank, rank_font,
                           w=PILL_W, h=PILL_H)

        # Value
        val_x_r = px_value_r if rank else (box_x1 - SIDE_PAD * SCALE)
        vbbox   = draw.textbbox((0, 0), row["value"], font=value_font)
        vw, vh  = vbbox[2] - vbbox[0], vbbox[3] - vbbox[1]
        draw.text((val_x_r - vw, row_cy - vh // 2 - vbbox[1]), row["value"], font=value_font, fill=C_VALUE)

        # Row divider
        if i < n - 1:
            div_y = row_top + ROW_H * SCALE
            draw.line([(box_x0 + 10 * SCALE, div_y), (box_x1 - 10 * SCALE, div_y)],
                      fill=C_DIVIDER, width=max(1, SCALE // 2))

    # Footer
    draw.rounded_rectangle(
        [ox, footer_top, ox + CARD_W, oy + card_h],
        radius=BOX_RADIUS * SCALE, fill=C_CARD,
        corners=(False, False, True, True),
    )
    foot_font = load_font("rubik", "medium", SZ_FOOTER)
    foot_text = f"{season} SEASON  \u2022  {week_label}"
    ftbb      = draw.textbbox((0, 0), foot_text, font=foot_font)
    ft_h      = ftbb[3] - ftbb[1]
    FOOTER_BASELINE = oy + card_h - 18 * SCALE
    draw.text((ox + SIDE_PAD * SCALE, FOOTER_BASELINE - ft_h - ftbb[1]),
              foot_text, font=foot_font, fill=C_FOOTER)

    watermark = load_fantasylan_watermark(max_width=52)
    if watermark:
        wm_x = ox + CARD_W - watermark.width - SIDE_PAD * SCALE
        wm_y = FOOTER_BASELINE - watermark.height
        img.paste(watermark, (wm_x, wm_y), watermark)

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        safe = off_team_name.lower().replace(" ", "_")
        output_path = OUTPUT_DIR / f"{safe}_odds_card_{date.today()}.png"
    img.save(str(output_path), "PNG")
    return output_path
