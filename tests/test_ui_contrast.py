from pathlib import Path
import unittest


class UiContrastTests(unittest.TestCase):
    def test_app_uses_an_explicit_light_theme(self):
        theme = Path(".streamlit/config.toml").read_text(encoding="utf-8")
        self.assertIn('base = "light"', theme)
        self.assertIn('backgroundColor = "#F8FAFC"', theme)
        self.assertIn('textColor = "#1E1B4B"', theme)

    def test_page_text_does_not_rely_on_generated_streamlit_classes(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertNotIn('[class*="css"]', source)
        self.assertIn('.stApp p, .stApp li, .stApp label', source)
        self.assertIn('[data-testid="stCaptionContainer"]', source)

    def test_form_widget_text_has_an_explicit_dark_color(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('[data-testid="stForm"] label', source)
        self.assertIn("color:#1e1b4b", source)
        self.assertIn('[data-testid="stForm"] * { color:#000 !important; }', source)

    def test_form_submit_button_has_high_contrast_color(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn("div.stFormSubmitButton > button, div.stFormSubmitButton > button * { color:#fff !important; }", source)

    def test_result_has_prominent_disclaimer_and_colored_meter(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn(".danger-notice", source)
        self.assertIn("Screening likelihood score", source)
        self.assertIn("linear-gradient(90deg,#15803d 0 33%,#d97706 33% 66%,#b91c1c 66% 100%)", source)
