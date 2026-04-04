"""
Shared Pillow utilities for all card generators.
Handles font loading, color helpers, logo loading, and the base card canvas.
"""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
LOGOS_DIR = ROOT / "NFL Team Logos"
BRANDING_DIR = ROOT / "branding assets"
FONTS_DIR = BRANDING_DIR / "fonts"
TEAM_MAP_PATH = ROOT / "config" / "team_map.json"

# ── Card dimensions ────────────────────────────────────────────────────────────
CARD_W = 650
CARD_H = 900
OUTER_PAD = 32          # space between card and image edge
IMG_W = CARD_W + OUTER_PAD * 2
IMG_H = CARD_H + OUTER_PAD * 2

# ── Palette ────────────────────────────────────────────────────────────────────
BG_DARK = "#1A1A1A"
CARD_BG = "#F5F0E8"
CARD_BG_ALT = "#EDE8DC"   # alternating row tint
DIVIDER = "#D8D0C0"
GRAY_LABEL = "#888888"
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
    """Load a font, caching by (family, weight, size)."""
    cache_key = f"{family}-{weight}-{size}"
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
        # Fallback: walk the font dir for any .ttf/.otf
        candidates = list(TOMMY_SOFT_DIR.glob("*.otf")) + list(SOURCE_SERIF_DIR.glob("*.ttf"))
        path = candidates[0] if candidates else None

    font = ImageFont.truetype(str(path), size) if path else ImageFont.load_default()
    _font_cache[cache_key] = font
    return font


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rank_color(rank: int, total: int = 32) -> str:
    """
    Return badge color based on rank.
    Rank 1 = most allowed = best matchup for fantasy starters = GREEN.
    """
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
    """Load and resize a team logo. Returns None if not found."""
    team_map = load_team_map()
    info = team_map.get(team_name)
    if not info:
        return None
    logo_path = LOGOS_DIR / info["logo"]
    if not logo_path.exists():
        return None
    try:
        img = Image.open(logo_path).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
        return img
    except Exception:
        return None


def load_fantasylan_watermark(max_width: int = 160) -> Image.Image | None:
    """Load the FantasyLand beige transparent watermark logo."""
    watermark_path = BRANDING_DIR / "logos" / "FantasyLand Branding_Second Beige Transparent Logo.png"
    if not watermark_path.exists():
        return None
    try:
        img = Image.open(watermark_path).convert("RGBA")
        # Scale proportionally
        ratio = max_width / img.width
        new_h = int(img.height * ratio)
        img = img.resize((max_width, new_h), Image.LANCZOS)
        return img
    except Exception:
        return None


def make_card_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw, tuple[int, int]]:
    """
    Create the base image: dark outer background with a cream card centered.

    Returns:
        (image, draw, card_origin) where card_origin is (x, y) of the card's top-left.
    """
    img = Image.new("RGB", (IMG_W, IMG_H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Draw card with slight shadow
    shadow_offset = 6
    shadow_rect = [
        OUTER_PAD + shadow_offset,
        OUTER_PAD + shadow_offset,
        OUTER_PAD + CARD_W + shadow_offset,
        OUTER_PAD + CARD_H + shadow_offset,
    ]
    draw.rounded_rectangle(shadow_rect, radius=16, fill="#0A0A0A")

    # Card background
    card_rect = [OUTER_PAD, OUTER_PAD, OUTER_PAD + CARD_W, OUTER_PAD + CARD_H]
    draw.rounded_rectangle(card_rect, radius=16, fill=CARD_BG)

    card_origin = (OUTER_PAD, OUTER_PAD)
    return img, draw, card_origin


def draw_pill_badge(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    color: str,
    font: ImageFont.FreeTypeFont,
    padding: tuple[int, int] = (14, 6),
) -> int:
    """
    Draw a pill-shaped badge with text. Returns the right edge x coordinate.
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pill_w = text_w + padding[0] * 2
    pill_h = text_h + padding[1] * 2

    rect = [x, y, x + pill_w, y + pill_h]
    draw.rounded_rectangle(rect, radius=pill_h // 2, fill=color)
    draw.text(
        (x + padding[0], y + padding[1] - bbox[1]),
        text,
        font=font,
        fill=WHITE,
    )
    return x + pill_w


def draw_divider(draw: ImageDraw.ImageDraw, card_x: int, y: int, width: int = CARD_W) -> None:
    """Draw a horizontal divider line inside the card."""
    draw.line(
        [(card_x + 24, y), (card_x + width - 24, y)],
        fill=DIVIDER,
        width=1,
    )


def ordinal(n: int) -> str:
    """Convert integer to ordinal string: 1 → '1st', 2 → '2nd', etc."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
