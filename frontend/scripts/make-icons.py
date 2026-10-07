"""Build every PWA icon in public/ from one source image, brand/icon.png (needs Pillow).
Run from frontend/: python scripts/make-icons.py  -- see brand/README.md.
If brand/icon.png is missing, the placeholder (white pin on a blue rounded square) is drawn first."""
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRAND, OUT = ROOT / "brand", ROOT / "public"
SRC = BRAND / "icon.png"
THEME = json.loads((BRAND / "brand.json").read_text(encoding="utf-8"))["themeColor"]


def placeholder(size: int = 1024) -> Image.Image:
    s = size * 4  # supersample, then shrink for smooth edges
    bg, fg = (25, 118, 210), (255, 255, 255)  # MUI primary blue
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s // 5, fill=bg)
    c, r, cy = s / 2, s * 0.22, s * 0.43
    d.ellipse([c - r, cy - r, c + r, cy + r], fill=fg)
    d.polygon([(c - r * 0.86, cy + r * 0.5), (c + r * 0.86, cy + r * 0.5), (c, cy + r * 2.1)], fill=fg)
    h = r * 0.42
    d.ellipse([c - h, cy - h, c + h, cy + h], fill=bg)
    return img.resize((size, size), Image.LANCZOS)


if not SRC.exists():
    placeholder().save(SRC)
logo = Image.open(SRC).convert("RGBA")
if logo.width != logo.height:
    raise SystemExit(f"{SRC} must be square, got {logo.width}x{logo.height}")
if logo.width < 512:
    print(f"warning: {SRC} is {logo.width}px; 512+ (ideally 1024) looks sharper")

# Colour behind the logo where a platform needs full bleed: the logo's own
# corner colour if it's opaque (it brings its own background), else themeColor.
corner = logo.getpixel((0, 0))
bleed = corner if corner[3] == 255 else THEME


def sized(px: int) -> Image.Image:
    return logo.resize((px, px), Image.LANCZOS)


def on_bleed(px: int, scale: float) -> Image.Image:
    # Opaque square with the logo centred: maskable icons get cropped to a
    # circle (keep the logo in the inner 80%), and iOS turns transparency black.
    out = Image.new("RGBA", (px, px), bleed)
    inner = round(px * scale)
    out.alpha_composite(sized(inner), ((px - inner) // 2, (px - inner) // 2))
    return out.convert("RGB")


(OUT / "icons").mkdir(parents=True, exist_ok=True)
sized(192).save(OUT / "icons/icon-192.png")
sized(512).save(OUT / "icons/icon-512.png")
on_bleed(512, 0.8).save(OUT / "icons/icon-maskable-512.png")
on_bleed(180, 1.0).save(OUT / "icons/apple-touch-icon.png")
sized(256).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print(f"icons written to {OUT} from {SRC.relative_to(ROOT)}")
