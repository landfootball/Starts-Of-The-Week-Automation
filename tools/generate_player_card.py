"""
Player matchup log card — matches clean_flat_v1 design system.

Same visual language as generate_def_card.py:
  - Dark neutral surfaces, no team color bleed into panels
  - Team color: radial glow, top rule, eyebrow chip border, logo circle, accent bars
  - FPTS colored green/yellow/red by position thresholds
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from card_utils import (
    CARD_W, OUTER_PAD, SCALE,
    RANK_GREEN, RANK_YELLOW, RANK_RED,
    WHITE,
    load_font, hex_to_rgb,
    load_team_map, load_fantasylan_watermark,
    draw_logo_circle,
    build_token_map, draw_radial_glow,
)
from PIL import Image, ImageDraw

OUTPUT_DIR    = ROOT / "output"
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

STATS_PAD_V =  20
ROW_H       =  84    # taller than def card — week label + name + subtext
FOOTER_H    =  54
BOX_MARGIN  =  14
BOX_RADIUS  =  10
SIDE_PAD    =  18

LOGO_OD = 118
LOGO_ID = 112
LOGO_SZ =  76

SZ_EYEBROW   = 11
SZ_NAME_MAX  = 46
SZ_NAME_MIN  = 18
SZ_NAME_STEP =  2
SZ_SUBTITLE  = 10
SZ_WEEK      =  9
SZ_PLAYER    = 22
SZ_SUBTEXT   =  9
SZ_FPTS      = 24
SZ_FOOTER    = 12

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

def _fpts_color(fpts: float, position: str) -> str:
    thresholds = {
        "QB": (20.0, 12.0),
        "RB": (15.0,  8.0),
        "WR": (15.0,  8.0),
        "TE": (12.0,  6.0),
    }
    good, bad = thresholds.get(position, (15.0, 8.0))
    if fpts >= good:
        return RANK_GREEN
    elif fpts >= bad:
        return RANK_YELLOW
    return RANK_RED

def _format_subtext(line: dict, position: str) -> str:
    if position in ("WR", "TE"):
        rec = int(line.get("rec", 0))
        yds = int(line.get("rec_yd", 0))
        td  = int(line.get("rec_td", 0))
        return f"{rec} REC  \u2022  {yds} YDs  \u2022  {td} TD"
    elif position == "RB":
        att    = int(line.get("rush_att", 0))
        yds    = int(line.get("rush_yd", 0))
        td     = int(line.get("rush_td", 0))
        rec    = int(line.get("rec", 0))
        rec_yd = int(line.get("rec_yd", 0))
        base   = f"{att} CAR  \u2022  {yds} YDs  \u2022  {td} TD"
        return base + (f"  |  {rec} REC, {rec_yd} YDs" if rec > 0 else "")
    elif position == "QB":
        cmp  = int(line.get("pass_cmp", 0))
        att  = int(line.get("pass_att", 0))
        yds  = int(line.get("pass_yd", 0))
        td   = int(line.get("pass_td", 0))
        ints = int(line.get("pass_int", 0))
        return f"{cmp}/{att}  \u2022  {yds} YDs  \u2022  {td} TD  \u2022  {ints} INT"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_player_card(
    def_team_name: str,
    position: str,
    player_lines: list[dict],
    season: int = 2025,
    output_path: Path | None = None,
) -> Path:

    n = len(player_lines)
    if n == 0:
        raise ValueError("player_lines must not be empty.")

    team_map     = load_team_map()
    tokens       = build_token_map(def_team_name, team_map)
    team_primary = tokens["team_primary"]
    tr, tg, tb  = hex_to_rgb(team_primary)

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
    rows_top   = box_top + STATS_PAD_V * SCALE

    # Eyebrow chip
    ew_font  = load_font("rubik", "semibold", SZ_EYEBROW)
    ew_text  = f"{position} MATCHUP STATS"
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
    parts  = def_team_name.upper().split()
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
    sub_text = f"OPPOSING DEFENSE  \u2022  {season} SEASON  \u2022  WEEKS 1\u201318"
    sub_bb   = draw.textbbox((0, 0), sub_text, font=sub_font)
    draw.text((name_x, sub_y - sub_bb[1]), sub_text, font=sub_font, fill=C_SUBTITLE)

    # Header separator
    draw.rectangle([ox, box_top - SCALE, ox + CARD_W, box_top], fill=C_HEADER_SEP)

    # Logo circle
    draw_logo_circle(img, draw, def_team_name, logo_cx, logo_cy, team_primary,
                     outer_d=LOGO_OD, inner_d=LOGO_ID, logo_size=LOGO_SZ)

    # Player rows
    week_font   = load_font("rubik", "medium",  SZ_WEEK)
    player_font = load_font("rubik", "black",   SZ_PLAYER)
    sub_tf      = load_font("rubik", "regular", SZ_SUBTEXT)
    fpts_font   = load_font("rubik", "black",   SZ_FPTS, italic=True)

    bar_h_px = int(ROW_H * SCALE * ROW_BAR_HEIGHT_RATIO)

    for i, line in enumerate(player_lines):
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

        text_x = box_x0 + (ROW_BAR_W + ROW_BAR_TO_LABEL_GAP) * SCALE

        # Week label — top of row content area
        week_num  = line.get("week", "")
        week_text = f"WEEK {week_num}" if week_num else ""
        wkbb      = draw.textbbox((0, 0), week_text, font=week_font)
        wk_h      = wkbb[3] - wkbb[1]

        # Stack: week → player name → subtext, vertically centered in row
        player_name = line.get("name", "").upper()
        plbb        = draw.textbbox((0, 0), player_name, font=player_font)
        pl_h        = plbb[3] - plbb[1]

        subtext = _format_subtext(line, position)
        stbb    = draw.textbbox((0, 0), subtext, font=sub_tf)
        st_h    = stbb[3] - stbb[1]

        gap      = 3 * SCALE
        total_h  = wk_h + gap + pl_h + gap + st_h
        stack_y  = row_cy - total_h // 2

        draw.text((text_x, stack_y - wkbb[1]),               week_text,   font=week_font,   fill=C_SUBTITLE)
        draw.text((text_x, stack_y + wk_h + gap - plbb[1]),  player_name, font=player_font, fill=C_NAME)
        draw.text((text_x, stack_y + wk_h + gap + pl_h + gap - stbb[1]), subtext, font=sub_tf, fill=C_SUBTITLE)

        # FPTS — right-aligned, vertically centered
        fpts_val = line.get("fpts", 0.0)
        fpts_str = f"{fpts_val:.1f}"
        fpts_col = _fpts_color(fpts_val, position)
        fbbox    = draw.textbbox((0, 0), fpts_str, font=fpts_font)
        fw, fh   = fbbox[2] - fbbox[0], fbbox[3] - fbbox[1]
        f_x      = box_x1 - fw - SIDE_PAD * SCALE
        f_y      = row_cy - fh // 2 - fbbox[1]
        draw.text((f_x, f_y), fpts_str, font=fpts_font, fill=fpts_col)

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
    foot_text = f"{season} SEASON  \u2022  WEEKS 1\u201318"
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
        safe = def_team_name.lower().replace(" ", "_")
        output_path = OUTPUT_DIR / f"{safe}_player_card_{date.today()}.png"
    img.save(str(output_path), "PNG")
    return output_path
