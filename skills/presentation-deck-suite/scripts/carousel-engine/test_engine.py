"""Run: python3 -m unittest test_engine (the render test needs Chrome and takes ~5s)."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import engine


class ParseTest(unittest.TestCase):
    def test_slide_headers(self):
        slides = engine.parse_script("Slide 1\nBig hook\n\nSlide 2: Short head\nlonger body line\nmore")
        self.assertEqual(slides[0], {"layout": "cover", "headline": "Big hook"})
        self.assertEqual(slides[1], {"layout": "text", "headline": "Short head", "body": "longer body line\nmore"})

    def test_header_edge_cases(self):
        slides = engine.parse_script("Intro line\nSlide 1 — Hook\nSlide 3 of the funnel matters most")
        self.assertEqual(slides[0]["headline"], "Intro line")
        self.assertEqual(slides[1], {"layout": "text", "headline": "Hook", "body": "Slide 3 of the funnel matters most"})

    def test_partial_font_override_keeps_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "b.json").write_text('{"fonts": {"headline": {"weight": 700}}}')
            brand = engine.load_brand(Path(d) / "b.json")
            self.assertEqual(brand["fonts"]["headline"]["family"], "Helvetica Neue")
            engine.font_css(brand)

    def test_blank_line_fallback_and_long_text_is_body(self):
        long = "x" * 200
        slides = engine.parse_script(f"Hook\n\n{long}")
        self.assertEqual([s.get("headline") for s in slides], ["Hook", None])
        self.assertEqual(slides[1]["body"], long)


class MarkupTest(unittest.TestCase):
    def test_emphasis_and_escaping(self):
        out = engine.markup("a *b* _c_ <script> snake_case_name")
        self.assertIn('<span class="em">b</span>', out)
        self.assertIn('<span class="aside f-aside">c</span>', out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("snake_case_name", out)


class RenderTest(unittest.TestCase):
    def test_render_produces_sized_slides_pdf_and_sheet(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            Image.new("RGB", (400, 300), "red").save(d / "shot.png")
            spec = {"handle": "@t", "slides": [
                {"layout": "cover", "headline": "Hi *there*"},
                {"layout": "image", "body": "words " * 300, "image": {"src": "shot.png", "crop": [10, 10, 200, 200]}},
            ]}
            (d / "slides.json").write_text(json.dumps(spec))
            engine.render(d / "slides.json", d / "out")
            for n in (1, 2):
                self.assertEqual(Image.open(d / "out" / f"slide0{n}.png").size, (1080, 1350))
            self.assertTrue((d / "out" / "carousel.pdf").stat().st_size > 0)
            self.assertTrue((d / "out" / "contact-sheet.jpg").exists())


if __name__ == "__main__":
    unittest.main()
