from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def _wav(path: Path, duration: float, frequency: float, volume: float = 0.15) -> None:
    if path.exists():
        return
    rate = 22050
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, rate, round(duration * rate), "NONE", "not compressed"))
        values = bytearray()
        for index in range(round(duration * rate)):
            envelope = min(1.0, index / (rate * 0.2), (duration * rate - index) / (rate * 0.2))
            sample = int(32767 * volume * envelope * math.sin(math.tau * frequency * index / rate))
            values.extend(struct.pack("<h", sample))
        stream.writeframes(values)


CHARACTERS: dict[str, list[str]] = {
    "ta": ["calm", "worried", "sad", "shocked"], "yeay": ["calm", "worried", "scared", "sad"],
    "pu": ["neutral", "angry", "scared", "calm"], "ming": ["calm", "worried", "shocked", "sad"],
    "kmeng_bros": ["calm", "scared", "shocked", "happy"], "kmeng_srey": ["calm", "scared", "worried", "happy"],
    "sangha": ["calm", "neutral", "serious"], "kasekor": ["neutral", "tired", "worried", "calm"],
    "moto": ["neutral", "scared", "shocked"], "neary": ["calm", "worried", "scared", "sad"],
    "ap": ["glow", "menace"], "kmaoch": ["ghostly"], "pret": ["looming", "menace"],
    "beisach": ["angry", "menace"], "kmaoch_srey": ["ghostly", "sorrowful"],
    "meav": ["angry", "shocked", "sad", "sneaky"], "kandol": ["calm", "scared", "cheeky", "happy"],
    "chkae": ["happy", "angry", "alert"], "tonsay": ["calm", "cheeky", "worried"],
    "krapeu": ["greedy", "angry", "shocked"],
}
ENVIRONMENTS = ["forest_night", "forest_day", "village_night", "village_day", "pagoda_night", "pagoda_day", "ricefield_dusk", "ricefield_day", "road_night", "road_day", "room_interior", "room_night", "well_area", "graveyard_night", "river_bank", "market", "trees_far", "mountains_far", "sky_night", "sky_day"]
FOREGROUNDS = ["trees", "bushes", "tall_grass", "fence", "temple_pillar"]
PROPS = ["motorbike", "bicycle", "oil_lamp", "candle", "lantern", "well", "tree_single", "rock", "basket", "pot", "food_plate", "cheese", "banana", "coconut", "door", "window", "spirit_house", "incense", "log"]
OVERLAYS = ["fog_01", "fog_02", "fog_03", "moonlight_rays", "godray", "rain", "mist", "dust", "vignette", "film_grain", "light_flicker", "shadow_soft"]
EFFECTS = ["flash_white", "smoke_puff", "sparkle", "blood_splat"]
AUDIO = ["amb_crickets", "amb_wind", "amb_forest_night", "amb_rain", "amb_village", "amb_market", "music_horror_ambient", "music_tension", "music_chase", "music_lullaby", "music_fable_light", "sfx_sting", "sfx_whoosh", "sfx_heartbeat", "sfx_footsteps", "sfx_running", "sfx_door_creak", "sfx_crash", "sfx_victory", "sfx_ghost_whisper", "sfx_thunder", "sfx_bell", "sfx_tiptoe"]


