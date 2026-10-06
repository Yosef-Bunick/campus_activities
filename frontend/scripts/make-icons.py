"""Regenerate the placeholder PWA icons in public/icons (needs Pillow).
Run: python scripts/make-icons.py  -- replace once the app has a real name/logo."""
from pathlib import Path

from PIL import Image, ImageDraw

BG, FG = (25, 118, 210), (255, 255, 255)  # MUI primary blue
OUT = Path(__file__).resolve().parents[1] / "public"


def pin(size: int, scale: float, rounded: bool) -> Image.Image:
    s = size * 4  # supersample, then shrink for smooth edges
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s // 5, fill=BG)
    else:
        d.rectangle([0, 0, s, s], fill=BG)  # maskable / iOS: full bleed
    c, r = s / 2, s * 0.22 * scale
    cy = s * 0.43
    d.ellipse([c - r, cy - r, c + r, cy + r], fill=FG)
    d.polygon([(c - r * 0.86, cy + r * 0.5), (c + r * 0.86, cy + r * 0.5), (c, cy + r * 2.1)], fill=FG)
    h = r * 0.42
    d.ellipse([c - h, cy - h, c + h, cy + h], fill=BG)
    return img.resize((size, size), Image.LANCZOS)


pin(192, 1.0, True).save(OUT / "icons/icon-192.png")
pin(512, 1.0, True).save(OUT / "icons/icon-512.png")
pin(512, 0.8, False).save(OUT / "icons/icon-maskable-512.png")
pin(180, 1.0, False).convert("RGB").save(OUT / "icons/apple-touch-icon.png")
pin(64, 1.0, True).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
