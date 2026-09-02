import io
import unittest
from PIL import Image
from backend.background_analysis import analyze_background


def encoded(color):
    result = io.BytesIO(); Image.new("RGB", (32, 32), color).save(result, "WEBP"); return result.getvalue()


class BackgroundAnalysisTests(unittest.TestCase):
    def test_white_recommends_dark_text(self): self.assertEqual(analyze_background(encoded("white"))["recommendedTextMode"], "dark")
    def test_black_recommends_light_text(self): self.assertEqual(analyze_background(encoded("black"))["recommendedTextMode"], "light")
    def test_mixed_image_has_large_contrast_spread(self):
        image = Image.new("RGB", (32, 32), "white")
        for x in range(16):
            for y in range(32): image.putpixel((x, y), (0, 0, 0))
        output = io.BytesIO(); image.save(output, "WEBP")
        analysis = analyze_background(output.getvalue())
        self.assertGreater(analysis["contrastSpread"], 0.9)
        self.assertGreater(analysis["darkRatio"], 0.4)
        self.assertGreater(analysis["lightRatio"], 0.4)
