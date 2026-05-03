"""
Generates a branded Pickle Score card PNG.

Shows: score, verdict, matchup, and 3 plain-English reason bullets.
Does NOT expose component weights, sub-scores, or data sources.

Usage (from Streamlit):
    from tools.generate_pickle_card import generate_pickle_card
    path = generate_pickle_card(
        def_team_name="Dallas Cowboys",
        off_team_name="Los Angeles Rams",
        position="QB",
        score=8.2,
        verdict="Must Start",
        reasons=[
            "Cowboys has been one of the most generous defenses vs QBs this season",
            "Weak across key QB metrics — yards, TDs, and conversion rate",
            "Rams have a high projected score this week — game script favours volume",
        ],
        season=2025,
    )
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
    CARD_BG, CARD_BG_ALT, DIVIDER, GRAY_LABEL, GRAY_SUBTITLE, BLACK, WHITE,
    load_font, load_team_map, load_team_logo, load_fantasylan_watermark,
    make_card_canvas, draw_pill_badge, draw_divider,
)

OUTPUT_DIR = ROOT / "output"

# Score tier colors (matches app.py)
def _score_color(score: float) -> str:
    if score >= 9.0:
        return "#00C853"   # GOAT MATCHUP — bright green
    elif score >= 7.8:
        return "#43A047"   # GREAT MATCHUP — medium green
    elif score >= 6.2:
        return "#29B6F6"   # SOLID MATCHUP — blue
    elif score >= 4.8:
        return "#FFD600"   # NEUTRAL MATCHUP — amber
    elif score >= 3.5:
        return "#FF6D00"   # TOUGH MATCHUP — orange
    else:
        return "#FF1744"   # BRUTAL MATCHUP — red


def generate_pickle_card(
    def_team_name: str,
    off_team_name: str,
    position: str,
    score: float,
    verdict: str,
    reasons: list[str],
    season: int = 2025,
    nfl_week: int | None = None,
    output_path: Path | None = None,
) -> Path:
    """
    Generate a Pickle Score card PNG.

    Args:
        def_team_name:  Defensive team (the opponent), e.g. "Dallas Cowboys"
        off_team_name:  Offensive team (player's team), e.g. "Los Angeles Rams"
        position:       "QB", "RB", "WR", or "TE"
        score:          Pickle Score (1.0–10.0)
        verdict:        Short verdict string, e.g. "Must Start"
        reasons:        List of 1–3 plain-English reason strings
        season:         NFL season year
        nfl_week:       Current NFL week (None = full season label)
        output_path:    Where to save the PNG (auto-named if None)
    """
    team_map    = load_team_map()
    def_info    = team_map.get(def_team_name, {})
    def_color   = def_info.get("primary", "#333333")
    score_color = _score_color(score)

    # ── Fonts ──────────────────────────────────────────────────────────────────
    score_font    = load_font("tommy", "extrabold", 72)
    verdict_font  = load_font("tommy", "extrabold", 20)
    label_font    = load_font("tommy", "bold", 11)
    matchup_font  = load_font("tommy", "bold", 15)
    reason_font   = load_font("serif", "regular", 13)
    footer_font   = load_font("serif", "regular", 11)
    tag_font      = load_font("tommy", "bold", 10)

    # ── Measure reason text heights ────────────────────────────────────────────
    # Wrap reasons to fit card width
    max_text_w = CARD_W - (56 * SCALE)   # left pad + right pad
    bullet_indent = 24 * SCALE

    def wrap_text(text: str, font, max_w: int) -> list[str]:
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = _dummy_draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    # Need a temporary draw to measure text — create a small scratch image
    from PIL import Image as _PILImage, ImageDraw as _PILDraw
    _scratch = _PILImage.new("RGB", (1, 1))
    _dummy_draw = _PILDraw.Draw(_scratch)

    reason_line_h = int(reason_font.size * 1.45)
    reason_blocks: list[list[str]] = []
    total_reason_h = 0
    for r in reasons[:3]:
        wrapped = wrap_text(r, reason_font, max_text_w - bullet_indent)
        reason_blocks.append(wrapped)
        total_reason_h += len(wrapped) * reason_line_h + (8 * SCALE)  # 8px gap after each
    total_reason_h += 12 * SCALE   # extra bottom padding

    # ── Card height ────────────────────────────────────────────────────────────
    ACCENT_BAR_H  = 8 * SCALE
    HEADER_H      = 112 * SCALE   # "Pickle Score" label + top padding
    SCORE_H       = 100 * SCALE   # big score number
    VERDICT_H     = 52 * SCALE    # verdict badge + gap
    MATCHUP_H     = 48 * SCALE    # matchup line
    RULE_H        = 28 * SCALE    # divider + spacing
    REASONS_H     = total_reason_h
    FOOTER_H      = 64 * SCALE

    card_h = ACCENT_BAR_H + HEADER_H + SCORE_H + VERDICT_H + MATCHUP_H + RULE_H + REASONS_H + FOOTER_H

    img, draw, (cx, cy) = make_card_canvas(card_h)

    # ── Team color accent bar ──────────────────────────────────────────────────
    CARD_RADIUS = 24 * SCALE
    draw.rounded_rectangle(
        [cx, cy, cx + CARD_W, cy + CARD_RADIUS + ACCENT_BAR_H],
        radius=CARD_RADIUS,
        fill=def_color,
        corners=(True, True, False, False),
    )
    draw.rectangle(
        [cx, cy + ACCENT_BAR_H, cx + CARD_W, cy + CARD_RADIUS + ACCENT_BAR_H],
        fill=CARD_BG,
    )

    # ── Defense logo (top right) ───────────────────────────────────────────────
    logo = load_team_logo(def_team_name, size=(72, 72))
    if logo:
        logo_x = cx + CARD_W - (20 * SCALE) - logo.width
        logo_y = cy + (20 * SCALE)
        img.paste(logo, (logo_x, logo_y), logo)

    # ── "PICKLE SCORE" label ───────────────────────────────────────────────────
    hx = cx + (28 * SCALE)
    hy = cy + (24 * SCALE)

    draw.text((hx, hy), "PICKLE SCORE", font=label_font, fill=GRAY_LABEL)

    # ── Position + matchup tag ─────────────────────────────────────────────────
    pos_tag = f"{position}  ·  {off_team_name.split()[-1].upper()} vs {def_team_name.split()[-1].upper()} DEF"
    draw.text((hx, hy + (18 * SCALE)), pos_tag, font=tag_font, fill=GRAY_SUBTITLE)

    # ── Big score ─────────────────────────────────────────────────────────────
    score_y = cy + ACCENT_BAR_H + HEADER_H - (16 * SCALE)
    score_str = str(score)
    draw.text((hx, score_y), score_str, font=score_font, fill=score_color)

    # ── Verdict badge ──────────────────────────────────────────────────────────
    verdict_y = score_y + SCORE_H
    draw_pill_badge(
        draw, verdict.upper(), hx, verdict_y,
        score_color, verdict_font,
        padding=(16, 7),
    )

    # ── Matchup line ───────────────────────────────────────────────────────────
    matchup_y = verdict_y + VERDICT_H
    matchup_text = f"{off_team_name}  vs  {def_team_name} Defense"
    draw.text((hx, matchup_y), matchup_text, font=matchup_font, fill=GRAY_LABEL)

    # ── Divider ────────────────────────────────────────────────────────────────
    rule_y = matchup_y + MATCHUP_H
    draw_divider(draw, cx, rule_y)

    # ── Reason bullets ────────────────────────────────────────────────────────
    bullet_x = hx
    text_x   = hx + bullet_indent
    current_y = rule_y + (16 * SCALE)

    for block in reason_blocks:
        # Draw bullet dot
        dot_y = current_y + reason_line_h // 2 - (3 * SCALE)
        draw.ellipse(
            [bullet_x, dot_y, bullet_x + (6 * SCALE), dot_y + (6 * SCALE)],
            fill=score_color,
        )
        for line in block:
            draw.text((text_x, current_y), line, font=reason_font, fill=GRAY_LABEL)
            current_y += reason_line_h
        current_y += 8 * SCALE

    # ── Footer ─────────────────────────────────────────────────────────────────
    footer_y = cy + card_h - FOOTER_H
    draw_divider(draw, cx, footer_y)

    if nfl_week and nfl_week == 1:
        footer_text = f"{season} Season Week 1"
    elif nfl_week and nfl_week > 1:
        footer_text = f"{season} Season Week 1-{nfl_week}"
    else:
        footer_text = f"{season} Season"
    draw.text(
        (hx, footer_y + (14 * SCALE)),
        footer_text,
        font=footer_font,
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
        safe_def = def_team_name.lower().replace(" ", "_")
        safe_off = off_team_name.lower().replace(" ", "_")
        output_path = OUTPUT_DIR / f"{safe_off}_vs_{safe_def}_{position}_pickle_{date.today()}.png"

    img.save(str(output_path), "PNG")
    return output_path
