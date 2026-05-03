"""
Defensive stats card — minimal/clean design.

Color philosophy:
  - Near-black neutral surfaces throughout (no team color tinting panels)
  - Team color appears ONLY in: logo circle inner ring + eyebrow tag text
  - All text is white or neutral gray
  - Rank pills use green/yellow/red only (never team color)
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
    RANK_GREEN, RANK_GREEN_BG,
    RANK_YELLOW, RANK_YELLOW_BG,
    RANK_RED, RANK_RED_BG,
    WHITE,
    load_font, rank_color, rank_bg_color, ordinal, hex_to_rgb,
    load_team_map, load_fantasylan_watermark,
    draw_rank_pill, draw_logo_circle,
    build_token_map, draw_radial_glow,
)
from PIL import Image, ImageDraw

DATA_PATH    = ROOT / "data" / "stats" / "latest.json"
OUTPUT_DIR   = ROOT / "output"
STYLE_VERSION = "clean_flat_v1"  # locks flat no-panel style — do not change

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS — neutral surfaces, no team color bleed
# ─────────────────────────────────────────────────────────────────────────────
C_PAGE       = "#0a0a0a"   # outer canvas
C_CARD       = "#111111"   # card body
# Panel: transparent — no fill, dividers only. Set to card bg so it blends.
C_PANEL      = None         # clean_flat_v1: NO panel fill — enforced below
C_DIVIDER    = "#333333"   # row dividers — only structure in stats area
C_HEADER_SEP = "#222222"   # header separator line
C_TAG_BG     = "#1a1a1a"   # eyebrow tag background
C_NAME       = "#ffffff"   # team name
C_LABEL      = "#e0e0e0"   # stat label — near-white
C_VALUE      = "#ffffff"   # stat value
C_SUBTITLE   = "#7a7a7a"   # subtitle / meta — clearly below label hierarchy
C_FOOTER     = "#7a7a7a"   # footer

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# All logical px; ×SCALE = rendered pixels
# ─────────────────────────────────────────────────────────────────────────────
HEADER_H     = 190   # header block — tall enough for name + subtitle + gap

# Header typography anchors — explicit, no eyeballing
TITLE_TOP_PAD       = 28   # fixed distance from card top to first title line
TITLE_LINE_HEIGHT   = 52   # fixed line-height for name lines (large font)
SUBTITLE_Y_OFFSET   = 16   # gap between bottom of last title line and subtitle
HEADER_TO_TABLE_GAP = 24   # gap between subtitle bottom and first stat row

STATS_PAD_V  =  24   # top/bottom padding inside stat area (above first / below last row)
ROW_H        =  66   # each stat row
FOOTER_H     =  54   # footer strip
BOX_MARGIN   =  14   # card edge → stat area horizontal inset
BOX_RADIUS   =  10   # reduced — less "floating card" feel
SIDE_PAD     =  18   # left text pad

# Logo circle
LOGO_OD      = 118
LOGO_ID      = 112
LOGO_SZ      =  76

# Column anchors (logical px from card left)
PILL_W       =  68
PILL_H       =  24
PILL_L       = (CARD_W // SCALE) - BOX_MARGIN - 8 - PILL_W
VALUE_R      = PILL_L - 14

# Font sizes
SZ_EYEBROW   = 11
SZ_NAME_MAX  = 46
SZ_NAME_MIN  = 18
SZ_NAME_STEP =  2
SZ_SUBTITLE  = 10
SZ_LABEL     = 13
SZ_VALUE     = 22
SZ_RANK      = 12
SZ_FOOTER    = 12

# ─────────────────────────────────────────────────────────────────────────────
# ACCENT SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
GLOW_RADIUS      = 340   # radial glow radius (logical px)
GLOW_MAX_ALPHA   =  22   # ~9% max opacity — subtle tint only
TOP_RULE_H       =   2   # team-color top rule height

# ── Left accent bar — every stat row, uniform, no exceptions ─────────────────
ROW_LEFT_ACCENT_MODE  = "all_rows"   # "all_rows" | "none" — change must be explicit
ROW_BAR_W             =   3          # bar width (logical px)
ROW_BAR_ALPHA         =  90          # opacity 0–255 (~35%) — present but not heavy
ROW_BAR_HEIGHT_RATIO  =  0.52        # bar height as fraction of ROW_H
ROW_BAR_TO_LABEL_GAP  =  10          # gap between bar right edge and label text (logical px)

assert ROW_LEFT_ACCENT_MODE in ("all_rows", "none"), \
    f"ROW_LEFT_ACCENT_MODE must be 'all_rows' or 'none', got {ROW_LEFT_ACCENT_MODE!r}"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _logo_cx(ox):
    """Logo circle center X — inset from right card edge."""
    return ox + ((CARD_W // SCALE) - BOX_MARGIN - LOGO_OD // 2) * SCALE


def _logo_cy(oy):
    """Logo circle center Y — raised 8px from midpoint for better title balance."""
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

def generate_def_card(
    team_name: str,
    position: str,
    stat_slugs: list[str],
    season: int = 2025,
    output_path: Path | None = None,
    debug: bool = False,
) -> Path:

    # Load stats
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Stats data not found at {DATA_PATH}.")
    with open(DATA_PATH) as f:
        all_stats = json.load(f)

    meta        = all_stats.get("_meta", {})
    nfl_week    = meta.get("nfl_week")
    data_season = meta.get("season", season)

    team_stats = all_stats.get(team_name)
    if not team_stats:
        raise ValueError(f"Team '{team_name}' not found in stats data.")

    rows = [team_stats[slug] for slug in stat_slugs if slug in team_stats]
    if not rows:
        raise ValueError(f"No matching stats found for slugs: {stat_slugs}")
    n = len(rows)

    # Resolve team color (for logo circle + eyebrow text only)
    team_map     = load_team_map()
    tokens       = build_token_map(team_name, team_map)
    team_primary = tokens["team_primary"]

    # Canvas
    card_h_l = HEADER_H + STATS_PAD_V + n * ROW_H + STATS_PAD_V + FOOTER_H
    card_h   = card_h_l * SCALE
    img_w    = CARD_W + OUTER_PAD * 2
    img_h    = card_h + OUTER_PAD * 2

    img  = Image.new("RGB", (img_w, img_h), C_PAGE)
    draw = ImageDraw.Draw(img)

    ox, oy = OUTER_PAD, OUTER_PAD   # card top-left corner

    # Card body (neutral near-black)
    draw.rounded_rectangle(
        [ox, oy, ox + CARD_W, oy + card_h],
        radius=BOX_RADIUS * SCALE, fill=C_CARD,
    )

    # ── Team-tinted radial glow — top-right corner near logo ─────────────────
    # Applied before all other elements so everything draws on top of it.
    glow_cx = ox + int(CARD_W * 0.75)   # x: 75% across card width
    glow_cy = oy                         # y: top edge of card
    img = draw_radial_glow(
        img, glow_cx, glow_cy,
        radius=GLOW_RADIUS * SCALE,
        color_hex=team_primary,
        max_alpha=GLOW_MAX_ALPHA,
    )
    draw = ImageDraw.Draw(img)   # re-bind after composite

    # ── Team-color top rule — 85% opacity so it's refined, not heavy ─────────
    rule_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rule_draw  = ImageDraw.Draw(rule_layer)
    tr, tg, tb = hex_to_rgb(team_primary)
    rule_draw.rectangle(
        [ox, oy, ox + CARD_W, oy + TOP_RULE_H * SCALE],
        fill=(tr, tg, tb, 217),   # 217/255 ≈ 85%
    )
    img  = Image.alpha_composite(img.convert("RGBA"), rule_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Precompute pixel anchors
    logo_cx     = _logo_cx(ox)
    logo_cy     = _logo_cy(oy)
    logo_left   = logo_cx - LOGO_OD // 2 * SCALE   # leftmost px of logo circle

    name_x      = ox + SIDE_PAD * SCALE
    name_max_w  = logo_left - name_x - 10 * SCALE  # stop before circle

    box_x0      = ox + BOX_MARGIN * SCALE
    box_x1      = ox + ((CARD_W // SCALE) - BOX_MARGIN) * SCALE
    box_top     = oy + HEADER_H * SCALE
    box_bottom  = box_top + (STATS_PAD_V + n * ROW_H + STATS_PAD_V) * SCALE
    footer_top  = box_bottom

    px_pill_l   = ox + PILL_L  * SCALE
    px_value_r  = ox + VALUE_R * SCALE
    rows_top    = box_top + STATS_PAD_V * SCALE

    # ── Eyebrow tag ───────────────────────────────────────────────────────────
    ew_font  = load_font("rubik", "semibold", SZ_EYEBROW)
    ew_text  = f"{position} MATCHUP STATS"
    ewbb     = draw.textbbox((0, 0), ew_text, font=ew_font)
    ew_pad_x, ew_pad_y = 12 * SCALE, 6 * SCALE
    ew_w     = (ewbb[2] - ewbb[0]) + ew_pad_x * 2
    ew_h     = (ewbb[3] - ewbb[1]) + ew_pad_y * 2
    # Chip: right-align to logo circle right edge, top aligned to title top
    logo_right = ox + ((CARD_W // SCALE) - BOX_MARGIN) * SCALE  # = box_x1
    ew_x = logo_right - ew_w
    ew_y = oy + TITLE_TOP_PAD * SCALE
    # Chip border: team color at 50% opacity — matches softened badge treatment
    chip_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    chip_draw  = ImageDraw.Draw(chip_layer)
    chip_draw.rounded_rectangle(
        [ew_x, ew_y, ew_x + ew_w, ew_y + ew_h],
        radius=5 * SCALE, fill=(*hex_to_rgb(C_TAG_BG), 255),
        outline=(*hex_to_rgb(team_primary), 128), width=SCALE,
    )
    img  = Image.alpha_composite(img.convert("RGBA"), chip_layer).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text(
        (ew_x + ew_pad_x, ew_y + ew_pad_y - ewbb[1]),
        ew_text, font=ew_font, fill=WHITE,
    )

    # ── Team name — fixed TITLE_TOP_PAD anchor, fixed TITLE_LINE_HEIGHT ──────
    parts = team_name.upper().split()
    line1 = " ".join(parts[:-1]) if len(parts) >= 2 else parts[0]
    line2 = parts[-1]             if len(parts) >= 2 else ""

    check     = load_font("rubik", "black", SZ_NAME_MAX)
    longest   = max([line1] + ([line2] if line2 else []),
                    key=lambda t: draw.textbbox((0, 0), t, font=check)[2])
    name_font = _fit_name(draw, longest, name_max_w)

    # Fixed y anchors — title never drifts into subtitle regardless of font size
    title_y   = oy + TITLE_TOP_PAD * SCALE        # top of first title line
    l1bb      = draw.textbbox((0, 0), line1, font=name_font)
    draw.text((name_x, title_y - l1bb[1]), line1, font=name_font, fill=C_NAME)

    if line2:
        line2_y = title_y + TITLE_LINE_HEIGHT * SCALE
        l2bb    = draw.textbbox((0, 0), line2, font=name_font)
        draw.text((name_x, line2_y - l2bb[1]), line2, font=name_font, fill=C_NAME)
        last_title_bottom = line2_y + (l2bb[3] - l2bb[1])
    else:
        last_title_bottom = title_y + (l1bb[3] - l1bb[1])

    # Subtitle sits a fixed SUBTITLE_Y_OFFSET below last title line — never collides
    sub_y    = last_title_bottom + SUBTITLE_Y_OFFSET * SCALE
    sub_font = load_font("rubik", "medium", SZ_SUBTITLE)
    wk_part  = (" WEEKS 1\u2013" + str(nfl_week)) if (nfl_week and nfl_week > 1) else ""
    sub_text = "OPPOSING DEFENSE  \u2022  " + str(data_season) + " SEASON" + wk_part
    sub_bb   = draw.textbbox((0, 0), sub_text, font=sub_font)
    draw.text((name_x, sub_y - sub_bb[1]), sub_text, font=sub_font, fill=C_SUBTITLE)

    # Header separator — sits just above stat area, neutral color
    draw.rectangle(
        [ox, box_top - SCALE, ox + CARD_W, box_top],
        fill=C_HEADER_SEP,
    )

    # ── Logo circle (team color ONLY here) ────────────────────────────────────
    draw_logo_circle(
        img, draw, team_name,
        logo_cx, logo_cy, team_primary,
        outer_d=LOGO_OD, inner_d=LOGO_ID, logo_size=LOGO_SZ,
    )

    # ── Stats panel — clean_flat_v1: NO fill, dividers only ──────────────────
    assert STYLE_VERSION == "clean_flat_v1" and C_PANEL is None, \
        "Panel fill must be None in clean_flat_v1"
    # Nothing drawn here — rows sit directly on card background.

    # ── Stat rows ─────────────────────────────────────────────────────────────
    label_font = load_font("rubik", "semibold", SZ_LABEL)
    value_font = load_font("rubik", "black",   SZ_VALUE, italic=True)
    rank_font  = load_font("rubik", "bold",    SZ_RANK)

    # Pre-parse team primary RGB once for RGBA bar compositing
    tp_r, tp_g, tp_b = hex_to_rgb(team_primary)
    bar_h_px = int(ROW_H * SCALE * ROW_BAR_HEIGHT_RATIO)

    for i, stat in enumerate(rows):
        row_top  = rows_top + i * ROW_H * SCALE
        row_cy   = row_top + ROW_H * SCALE // 2
        rank     = stat["rank"]

        # ── Left accent bar — every row, identical specs, no exceptions ──────
        if ROW_LEFT_ACCENT_MODE == "all_rows":
            bar_top   = row_cy - bar_h_px // 2
            bar_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            bar_draw  = ImageDraw.Draw(bar_layer)
            bar_draw.rectangle(
                [box_x0,
                 bar_top,
                 box_x0 + ROW_BAR_W * SCALE,
                 bar_top + bar_h_px],
                fill=(tp_r, tp_g, tp_b, ROW_BAR_ALPHA),
            )
            img  = Image.alpha_composite(img.convert("RGBA"), bar_layer).convert("RGB")
            draw = ImageDraw.Draw(img)

        # Label — fixed offset from bar right edge
        label_x = box_x0 + (ROW_BAR_W + ROW_BAR_TO_LABEL_GAP) * SCALE
        lbbox   = draw.textbbox((0, 0), stat["label"], font=label_font)
        lh      = lbbox[3] - lbbox[1]
        draw.text(
            (label_x, row_cy - lh // 2 - lbbox[1]),
            stat["label"], font=label_font, fill=C_LABEL,
        )

        # Rank pill
        pill_y = row_cy - PILL_H * SCALE // 2
        draw_rank_pill(draw, ordinal(rank), px_pill_l, pill_y, rank, rank_font,
                       w=PILL_W, h=PILL_H)

        # Value — right-aligned
        val_text = stat.get("value_display", str(stat["value"]))
        vbbox    = draw.textbbox((0, 0), val_text, font=value_font)
        vw, vh   = vbbox[2] - vbbox[0], vbbox[3] - vbbox[1]
        draw.text(
            (px_value_r - vw, row_cy - vh // 2 - vbbox[1]),
            val_text, font=value_font, fill=C_VALUE,
        )

        # Row divider
        if i < n - 1:
            div_y = row_top + ROW_H * SCALE
            draw.line(
                [(box_x0 + 10 * SCALE, div_y), (box_x1 - 10 * SCALE, div_y)],
                fill=C_DIVIDER, width=max(1, SCALE // 2),
            )

    # ── Footer ────────────────────────────────────────────────────────────────
    draw.rounded_rectangle(
        [ox, footer_top, ox + CARD_W, oy + card_h],
        radius=BOX_RADIUS * SCALE, fill=C_CARD,
        corners=(False, False, True, True),
    )

    foot_font = load_font("rubik", "medium", SZ_FOOTER)
    foot_text = str(data_season) + " SEASON"
    if nfl_week and nfl_week > 1:
        foot_text += "  \u2022  WEEKS 1\u2013" + str(nfl_week)

    ftbb = draw.textbbox((0, 0), foot_text, font=foot_font)
    ft_h = ftbb[3] - ftbb[1]

    # Shared optical baseline: 18px up from card bottom
    FOOTER_BASELINE = oy + card_h - 18 * SCALE

    draw.text(
        (ox + SIDE_PAD * SCALE, FOOTER_BASELINE - ft_h - ftbb[1]),
        foot_text, font=foot_font, fill=C_FOOTER,
    )

    watermark = load_fantasylan_watermark(max_width=52)
    if watermark:
        wm_x = ox + CARD_W - watermark.width - SIDE_PAD * SCALE
        # Align watermark baseline to same optical baseline as season text
        wm_y = FOOTER_BASELINE - watermark.height
        img.paste(watermark, (wm_x, wm_y), watermark)

    # ── Debug overlay ─────────────────────────────────────────────────────────
    if debug:
        lbl = load_font("rubik", "regular", 7)
        for x_l, color, label in [
            (SIDE_PAD,  "#ff4444", "name-X"),
            (VALUE_R,   "#44ff44", "value-R"),
            (PILL_L,    "#4488ff", "pill-L"),
            (PILL_L + PILL_W, "#aaccff", "pill-R"),
        ]:
            x = ox + x_l * SCALE
            draw.line([(x, oy), (x, oy + card_h)], fill=color, width=SCALE)
            draw.text((x + 2, oy + 4), label, font=lbl, fill=color)
        for y_l, color, label in [
            (HEADER_H,  "#888888", "header-bottom"),
            (card_h_l - FOOTER_H, "#888888", "footer-top"),
        ]:
            y = oy + y_l * SCALE
            draw.line([(ox, y), (ox + CARD_W, y)], fill=color, width=SCALE)
            draw.text((ox + 4, y + 2), label, font=lbl, fill=color)

    # ── Save ──────────────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        safe   = team_name.lower().replace(" ", "_")
        suffix = "_debug" if debug else ""
        output_path = OUTPUT_DIR / f"{safe}_def_card_{date.today()}{suffix}.png"
    img.save(str(output_path), "PNG")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team",     default=None)
    parser.add_argument("--position", default="WR", choices=["QB", "RB", "WR", "TE"])
    parser.add_argument("--stats",    default="")
    parser.add_argument("--season",   type=int, default=2025)
    parser.add_argument("--output",   default=None)
    parser.add_argument("--debug",    action="store_true")
    parser.add_argument("--sample",   action="store_true",
                        help="Generate sample cards for 4 teams")
    args = parser.parse_args()

    from scrape_teamrankings import STATS as _STATS
    slugs_for = {
        pos: [s for s, m in _STATS.items() if pos in m["positions"]]
        for pos in ["QB", "RB", "WR", "TE"]
    }

    if args.sample:
        for team, pos in [
            ("Cincinnati Bengals", "WR"),
            ("Dallas Cowboys",     "WR"),
            ("Green Bay Packers",  "RB"),
            ("Miami Dolphins",     "WR"),
        ]:
            try:
                out = generate_def_card(team, pos, slugs_for[pos],
                                        season=args.season, debug=args.debug)
                print(f"OK  {team:30s}  {out.name}")
            except Exception as e:
                print(f"ERR {team:30s}  {e}")
        return

    if not args.team:
        parser.error("--team required unless --sample")

    slugs = ([s.strip() for s in args.stats.split(",")]
             if args.stats else slugs_for.get(args.position, []))
    out = generate_def_card(
        args.team, args.position, slugs, season=args.season,
        output_path=Path(args.output) if args.output else None,
        debug=args.debug,
    )
    print(f"Generated: {out}")


if __name__ == "__main__":
    main()
