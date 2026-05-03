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

# ── Palette — designer template v1 ────────────────────────────────────────────
BG_DARK       = "#0a0a0a"   # outer canvas (true near-black, no blue tint)
CARD_BG       = "#0e1e58"   # legacy — dark navy (only for blue-team cards / old generators)
CARD_BG_ALT   = "#0b1a42"   # legacy — keep for backward compat
CARD_BG_INNER = "#0b1a42"   # legacy — keep for backward compat
DIVIDER       = "#FFFFFF"   # white divider lines (0.5pt)
EYEBROW_BG    = "#092142"   # legacy — blue eyebrow (blue-team cards only)
LABEL_COLOR   = "#d4e3fd"   # legacy — blue-white label
SUBTITLE_COLOR= "#7895cc"   # legacy — blue subtitle
FOOTER_TEXT   = "#3a4ea7"   # legacy — blue footer
WHITE         = "#FFFFFF"
BLACK         = "#050c1c"

# ── Neutral (team-agnostic) surface tokens — no blue tint ─────────────────────
# Use these in any card where blue is NOT the team color.
NEUTRAL_BG_PAGE   = "#0a0a0a"   # outer canvas fill
NEUTRAL_BG_PANEL  = "#141414"   # stats-box / inner panel fill
NEUTRAL_BG_TAG    = "#1e1e1e"   # eyebrow pill / tag fill
NEUTRAL_TEXT_LBL  = "#c8c8c8"   # stat label text (neutral light gray)
NEUTRAL_TEXT_SUB  = "#737373"   # subtitle / meta text
NEUTRAL_TEXT_FTR  = "#505050"   # footer text

# Rank pill colors (text, background, outline)
# Softer than pure RGB — high contrast text but not eye-searing
RANK_GREEN        = "#3ecf5a"   # muted green — readable, not neon
RANK_GREEN_BG     = "#0f2014"
RANK_YELLOW       = "#d4ad35"   # warm amber — clearly mid
RANK_YELLOW_BG    = "#221c0a"
RANK_RED          = "#d94f4f"   # soft red — clearly bad but not alarming
RANK_RED_BG       = "#200d0d"

# Legacy aliases (keep for pickle card which uses score colors)
GRAY_LABEL    = LABEL_COLOR
GRAY_SUBTITLE = SUBTITLE_COLOR

# ── Font paths ─────────────────────────────────────────────────────────────────
RUBIK_DIR        = FONTS_DIR / "Rubik"
TOMMY_SOFT_DIR   = FONTS_DIR / "made_tommy_soft"
SOURCE_SERIF_DIR = FONTS_DIR / "Source_Serif_4" / "static" / "SourceSerif4_36pt"

# Rubik variable font — weight axis: 300=Light, 400=Regular, 500=Medium,
#   600=SemiBold, 700=Bold, 800=ExtraBold, 900=Black
_RUBIK_WEIGHTS = {
    "light":     300,
    "regular":   400,
    "medium":    500,
    "semibold":  600,
    "bold":      700,
    "extrabold": 800,
    "black":     900,
}

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


