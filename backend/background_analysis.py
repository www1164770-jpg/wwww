"""Small, deterministic luminance analysis for persisted background metadata."""

from io import BytesIO
from PIL import Image


def relative_luminance(red, green, blue):
    def linear(channel):
        channel /= 255
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
    return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)


def analyze_background(content):
    with Image.open(BytesIO(content)) as source:
        image = source.convert("RGB")
        image.thumbnail((32, 32), Image.Resampling.BILINEAR)
        values = [relative_luminance(*pixel) for pixel in image.getdata()]
    average = sum(values) / len(values)
    return {
        "averageLuminance": round(average, 4),
        "darkRatio": round(sum(value < 0.25 for value in values) / len(values), 4),
        "lightRatio": round(sum(value > 0.75 for value in values) / len(values), 4),
        "contrastSpread": round(max(values) - min(values), 4),
        "recommendedTextMode": "dark" if average > 0.5 else "light",
    }
