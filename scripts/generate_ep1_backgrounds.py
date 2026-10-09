"""Generate background images for Jungle Pop Episode 1 locations."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "assets" / "backgrounds" / "jungle_pop"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1920, 1080


def gradient(top: tuple, bottom: tuple) -> Image.Image:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return img


def add_trees(img: Image.Image, count: int, color: tuple, base_y: int, height_range: tuple):
    draw = ImageDraw.Draw(img)
    import random
    rng = random.Random(42)
    for _ in range(count):
        x = rng.randint(0, W)
        h = rng.randint(*height_range)
        trunk_w = rng.randint(15, 35)
        # trunk
        draw.rectangle([x - trunk_w // 2, base_y - h, x + trunk_w // 2, base_y], fill=color)
        # canopy
        canopy_r = rng.randint(60, 140)
        canopy_color = (color[0] - 10, min(255, color[1] + 30), color[2] - 5)
        draw.ellipse([x - canopy_r, base_y - h - canopy_r, x + canopy_r, base_y - h + canopy_r // 2], fill=canopy_color)
    return img


def add_light_rays(img: Image.Image, count: int = 5, alpha: int = 30):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    import random
    rng = random.Random(99)
    for _ in range(count):
        x = rng.randint(0, W)
        w = rng.randint(40, 120)
        color = (255, 255, 200, alpha)
        draw.polygon([(x, 0), (x - w, H), (x + w, H)], fill=color)
    overlay = overlay.filter(ImageFilter.GaussianBlur(30))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


def fruit_grove():
    img = gradient((135, 206, 180), (60, 120, 50))
    img = add_trees(img, 8, (80, 60, 30), H - 100, (200, 400))
    # ground
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, H - 150, W, H], fill=(55, 110, 45))
    draw.rectangle([0, H - 100, W, H], fill=(45, 95, 35))
    img = add_light_rays(img, 6, 25)
    img.save(OUT / "fruit_grove.png")
    print("  fruit_grove.png")


def jungle_path():
    img = gradient((50, 100, 50), (25, 60, 25))
    img = add_trees(img, 15, (50, 40, 20), H - 80, (300, 550))
    draw = ImageDraw.Draw(img)
    # path
    draw.polygon([(W // 2 - 30, H), (W // 2 + 30, H), (W // 2 + 5, H // 3), (W // 2 - 5, H // 3)], fill=(90, 70, 45))
    draw.rectangle([0, H - 80, W, H], fill=(35, 75, 30))
    img = add_light_rays(img, 3, 15)
    img.save(OUT / "jungle_path.png")
    print("  jungle_path.png")


def old_jungle_boundary():
    img = gradient((35, 70, 50), (15, 40, 25))
    img = add_trees(img, 20, (40, 30, 15), H - 60, (400, 650))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, H - 80, W, H], fill=(25, 55, 20))
    # massive roots
    import random
    rng = random.Random(77)
    for _ in range(6):
        x = rng.randint(0, W)
        draw.ellipse([x - 80, H - 180, x + 80, H - 40], fill=(55, 40, 25))
    img = add_light_rays(img, 2, 10)
    img.save(OUT / "old_jungle_boundary.png")
    print("  old_jungle_boundary.png")


def ancient_tree_area():
    img = gradient((30, 65, 55), (10, 35, 20))
    draw = ImageDraw.Draw(img)
    # giant ancient tree center
    draw.rectangle([W // 2 - 80, 50, W // 2 + 80, H - 60], fill=(60, 45, 25))
    draw.ellipse([W // 2 - 250, -100, W // 2 + 250, 250], fill=(30, 70, 30))
    # ground clearing
    draw.ellipse([W // 2 - 350, H - 250, W // 2 + 350, H + 50], fill=(40, 80, 35))
    draw.rectangle([0, H - 60, W, H], fill=(30, 60, 25))
    # golden light shaft center
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon([(W // 2 - 60, 0), (W // 2 + 60, 0), (W // 2 + 120, H), (W // 2 - 120, H)], fill=(255, 245, 180, 20))
    overlay = overlay.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img, overlay).convert("RGB")
    # surrounding trees
    img = add_trees(img, 12, (45, 35, 18), H - 50, (350, 600))
    img.save(OUT / "ancient_tree_area.png")
    print("  ancient_tree_area.png")


def kiko_home_night():
    img = gradient((15, 15, 40), (8, 8, 20))
    draw = ImageDraw.Draw(img)
    # house shape
    draw.rectangle([W // 2 - 300, H // 2 - 100, W // 2 + 300, H - 80], fill=(70, 55, 40))
    # roof
    draw.polygon([(W // 2 - 350, H // 2 - 100), (W // 2, H // 2 - 280), (W // 2 + 350, H // 2 - 100)], fill=(90, 50, 30))
    # window with warm glow
    draw.rectangle([W // 2 - 80, H // 2, W // 2 + 80, H // 2 + 120], fill=(220, 180, 100))
    # warm interior glow
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([W // 2 - 200, H // 2 - 80, W // 2 + 200, H // 2 + 200], fill=(220, 180, 100, 30))
    overlay = overlay.filter(ImageFilter.GaussianBlur(60))
    img = Image.alpha_composite(img, overlay).convert("RGB")
    # ground
    draw2 = ImageDraw.Draw(img)
    draw2.rectangle([0, H - 80, W, H], fill=(20, 20, 15))
    # stars
    import random
    rng = random.Random(123)
    for _ in range(50):
        x, y = rng.randint(0, W), rng.randint(0, H // 3)
        draw2.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(200, 200, 220))
    img.save(OUT / "kiko_home_night.png")
    print("  kiko_home_night.png")


def kiko_home_interior():
    img = gradient((80, 60, 40), (50, 35, 25))
    draw = ImageDraw.Draw(img)
    # floor
    draw.rectangle([0, H - 200, W, H], fill=(90, 65, 40))
    # walls
    draw.rectangle([0, 0, 60, H], fill=(75, 55, 35))
    draw.rectangle([W - 60, 0, W, H], fill=(75, 55, 35))
    # window
    draw.rectangle([W - 250, 150, W - 100, 400], fill=(15, 15, 40))
    # lantern glow
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([W // 2 - 300, H // 2 - 200, W // 2 + 300, H // 2 + 200], fill=(255, 200, 100, 40))
    overlay = overlay.filter(ImageFilter.GaussianBlur(80))
    img = Image.alpha_composite(img, overlay).convert("RGB")
    img.save(OUT / "kiko_home_interior.png")
    print("  kiko_home_interior.png")


if __name__ == "__main__":
    print("Generating Jungle Pop EP1 backgrounds...")
    fruit_grove()
    jungle_path()
    old_jungle_boundary()
    ancient_tree_area()
    kiko_home_night()
    kiko_home_interior()
    print("Done!")
