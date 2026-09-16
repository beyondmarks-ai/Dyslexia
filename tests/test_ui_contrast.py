from pathlib import Path
import unittest


class UiContrastTests(unittest.TestCase):
    def test_form_widget_text_has_an_explicit_dark_color(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('[data-testid="stForm"] label', source)
        self.assertIn("color:#1e1b4b", source)
        self.assertIn('[data-testid="stForm"] * { color:#000 !important; }', source)

    def test_form_submit_button_has_high_contrast_color(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn("div.stFormSubmitButton > button, div.stFormSubmitButton > button * { color:#fff !important; }", source)