def _placeholder(path: Path, size: tuple[int, int], label: str, *, transparent: bool, color: tuple[int, int, int]) -> None:
    if path.exists():
        return
    image = Image.new("RGBA", size, (0, 0, 0, 0) if transparent else (*color, 255))
    draw = ImageDraw.Draw(image)
    if transparent:
        margin = max(2, min(20, min(size) // 5))
        draw.rounded_rectangle((margin, margin, size[0] - margin, size[1] - margin), radius=margin, fill=(*color, 225), outline=(255, 255, 255, 210), width=max(3, margin // 8))
    bbox = draw.textbbox((0, 0), label)
    draw.text(((size[0] - (bbox[2] - bbox[0])) / 2, (size[1] - (bbox[3] - bbox[1])) / 2), label, fill="white", stroke_width=2, stroke_fill="black")
    image.save(path)


def create_full_asset_library(root: Path) -> dict[str, int]:
    """Create the complete documented placeholder catalog without replacing real art."""
    assets = root / "assets"
    counts = {"characters": 0, "backgrounds": 0, "foregrounds": 0, "props": 0, "overlays": 0, "effects": 0, "audio": 0}
    for folder in counts:
        (assets / folder).mkdir(parents=True, exist_ok=True)
    palette = [(48, 92, 125), (107, 69, 128), (45, 120, 83), (154, 83, 52), (82, 86, 150)]
    for index, (character_id, emotions) in enumerate(CHARACTERS.items()):
        folder = assets / "characters" / character_id; folder.mkdir(exist_ok=True)
        base = folder / f"{character_id}_idle.png"
        _placeholder(base, (700, 1000), character_id, transparent=True, color=palette[index % len(palette)])
        manifest = {"id": character_id, "pivot": "bottom_center", "files": {"idle": base.name}, "emotions": emotions, "actions": ["idle", "subtle_breathing", "walk_in_place", "look_left", "look_right", "shake", "float", "fade_in", "fade_out"], "size": [700, 1000]}
        (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        counts["characters"] += 1
    # Keep the canonical V2 puppet separate from the real/single-sprite Ta pack;
    # rig auto-discovery is directory-based.
    puppet = assets / "characters" / "ta_puppet"; parts = puppet / "parts"; parts.mkdir(parents=True, exist_ok=True)
    _placeholder(puppet / "ta_puppet_idle.png", (700, 1000), "ta_puppet", transparent=True, color=(48, 92, 125))
    puppet_parts = {
        "body.png": ((320, 520), (52, 102, 145)), "head.png": ((340, 300), (184, 132, 89)),
        "arm_l.png": ((100, 360), (52, 102, 145)), "arm_r.png": ((100, 360), (52, 102, 145)),
        "eyes_open.png": ((180, 70), (245, 245, 245)), "eyes_closed.png": ((180, 35), (50, 40, 35)),
        "mouth_closed.png": ((110, 35), (75, 30, 30)), "mouth_small.png": ((110, 55), (120, 35, 45)),
        "mouth_wide.png": ((120, 85), (145, 40, 50)),
    }
    for filename, (size, color) in puppet_parts.items():
        _placeholder(parts / filename, size, filename.removesuffix(".png"), transparent=True, color=color)
    rig = {"rig_version": 1, "parts": {
        "body": {"image": "parts/body.png", "pivot": [0.5, 0.95], "z": 0},
        "head": {"image": "parts/head.png", "parent": "body", "attach": [0.5, 0.15], "pivot": [0.5, 0.9], "z": 2},
        "arm_l": {"image": "parts/arm_l.png", "parent": "body", "attach": [0.25, 0.28], "pivot": [0.5, 0.05], "z": 1},
        "arm_r": {"image": "parts/arm_r.png", "parent": "body", "attach": [0.75, 0.28], "pivot": [0.5, 0.05], "z": 1},
        "eyes": {"image": "parts/eyes_open.png", "parent": "head", "attach": [0.5, 0.42], "pivot": [0.5, 0.5], "z": 3, "swap": {"open": "parts/eyes_open.png", "closed": "parts/eyes_closed.png"}},
        "mouth": {"image": "parts/mouth_closed.png", "parent": "head", "attach": [0.5, 0.72], "pivot": [0.5, 0.5], "z": 3, "swap": {"closed": "parts/mouth_closed.png", "small": "parts/mouth_small.png", "wide": "parts/mouth_wide.png"}}
    }}
    (puppet / "rig.json").write_text(json.dumps(rig, indent=2), encoding="utf-8")
    groups = [("backgrounds", ENVIRONMENTS, (1920, 1080), False), ("foregrounds", FOREGROUNDS, (1920, 1080), True), ("props", PROPS, (900, 900), True), ("overlays", OVERLAYS, (1920, 1080), True), ("effects", EFFECTS, (900, 900), True)]
    for group_index, (folder, names, size, transparent) in enumerate(groups):
        for index, name in enumerate(names):
            _placeholder(assets / folder / f"{name}.png", size, name, transparent=transparent, color=palette[(index + group_index) % len(palette)])
            counts[folder] += 1
    for index, name in enumerate(AUDIO):
        path = assets / "audio" / f"{name}.wav"
        if not path.exists():
            _wav(path, 1.0, 90 + index * 11, 0.025)
        counts["audio"] += 1
    dialogue = assets / "audio" / "ta_line_01.wav"
    if not dialogue.exists(): _wav(dialogue, 6.0, 185, 0.18)
    catalog = {"format_version": 1, "counts": counts, "characters": sorted(CHARACTERS), "backgrounds": ENVIRONMENTS, "foregrounds": FOREGROUNDS, "props": PROPS, "overlays": OVERLAYS, "effects": EFFECTS, "audio": AUDIO}
    (assets / "manifest.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    puppet_project = {
        "format_version": 1,
        "project": {"title": "Ta Puppet Narrator", "mode": "2.5d", "resolution": {"width": 1280, "height": 720}, "fps": 24, "seed": 23, "timing_mode": "scenes_driven"},
        "scenes": [
            {"id": f"ta_{action}", "duration": 2, "background": {"source": "assets/backgrounds/village_day.png", "scale": "cover"}, "layers": [{"id": "ta", "source": "assets/characters/ta_puppet/ta_puppet_idle.png", "type": "character", "position": {"x": 0.5, "y": 0.92}, "scale": 0.7}], "characters": [{"layer_id": "ta", "emotion": emotion, "action": action, "dialogue_audio": "assets/audio/ta_line_01.wav", "auto_blink": True}], "transition_out": {"type": "cut", "duration": 0}}
            for action, emotion in (("idle", "calm"), ("nod", "worried"), ("point", "serious"))
        ]
    }
    puppet_project_path = root / "projects" / "example_puppet_talk.json"
    if not puppet_project_path.exists(): puppet_project_path.write_text(json.dumps(puppet_project, ensure_ascii=False, indent=2), encoding="utf-8")
    return counts


def create_demo(root: Path, *, full: bool = False) -> Path:
    root = root.resolve()
    for folder in ("backgrounds", "foregrounds", "characters", "overlays", "audio"):
        (root / "assets" / folder).mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(exist_ok=True)
    size = (1280, 720)
    bg = Image.new("RGBA", size, "#07131d"); draw = ImageDraw.Draw(bg)
    for y in range(size[1]):
        shade = int(18 + 24 * y / size[1]); draw.line((0, y, size[0], y), fill=(3, shade, 28, 255))
    draw.ellipse((850, 70, 970, 190), fill=(210, 220, 190, 170))
    for x in range(46, 1280, 130):
        draw.polygon((x, 600, x + 65, 180, x + 130, 600), fill=(4, 35, 28, 255))
    background_path = root / "assets/backgrounds/forest_night.png"
    if not background_path.exists(): bg.save(background_path)
    trees = Image.new("RGBA", size, (0, 0, 0, 0)); draw = ImageDraw.Draw(trees)
    for x in (30, 1030):
        draw.rectangle((x, 0, x + 150, 720), fill=(3, 15, 14, 255)); draw.ellipse((x - 180, -100, x + 350, 280), fill=(2, 18, 12, 255))
    trees_path = root / "assets/foregrounds/trees.png"
    if not trees_path.exists(): trees.save(trees_path)
    character = Image.new("RGBA", (260, 520), (0, 0, 0, 0)); draw = ImageDraw.Draw(character)
    draw.ellipse((70, 20, 190, 145), fill=(20, 22, 28, 255)); draw.polygon((65, 130, 195, 130, 235, 500, 25, 500), fill=(12, 15, 22, 255)); draw.ellipse((105, 70, 120, 82), fill="white")
    character_path = root / "assets/characters/rith.png"
    if not character_path.exists(): character.save(character_path)
    ghost = Image.new("RGBA", (250, 420), (0, 0, 0, 0)); draw = ImageDraw.Draw(ghost)
    draw.ellipse((35, 0, 215, 180), fill=(220, 235, 230, 190)); draw.polygon((35, 90, 215, 90, 235, 410, 190, 370, 145, 415, 95, 370, 30, 410), fill=(210, 230, 225, 160)); draw.ellipse((80, 65, 105, 95), fill=(10, 15, 20, 220)); draw.ellipse((145, 65, 170, 95), fill=(10, 15, 20, 220))
    ghost_path = root / "assets/characters/ghost.png"
    if not ghost_path.exists(): ghost.save(ghost_path)
    fog = Image.new("RGBA", size, (0, 0, 0, 0)); draw = ImageDraw.Draw(fog)
    for x in range(-100, 1400, 200): draw.ellipse((x, 350, x + 500, 650), fill=(220, 230, 235, 30))
    fog_path = root / "assets/overlays/fog.png"
    if not fog_path.exists(): fog.filter(ImageFilter.GaussianBlur(45)).save(fog_path)
    _wav(root / "assets/audio/narration.wav", 6.0, 180, 0.08)
    _wav(root / "assets/audio/ambient.wav", 2.0, 65, 0.05)
    project = {
        "format_version": 1,
        "project": {"title": "ព្រៃអាថ៌កំបាំង", "mode": "2.5d", "resolution": {"width": 1280, "height": 720}, "fps": 24, "background_color": "#000000", "seed": 42, "timing_mode": "narration_driven"},
        "defaults": {"transition_duration": 0.5, "camera_easing": "ease_in_out", "music_volume": 0.12, "narration_volume": 1.0, "sfx_volume": 0.55},
        "audio": {"narration": "assets/audio/narration.wav", "background_music": "assets/audio/ambient.wav"},
        "scenes": [
            {"id": "scene_001", "duration": 2, "background": {"source": "assets/backgrounds/forest_night.png", "scale": "cover"}, "layers": [{"id": "fog", "source": "assets/overlays/fog.png", "type": "overlay", "depth": 0.2, "opacity": 0.45}, {"id": "trees", "source": "assets/foregrounds/trees.png", "depth": 0.9, "scale_mode": "cover"}], "camera": {"shot": "wide", "movement": "slow_push", "from": {"x": 0.5, "y": 0.5, "zoom": 1}, "to": {"x": 0.52, "y": 0.48, "zoom": 1.1}}, "effects": [{"type": "fog", "intensity": 0.25, "speed": 0.08}, {"type": "vignette", "intensity": 0.4}], "transition_out": {"type": "crossfade", "duration": 0.4}},
            {"id": "scene_002", "duration": 2, "background": {"source": "assets/backgrounds/forest_night.png", "scale": "cover"}, "layers": [{"id": "rith", "type": "character", "source": "assets/characters/rith.png", "depth": 0.75, "position": {"x": 0.55, "y": 0.78}, "scale": 0.75}], "camera": {"movement": "drift_right"}, "characters": [{"layer_id": "rith", "emotion": "worried", "action": "subtle_breathing"}], "effects": [{"type": "film_grain", "intensity": 0.12}], "audio": [{"source": "assets/audio/ambient.wav", "volume": 0.15, "loop": True}], "transition_out": {"type": "crossfade", "duration": 0.4}},
            {"id": "scene_003", "duration": 2, "background": {"source": "assets/backgrounds/forest_night.png", "scale": "cover"}, "layers": [{"id": "ghost", "type": "character", "source": "assets/characters/ghost.png", "depth": 0.35, "position": {"x": 0.68, "y": 0.5}, "scale": 0.7}], "characters": [{"layer_id": "ghost", "emotion": "ghostly", "action": "fade_in"}], "effects": [{"type": "shake", "intensity": 0.3}, {"type": "desaturate", "intensity": 0.25}, {"type": "vignette", "intensity": 0.5}], "transition_out": {"type": "fade_black", "duration": 0.8}}
        ]
    }
    target = root / "projects/example_forest_story.json"
    if not target.exists():
        target.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    if full:
        create_full_asset_library(root)
    return target
