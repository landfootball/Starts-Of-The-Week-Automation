"""
Shared Pillow utilities for all card generators.
Handles font loading, color helpers, logo loading, and the base card canvas.
"""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
LOGOS_DIR = ROOT / "NFL Team Logos"
BRANDING_DIR = ROOT / "branding assets"
FONTS_DIR = BRANDING_DIR / "fonts"
TEAM_MAP_PATH = ROOT / "config" / "team_map.json"

# ── Resolution scale (2 = crisp on modern screens) ────────────────────────────
SCALE = 2

# ── Card dimensions (logical units × SCALE = actual pixels) ───────────────────
CARD_W = 500 * SCALE        # 1000px
OUTER_PAD = 32 * SCALE      # 64px
# CARD_H is dynamic — calculated per card based on content

# ── Palette ────────────────────────────────────────────────────────────────────
BG_DARK = "#1A1A1A"
CARD_BG = "#F5F0E8"
CARD_BG_ALT = "#EDE8DC"
DIVIDER = "#D8D0C0"
GRAY_LABEL = "#4A4A4A"
GRAY_SUBTITLE = "#666666"
BLACK = "#111111"
WHITE = "#FFFFFF"

RANK_GREEN = "#2E7D32"    # rank 1–10  (most allowed = great matchup)
RANK_YELLOW = "#F57C00"   # rank 11–22 (mid)
RANK_RED = "#C62828"      # rank 23–32 (fewest allowed = tough matchup)

# ── Font paths ─────────────────────────────────────────────────────────────────
TOMMY_SOFT_DIR = FONTS_DIR / "made_tommy_soft"
SOURCE_SERIF_DIR = FONTS_DIR / "Source_Serif_4" / "static" / "SourceSerif4_36pt"

_TOMMY_WEIGHTS = {
    "light": "MADE Tommy Soft Light PERSONAL USE.otf",
    "regular": "MADE Tommy Soft Regular PERSONAL USE.otf",
    "medium": "MADE Tommy Soft Medium PERSONAL USE.otf",
    "bold": "MADE Tommy Soft Bold PERSONAL USE.otf",
    "extrabold": "MADE Tommy Soft ExtraBold PERSONAL USE.otf",
    "black": "MADE Tommy Soft Black PERSONAL USE.otf",
}

_SERIF_WEIGHTS = {
    "light": "SourceSerif4_36pt-Light.ttf",
    "regular": "SourceSerif4_36pt-Regular.ttf",
    "medium": "SourceSerif4_36pt-Medium.ttf",
    "semibold": "SourceSerif4_36pt-SemiBold.ttf",
    "bold": "SourceSerif4_36pt-Bold.ttf",
    "extrabold": "SourceSerif4_36pt-ExtraBold.ttf",
}

_font_cache: dict[str, ImageFont.FreeTypeFont] = {}


def load_font(family: str, weight: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font at size × SCALE, cached."""
    scaled_size = size * SCALE
    cache_key = f"{family}-{weight}-{scaled_size}"
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    if family == "tommy":
        fname = _TOMMY_WEIGHTS.get(weight, _TOMMY_WEIGHTS["regular"])
        path = TOMMY_SOFT_DIR / fname
    elif family == "serif":
        fname = _SERIF_WEIGHTS.get(weight, _SERIF_WEIGHTS["regular"])
        path = SOURCE_SERIF_DIR / fname
    else:
        raise ValueError(f"Unknown font family: {family}")

    if not path.exists():
        candidates = list(TOMMY_SOFT_DIR.glob("*.otf")) + list(SOURCE_SERIF_DIR.glob("*.ttf"))
        path = candidates[0] if candidates else None

    font = ImageFont.truetype(str(path), scaled_size) if path else ImageFont.load_default()
    _font_cache[cache_key] = font
    return font


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rank_color(rank: int, total: int = 32) -> str:
    """Rank 1 = most allowed = best matchup = GREEN."""
    if rank <= 10:
        return RANK_GREEN
    elif rank <= 22:
        return RANK_YELLOW
    else:
        return RANK_RED


def load_team_map() -> dict:
    with open(TEAM_MAP_PATH) as f:
        return json.load(f)


def load_team_logo(team_name: str, size: tuple[int, int] = (80, 80)) -> Image.Image | None:
    scaled_size = (size[0] * SCALE, size[1] * SCALE)
    team_map = load_team_map()
    info = team_map.get(team_name)
    if not info:
        return None
    logo_path = LOGOS_DIR / info["logo"]
    if not logo_path.exists():
        return None
    try:
        img = Image.open(logo_path).convert("RGBA")
        img.thumbnail(scaled_size, Image.LANCZOS)
        return img
    except Exception:
        return None


def load_fantasylan_watermark(max_width: int = 160) -> Image.Image | None:
    watermark_path = BRANDING_DIR / "logos" / "FantasyLand Branding_Second Beige Transparent Logo.png"
    if not watermark_path.exists():
        return None
    try:
        img = Image.open(watermark_path).convert("RGBA")
        scaled_max = max_width * SCALE
        ratio = scaled_max / img.width
        new_h = int(img.height * ratio)
        img = img.resize((scaled_max, new_h), Image.LANCZOS)
        return img
    except Exception:
        return None


def make_card_canvas(card_h: int) -> tuple[Image.Image, ImageDraw.ImageDraw, tuple[int, int]]:
    """
    Create the base image with a dynamic card height.
    card_h: actual pixel height of the card (already scaled).
    """
    img_w = CARD_W + OUTER_PAD * 2
    img_h = card_h + OUTER_PAD * 2

    img = Image.new("RGB", (img_w, img_h), BG_DARK)
    draw = ImageDraw.Draw(img)

    shadow_offset = 8
    shadow_rect = [
        OUTER_PAD + shadow_offset,
        OUTER_PAD + shadow_offset,
        OUTER_PAD + CARD_W + shadow_offset,
        OUTER_PAD + card_h + shadow_offset,
    ]
    draw.rounded_rectangle(shadow_rect, radius=24, fill="#0A0A0A")

    card_rect = [OUTER_PAD, OUTER_PAD, OUTER_PAD + CARD_W, OUTER_PAD + card_h]
    draw.rounded_rectangle(card_rect, radius=24, fill=CARD_BG)

    return img, draw, (OUTER_PAD, OUTER_PAD)


def draw_pill_badge(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    color: str,
    font: ImageFont.FreeTypeFont,
    padding: tuple[int, int] = (14, 6),
) -> int:
    scaled_pad = (padding[0] * SCALE, padding[1] * SCALE)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pill_w = text_w + scaled_pad[0] * 2
    pill_h = text_h + scaled_pad[1] * 2

    rect = [x, y, x + pill_w, y + pill_h]
    draw.rounded_rectangle(rect, radius=pill_h // 2, fill=color)
    draw.text(
        (x + scaled_pad[0], y + scaled_pad[1] - bbox[1]),
        text,
        font=font,
        fill=WHITE,
    )
    return x + pill_w


def draw_divider(draw: ImageDraw.ImageDraw, card_x: int, y: int, width: int = CARD_W) -> None:
    pad = 24 * SCALE
    draw.line(
        [(card_x + pad, y), (card_x + width - pad, y)],
        fill=DIVIDER,
        width=SCALE,
    )


def ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