def load_font(family: str, weight: str, size: int, italic: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font at size × SCALE, cached."""
    scaled_size = size * SCALE
    cache_key = f"{family}-{weight}-{scaled_size}-{'i' if italic else 'n'}"
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    if family == "rubik":
        ttf_file = "Rubik-Italic[wght].ttf" if italic else "Rubik[wght].ttf"
        path = RUBIK_DIR / ttf_file
        wght = _RUBIK_WEIGHTS.get(weight, 400)
        font = ImageFont.truetype(str(path), scaled_size)
        try:
            font.set_variation_by_axes([wght])
        except Exception:
            pass
    elif family == "tommy":
        fname = _TOMMY_WEIGHTS.get(weight, _TOMMY_WEIGHTS["regular"])
        path = TOMMY_SOFT_DIR / fname
        if not path.exists():
            candidates = list(TOMMY_SOFT_DIR.glob("*.otf"))
            path = candidates[0] if candidates else None
        font = ImageFont.truetype(str(path), scaled_size) if path else ImageFont.load_default()
    elif family == "serif":
        fname = _SERIF_WEIGHTS.get(weight, _SERIF_WEIGHTS["regular"])
        path = SOURCE_SERIF_DIR / fname
        if not path.exists():
            candidates = list(SOURCE_SERIF_DIR.glob("*.ttf"))
            path = candidates[0] if candidates else None
        font = ImageFont.truetype(str(path), scaled_size) if path else ImageFont.load_default()
    else:
        raise ValueError(f"Unknown font family: {family}")

    _font_cache[cache_key] = font
    return font


def draw_radial_glow(
    img: Image.Image,
    cx: int,
    cy: int,
    radius: int,
    color_hex: str,
    max_alpha: int = 28,
) -> Image.Image:
    """
    Composite a soft radial glow onto img at (cx, cy).
    Drawn as concentric filled ellipses fading to transparent.
    max_alpha: 0–255; keep ≤35 for a 5–10% tint.
    Returns the composited image (RGB).
    """
    r, g, b = hex_to_rgb(color_hex)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    step = 4
    for rad in range(radius, 0, -step):
        alpha = int(max_alpha * (1 - rad / radius) ** 0.5)
        gd.ellipse(
            [cx - rad, cy - rad, cx + rad, cy + rad],
            fill=(r, g, b, alpha),
        )
    return Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rank_color(rank: int, total: int = 32) -> str:
    """
    Rank 1 = most allowed = best matchup = GREEN.
    Tighter tiers so green/yellow/red feel semantically distinct:
      Green  = top 8  (clear favorable matchup)
      Yellow = 9–20   (mid / neutral)
      Red    = 21–32  (clear unfavorable matchup)
    """
    if rank <= 8:
        return RANK_GREEN
    elif rank <= 20:
        return RANK_YELLOW
    else:
        return RANK_RED


def team_dark_bg(primary_hex: str) -> str:
    """
    Returns a card background color derived from the team's primary.
    Targets ~20% perceived brightness so white text is always readable,
    while keeping the hue clearly recognisable.
    Already-dark colors (e.g. GB #203731) are used closer to their original value.
    """
    h = primary_hex.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    # Perceived brightness (0–255)
    brightness = 0.299 * r + 0.587 * g + 0.114 * b

    if brightness < 40:
        # Very dark already (Raiders black, GB dark green) — lighten slightly so color shows
        factor = 1.8
    elif brightness < 80:
        # Dark (navy, dark red, dark purple) — small boost
        factor = 1.3
    elif brightness < 140:
        # Mid (medium blues, teals) — bring down to ~40%
        factor = 0.45
    else:
        # Bright (orange, red, cyan) — bring down significantly
        factor = 0.28

    r = min(255, max(12, int(r * factor)))
    g = min(255, max(12, int(g * factor)))
    b = min(255, max(12, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def rank_bg_color(rank: int) -> str:
    """Background fill for rank pill — matches rank_color thresholds."""
    if rank <= 8:
        return RANK_GREEN_BG
    elif rank <= 20:
        return RANK_YELLOW_BG
    else:
        return RANK_RED_BG


def team_panel_bg(primary_hex: str) -> str:
    """
    Very dark panel background derived from team primary — no hardcoded blue.
    Pushes the primary to ~6% brightness so it's near-black but team-hued.
    Result is always suitable for white text.
    """
    r, g, b = hex_to_rgb(primary_hex)
    r = min(255, max(8, int(r * 0.06)))
    g = min(255, max(8, int(g * 0.06)))
    b = min(255, max(8, int(b * 0.06)))
    return f"#{r:02x}{g:02x}{b:02x}"


def team_tag_bg(primary_hex: str) -> str:
    """
    Dark pill/tag background derived from team primary — no hardcoded blue.
    Slightly lighter than panel (~12%) so it reads as a distinct surface.
    """
    r, g, b = hex_to_rgb(primary_hex)
    r = min(255, max(10, int(r * 0.12)))
    g = min(255, max(10, int(g * 0.12)))
    b = min(255, max(10, int(b * 0.12)))
    return f"#{r:02x}{g:02x}{b:02x}"


def build_token_map(team_name: str, team_map: dict | None = None) -> dict:
    """
    Build a named-role token map for a given team.
    Roles: bg_page, bg_card, bg_panel, bg_tag, text_primary, text_secondary,
           text_sub, text_footer, divider, team_primary, team_secondary.

    Prints resolved colors and warns on fallback.
    Returns the full token dict.
    """
    if team_map is None:
        team_map = load_team_map()

    info = team_map.get(team_name)
    fallback_used: list[str] = []

    if not info:
        print(f"[TOKEN WARNING] Team '{team_name}' not found in team_map.json — using fallback colors")
        fallback_used.append("team_primary")
        fallback_used.append("team_secondary")
        team_primary   = "#555555"
        team_secondary = "#333333"
    else:
        team_primary   = info.get("primary")
        team_secondary = info.get("secondary")
        if not team_primary:
            print(f"[TOKEN WARNING] '{team_name}' missing 'primary' in team_map — using fallback #555555")
            fallback_used.append("team_primary")
            team_primary = "#555555"
        if not team_secondary:
            print(f"[TOKEN WARNING] '{team_name}' missing 'secondary' in team_map — using fallback #333333")
            fallback_used.append("team_secondary")
            team_secondary = "#333333"

    tokens = {
        "bg_page":       NEUTRAL_BG_PAGE,          # outer canvas — always neutral
        "bg_card":       team_dark_bg(team_primary),# card body — team-tinted dark
        "bg_panel":      team_panel_bg(team_primary),# stats box — very dark team hue
        "bg_tag":        team_tag_bg(team_primary), # eyebrow tag — slightly lighter dark
        "text_primary":  WHITE,                     # names, values
        "text_label":    NEUTRAL_TEXT_LBL,          # stat label text
        "text_sub":      NEUTRAL_TEXT_SUB,          # subtitle / meta
        "text_footer":   NEUTRAL_TEXT_FTR,          # footer text
        "divider":       WHITE,                     # row dividers
        "team_primary":  team_primary,
        "team_secondary": team_secondary,
        "rank_good":     RANK_GREEN,
        "rank_mid":      RANK_YELLOW,
        "rank_bad":      RANK_RED,
    }

    print(f"[TOKENS] {team_name}")
    print(f"  team_primary   = {tokens['team_primary']}")
    print(f"  team_secondary = {tokens['team_secondary']}")
    print(f"  bg_card        = {tokens['bg_card']}")
    print(f"  bg_panel       = {tokens['bg_panel']}")
    print(f"  bg_tag         = {tokens['bg_tag']}")
    if fallback_used:
        print(f"  [!] FALLBACK used for: {', '.join(fallback_used)}")
    else:
        print(f"  [OK] All team colors resolved from team_map.json")

    return tokens


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
    # Use the beige transparent logo — readable on dark backgrounds
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


def make_card_canvas(card_h: int, card_bg: str = CARD_BG) -> tuple[Image.Image, ImageDraw.ImageDraw, tuple[int, int]]:
    """
    Create the base image with a dynamic card height.
    card_h: actual pixel height of the card (already scaled).
    card_bg: card background fill color (default dark navy; pass team_dark_bg() for team-colored cards).
    """
    img_w = CARD_W + OUTER_PAD * 2
    img_h = card_h + OUTER_PAD * 2

    img = Image.new("RGB", (img_w, img_h), BG_DARK)
    draw = ImageDraw.Draw(img)

    CARD_RADIUS = 18 * SCALE
    card_rect = [OUTER_PAD, OUTER_PAD, OUTER_PAD + CARD_W, OUTER_PAD + card_h]
    draw.rounded_rectangle(card_rect, radius=CARD_RADIUS, fill=card_bg)

    return img, draw, (OUTER_PAD, OUTER_PAD)


def draw_rank_pill(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    rank: int,
    font: ImageFont.FreeTypeFont,
    w: int = 70,
    h: int = 22,
) -> None:
    """Draw a rank pill: dark fill + colored border + colored text. 70x22px per spec."""
    sw, sh = w * SCALE, h * SCALE
    fg = rank_color(rank)
    bg = rank_bg_color(rank)
    radius = sh // 2
    rect = [x, y, x + sw, y + sh]
    draw.rounded_rectangle(rect, radius=radius, fill=bg, outline=fg, width=2 * SCALE)
    bbox = draw.textbbox((0, 0), text, font=font)
    tx = x + (sw - (bbox[2] - bbox[0])) // 2
    ty = y + (sh - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=fg)


def draw_pill_badge(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    color: str,
    font: ImageFont.FreeTypeFont,
    padding: tuple[int, int] = (14, 6),
) -> int:
    """Generic solid-fill pill badge (used by pickle card verdict)."""
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
    """White 0.5pt divider per designer spec."""
    pad = 14 * SCALE
    draw.line(
        [(card_x + pad, y), (card_x + width - pad, y)],
        fill=WHITE,
        width=max(1, SCALE // 2),
    )


def draw_logo_circle(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    team_name: str,
    cx: int,
    cy: int,
    team_color: str,
    outer_d: int = 131,
    inner_d: int = 115,
    logo_size: int = 82,
) -> None:
    """
    Solid refined badge — visible presence, not ghosted:
      - Outer glow: team color, very low opacity, fades out (halo feel)
      - Ring: team color at 55% opacity — visible but not harsh white
      - Fill: actual team color darkened 35% — solid, readable
      - Vignette: subtle dark at fill edge for depth
      - Logo crisp on top
    """
    r, g, b = hex_to_rgb(team_color)
    badge_d = outer_d * SCALE
    bc      = badge_d // 2

    badge = Image.new("RGBA", (badge_d, badge_d), (0, 0, 0, 0))
    bd    = ImageDraw.Draw(badge)

    # ── Outer glow: 8px soft halo of team color ───────────────────────────────
    halo_steps = 10
    for s in range(halo_steps, 0, -1):
        t     = s / halo_steps
        alpha = int(30 * (t ** 1.5))
        rad   = bc + int(8 * SCALE * t)
        bd.ellipse(
            [bc - rad, bc - rad, bc + rad, bc + rad],
            fill=(r, g, b, alpha),
        )

    # ── Ring: team color at 55% opacity, 4px thick ───────────────────────────
    ring_inset = 2 * SCALE
    bd.ellipse(
        [ring_inset, ring_inset, badge_d - ring_inset, badge_d - ring_inset],
        outline=(r, g, b, 140),   # 140/255 ≈ 55%
        width=4 * SCALE,
    )

    # ── Fill: team color darkened 35%, fully opaque ───────────────────────────
    fill_r = max(8, int(r * 0.65))
    fill_g = max(8, int(g * 0.65))
    fill_b = max(8, int(b * 0.65))
    fill_inset = ring_inset + 4 * SCALE
    bd.ellipse(
        [fill_inset, fill_inset, badge_d - fill_inset, badge_d - fill_inset],
        fill=(fill_r, fill_g, fill_b, 255),
    )

    # ── Vignette: dark edge inside fill for depth ─────────────────────────────
    fill_rad = bc - fill_inset
    for s in range(8, 0, -1):
        t     = s / 8
        alpha = int(50 * (t ** 2))
        inset_v = fill_inset + int(fill_rad * (1 - t))
        bd.ellipse(
            [inset_v, inset_v, badge_d - inset_v, badge_d - inset_v],
            fill=(0, 0, 0, alpha),
        )

    # Composite badge onto main image
    bx = cx - badge_d // 2
    by = cy - badge_d // 2
    img.paste(badge, (bx, by), badge)

    # Logo — crisp on top
    logo = load_team_logo(team_name, size=(logo_size, logo_size))
    if logo:
        lx = cx - logo.width // 2
        ly = cy - logo.height // 2
        img.paste(logo, (lx, ly), logo)


def ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
