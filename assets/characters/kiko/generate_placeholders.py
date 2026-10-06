#!/usr/bin/env python3
"""Generate KIKO's deliberately simple, replaceable 2.5D placeholder layers."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
LAYERS = ROOT / "layers"
LAYERS.mkdir(parents=True, exist_ok=True)

C = {
    "teal": "#6F8C88", "cream": "#ECE1CE", "rust": "#C76B38", "crest": "#B8A066",
    "nose": "#E3A0A0", "iris": "#A5571F", "ear": "#C98E73", "pad": "#7E99A0",
    "freckle": "#8A4A2A", "cloth": "#6E5035", "leather": "#49301F", "brass": "#B58A3B",
    "ink": "#27312F", "white": "#FFF9ED",
}
FONT = ImageFont.load_default()


def layer(name: str, size: tuple[int, int], painter) -> None:
    im = Image.new("RGBA", size, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    painter(d, size)
    label = "PLACEHOLDER " + name
    box = d.textbbox((0, 0), label, font=FONT)
    tw, th = box[2] - box[0], box[3] - box[1]
    x, y = max(2, (size[0] - tw) // 2), max(2, size[1] - th - 3)
    d.rounded_rectangle((x - 2, y - 1, x + tw + 2, y + th + 1), 3, fill=(255, 255, 255, 185))
    d.text((x, y), label, fill=C["ink"], font=FONT)
    im.save(LAYERS / f"{name}.png")


def ellipse(fill, inset=(6, 6, 6, 6), outline=C["ink"], width=3):
    return lambda d, s: d.ellipse((inset[0], inset[1], s[0]-inset[2], s[1]-inset[3]), fill=fill, outline=outline, width=width)


def capsule(fill):
    return lambda d, s: d.rounded_rectangle((8, 4, s[0]-8, s[1]-4), radius=min(s)//2, fill=fill, outline=C["ink"], width=3)


def plume(fill, bend: int):
    """Thick curved segment: joint at top-center, continuation low and left."""
    def paint(d, s):
        start = (s[0]//2, 22)
        end = (s[0]//2 + bend, s[1]-24)
        width = max(54, s[0]//2)
        d.line((start, end), fill=C["ink"], width=width+6)
        d.line((start, end), fill=fill, width=width)
        radius = width//2
        for x, y in (start, end):
            d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill, outline=C["ink"], width=3)
    return paint


def body(d, s):
    d.ellipse((185, 315, 615, 870), fill=C["teal"], outline=C["ink"], width=5)
    d.ellipse((255, 445, 545, 820), fill=C["cream"], outline=C["ink"], width=3)


def head(d, s):
    d.ellipse((18, 35, s[0]-18, s[1]-22), fill=C["teal"], outline=C["ink"], width=5)


def ear(side):
    def paint(d, s):
        pts = [(s[0]//2, 5), (s[0]-10, s[1]-12), (10, s[1]-12)]
        d.polygon(pts, fill=C["teal"], outline=C["ink"])
        inner = [(s[0]//2, 28), (s[0]-31, s[1]-30), (31, s[1]-30)]
        d.polygon(inner, fill=C["ear"], outline=C["rust"])
        for i in range(3):
            x = s[0]//2 + (-1 if side == "l" else 1) * (i-1)*8
            d.ellipse((x-4, 70+i*30, x+4, 78+i*30), fill=C["freckle"])
    return paint


def eyes(opened=True):
    def paint(d, s):
        for cx in (70, 170):
            if opened:
                d.ellipse((cx-50, 10, cx+50, s[1]-10), fill=C["white"], outline=C["ink"], width=4)
                d.ellipse((cx-19, 28, cx+19, s[1]-20), fill=C["iris"], outline=C["ink"], width=3)
                d.ellipse((cx-7, 42, cx+7, s[1]-30), fill=C["ink"])
            else:
                d.arc((cx-50, 5, cx+50, s[1]+20), 15, 165, fill=C["ink"], width=8)
    return paint


def crest(d, s):
    pts = [(8, s[1]-8), (35, 54), (66, s[1]-35), (94, 12), (125, s[1]-38), (154, 45), (190, s[1]-8)]
    d.polygon(pts, fill=C["crest"], outline=C["ink"])


def foot(side):
    def paint(d, s):
        d.ellipse((5, 10, s[0]-5, s[1]-5), fill=C["teal"], outline=C["ink"], width=3)
        d.ellipse((35 if side == "l" else 55, 45, 105 if side == "l" else 125, 80), fill=C["pad"])
    return paint


def muzzle(d, s):
    d.ellipse((4, 8, s[0]-4, s[1]-5), fill=C["cream"], outline=C["ink"], width=3)


def nose(d, s):
    d.ellipse((5, 4, s[0]-5, s[1]-5), fill=C["nose"], outline=C["ink"], width=3)


def cheeks(side):
    def paint(d, s):
        pts = [(s[0]//2, 8), (s[0]-8, 35), (s[0]-24, 62), (s[0]-5, 88), (s[0]//2, s[1]-5), (8, 88), (26, 62), (5, 35)]
        d.polygon(pts, fill=C["cream"], outline=C["ink"])
    return paint


def mouth(opened=False):
    def paint(d, s):
        if opened:
            d.ellipse((8, 5, s[0]-8, s[1]-5), fill=C["ink"], outline=C["rust"], width=3)
            d.ellipse((30, s[1]//2, s[0]-30, s[1]-12), fill=C["nose"])
        else:
            d.arc((5, -10, s[0]-5, s[1]-4), 20, 160, fill=C["ink"], width=6)
    return paint


def strap(d, s):
    d.line((15, 5, s[0]-15, s[1]-5), fill=C["leather"], width=18)
    d.line((s[0]-15, 5, 15, s[1]-5), fill=C["leather"], width=18)


def stage(d, s):
    d.rectangle((0, 0, s[0], s[1]), fill="#D8D2C4")
    d.rectangle((0, int(s[1]*.82), s[0], s[1]), fill="#9C927F")
    d.line((0, int(s[1]*.82), s[0], int(s[1]*.82)), fill=C["ink"], width=4)
    d.text((24, 24), "KIKO 2.5D PLACEHOLDER STAGE", fill=C["ink"], font=FONT)


# Root/body canvas establishes the rig's spacious 1600x2000 internal canvas.
layer("body", (800, 1000), body)
for name, size, paint in [
    ("tail_base", (180, 220), plume(C["teal"], -28)), ("tail_mid", (170, 210), plume(C["cream"], -25)),
    ("tail_tip", (160, 180), plume(C["rust"], -18)), ("thigh_l", (120, 260), capsule(C["teal"])),
    ("shin_l", (105, 250), capsule(C["cream"])), ("foot_l", (190, 105), foot("l")),
    ("thigh_r", (120, 260), capsule(C["teal"])), ("shin_r", (105, 250), capsule(C["cream"])),
    ("foot_r", (190, 105), foot("r")), ("upper_arm_l", (110, 250), capsule(C["teal"])),
    ("arm_l", (95, 245), capsule(C["cream"])), ("hand_l", (145, 145), ellipse(C["cream"])),
    ("upper_arm_r", (110, 250), capsule(C["teal"])), ("arm_r", (95, 245), capsule(C["cream"])),
    ("hand_r", (145, 145), ellipse(C["cream"])), ("head", (600, 560), head),
    ("ear_l", (190, 390), ear("l")), ("ear_r", (190, 390), ear("r")),
    ("muzzle", (270, 145), muzzle), ("nose", (82, 58), nose),
    ("eyes_open", (240, 125), eyes(True)), ("eyes_closed", (240, 70), eyes(False)),
    ("cheek_l", (125, 125), cheeks("l")), ("cheek_r", (125, 125), cheeks("r")),
    ("crest", (198, 235), crest), ("mouth_neutral", (135, 45), mouth(False)),
    ("mouth_open", (135, 90), mouth(True)), ("scarf", (390, 120), capsule(C["rust"])),
    ("vest", (420, 470), lambda d,s: d.rounded_rectangle((8,5,s[0]-8,s[1]-5), 80, fill=C["cloth"], outline=C["ink"], width=4)),
    ("harness_straps", (360, 390), strap), ("belt", (440, 85), capsule(C["leather"])),
    ("backpack", (390, 490), lambda d,s: d.rounded_rectangle((8,5,s[0]-8,s[1]-5), 95, fill=C["leather"], outline=C["ink"], width=4)),
    ("charm", (90, 125), lambda d,s: (d.line((s[0]//2,0,s[0]//2,35),fill=C["leather"],width=7), d.ellipse((12,30,s[0]-12,s[1]-8),fill=C["brass"],outline=C["ink"],width=3))),
]:
    layer(name, size, paint)

stage_im = Image.new("RGB", (1280, 720), "white"); stage(ImageDraw.Draw(stage_im), stage_im.size); stage_im.save(ROOT / "stage.png")
Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(ROOT / "kiko_2d_idle.png")
print(f"Generated {len(list(LAYERS.glob('*.png')))} placeholder layers in {LAYERS}")
