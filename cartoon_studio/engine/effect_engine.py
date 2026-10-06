from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from cartoon_studio.models.effects import Effect
from cartoon_studio.utils.interpolation import clamp


class EffectEngine:
    @staticmethod
    def apply(image: Image.Image, effects: list[Effect], frame: int, progress: float, seed: int) -> Image.Image:
        result = image
        for effect in effects:
            amount = effect.intensity
            if effect.type == "film_grain":
                rng = np.random.default_rng(np.random.SeedSequence([seed, frame, 101]))
                array = np.asarray(result).astype(np.int16)
                noise = rng.normal(0, 18 * amount, array.shape[:2])[:, :, None]
                array[:, :, :3] = np.clip(array[:, :, :3] + noise, 0, 255)
                result = Image.fromarray(array.astype(np.uint8), "RGBA")
            elif effect.type == "vignette":
                yy, xx = np.ogrid[-1:1:complex(result.height), -1:1:complex(result.width)]
                mask = np.clip((xx * xx + yy * yy - 0.25) * amount * 180, 0, 200).astype(np.uint8)
                overlay = Image.new("RGBA", result.size, (0, 0, 0, 0)); overlay.putalpha(Image.fromarray(mask))
                result = Image.alpha_composite(result, overlay)
            elif effect.type == "fog":
                overlay = Image.new("RGBA", result.size, (220, 230, 235, 0))
                draw = ImageDraw.Draw(overlay)
                shift = math.sin(frame * effect.speed * 0.1) * result.width * 0.2
                for i in range(5):
                    x = int((i / 4) * result.width + shift - result.width * 0.2)
                    draw.ellipse((x - result.width // 3, result.height // 3, x + result.width // 3, result.height), fill=(220, 230, 235, round(25 * amount)))
                result = Image.alpha_composite(result, overlay.filter(ImageFilter.GaussianBlur(max(2, result.width // 25))))
            elif effect.type == "darken": result = ImageEnhance.Brightness(result).enhance(1 - amount * 0.7)
            elif effect.type == "desaturate": result = ImageEnhance.Color(result).enhance(1 - amount)
            elif effect.type == "flash":
                alpha = round(255 * amount * max(0, 1 - progress * 8))
                result = Image.alpha_composite(result, Image.new("RGBA", result.size, (255, 255, 255, alpha)))
            elif effect.type == "fade":
                alpha = round(255 * amount * (1 - progress))
                result = Image.alpha_composite(result, Image.new("RGBA", result.size, (0, 0, 0, alpha)))
        return result

