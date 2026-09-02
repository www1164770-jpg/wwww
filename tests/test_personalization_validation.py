import unittest

from backend.personalization import default_settings, normalize_settings


class PersonalizationValidationTests(unittest.TestCase):
    def test_default_settings_are_safe_and_independent(self):
        first = default_settings(); second = default_settings()
        first["background"]["color"] = "#000000"
        self.assertEqual(second["background"]["color"], "#F8FAFC")

    def test_normalizes_valid_gradient_and_card_settings(self):
        settings = normalize_settings({"background": {"type": "gradient"}, "gradient": {"angle": 90, "stops": [{"color": "#FFFFFF", "position": 100}, {"color": "#000000", "position": 0}]}, "card": {"opacity": 75}})
        self.assertEqual(settings["background"]["type"], "gradient")
        self.assertEqual(settings["gradient"]["stops"][0]["position"], 0)
        self.assertEqual(settings["card"]["opacity"], 75)

    def test_rejects_bad_gradient_and_unknown_background(self):
        with self.assertRaises(ValueError): normalize_settings({"background": {"type": "script"}})
        with self.assertRaises(ValueError): normalize_settings({"gradient": {"stops": [{"color": "#FFFFFF", "position": 0}]}})
        with self.assertRaises(ValueError): normalize_settings({"gradient": {"stops": [{"color": "red", "position": 0}, {"color": "#FFFFFF", "position": 100}]}})

    def test_limits_custom_themes_to_five(self):
        themes = [{"key": str(index), "name": str(index), "settings": {}} for index in range(8)]
        self.assertEqual(len(normalize_settings({"customThemes": themes})["customThemes"]), 5)

    def test_persists_independent_desktop_and_mobile_composition(self):
        settings = normalize_settings({"background": {"type": "image", "desktop": {"positionX": 20, "positionY": 30, "scale": 2, "rotation": 90}, "mobile": {"positionX": 80, "positionY": 70, "scale": 1.5, "rotation": -45}}})
        self.assertEqual(settings["background"]["desktop"]["scale"], 2)
        self.assertEqual(settings["background"]["mobile"]["positionX"], 80)

    def test_clamps_invalid_composition_values_to_safe_defaults(self):
        settings = normalize_settings({"background": {"desktop": {"scale": 30, "rotation": 500, "positionX": -1}}})
        self.assertEqual(settings["background"]["desktop"], {"positionX": 50, "positionY": 50, "scale": 1, "rotation": 0})


if __name__ == "__main__":
    unittest.main()
