"""Generate tabBar icon PNGs for Selfwell 微信小程序 (SF0 scaffold).

Outputs 8 PNGs (81x81 px RGBA) at:
  apps/mp-selfwell/miniprogram/assets/tabbar/{home,butler,plaza,profile}.png
                                              -active.png

Color palette (no forbidden colors):
  - Default: #718096 (ink-500)
  - Active : #A8C5B5 (mint)
"""

from PIL import Image, ImageDraw
from pathlib import Path

OUT_DIR = Path("apps/mp-selfwell/miniprogram/assets/tabbar")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SIZE = 81
DEFAULT = (113, 128, 150, 255)   # #718096
ACTIVE = (168, 197, 181, 255)    # #A8C5B5


def make_icon(path: Path, color: tuple[int, int, int, int], draw_fn) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_fn(d, color)
    img.save(path, "PNG")


def home(d: ImageDraw.ImageDraw, c: tuple[int, int, int, int]) -> None:
    # roof
    d.polygon([(40, 14), (12, 36), (68, 36)], outline=c, width=4)
    # body
    d.rectangle([(18, 36), (62, 70)], outline=c, width=4)
    # door
    d.rectangle([(34, 50), (46, 70)], outline=c, width=4)


def butler(d: ImageDraw.ImageDraw, c: tuple[int, int, int, int]) -> None:
    # chat bubble with 3 dots
    d.rounded_rectangle([(12, 18), (68, 56)], radius=10, outline=c, width=4)
    d.ellipse([(22, 30), (30, 38)], fill=c)
    d.ellipse([(34, 30), (42, 38)], fill=c)
    d.ellipse([(46, 30), (54, 38)], fill=c)
    # tail
    d.polygon([(28, 56), (40, 56), (32, 66)], outline=c, width=4)


def plaza(d: ImageDraw.ImageDraw, c: tuple[int, int, int, int]) -> None:
    # 4 small avatars in 2x2 grid
    for r in (0, 1):
        for col in (0, 1):
            cx = 22 + col * 36
            cy = 22 + r * 36
            d.ellipse([(cx - 14, cy - 14), (cx + 14, cy + 14)], outline=c, width=4)


def profile(d: ImageDraw.ImageDraw, c: tuple[int, int, int, int]) -> None:
    # head + shoulders
    d.ellipse([(28, 14), (54, 40)], outline=c, width=4)
    d.arc([(14, 36), (68, 80)], 180, 360, fill=c, width=4)


# Generate all 8 icons
icons = {
    "home.png": home,
    "butler.png": butler,
    "plaza.png": plaza,
    "profile.png": profile,
}

for name, fn in icons.items():
    make_icon(OUT_DIR / name, DEFAULT, fn)
    make_icon(OUT_DIR / name.replace(".png", "-active.png"), ACTIVE, fn)

print(f"Generated {len(icons) * 2} tabBar icons in {OUT_DIR}")