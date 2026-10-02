from io import BytesIO

from PIL import Image, ImageChops
from django.test import SimpleTestCase

from .share_images import render_card


class SharingImageLayoutTests(SimpleTestCase):
    def test_portrait_square_and_wide_images_keep_their_proportions_and_edges(self):
        for size in ((100, 300), (100, 100), (600, 100)):
            with self.subTest(size=size):
                source = Image.new("RGB", size, "red")
                # Different bands on each edge prove none of the artwork was cropped.
                source.paste("blue", (0, 0, size[0], 10))
                source.paste("green", (0, size[1] - 10, size[0], size[1]))
                source.paste("yellow", (0, 10, 10, size[1] - 10))
                stream = BytesIO()
                source.save(stream, format="PNG")
                stream.seek(0)
                with Image.open(BytesIO(render_card(stream, "white"))) as card:
                    self.assertEqual(card.size, (1200, 630))
                    bounds = ImageChops.difference(card, Image.new("RGB", card.size, "white")).getbbox()
                    left, top, right, bottom = bounds
                    self.assertGreaterEqual(left, 48)
                    self.assertGreaterEqual(top, 48)
                    self.assertEqual(left, 1200 - right)
                    self.assertLessEqual(abs(top - (630 - bottom)), 1)
                    self.assertAlmostEqual((right - left) / (bottom - top), size[0] / size[1], delta=0.02)
                    self.assertEqual(card.getpixel(((left + right) // 2, top)), (0, 0, 255))
                    self.assertEqual(card.getpixel(((left + right) // 2, bottom - 1)), (0, 128, 0))
                    self.assertEqual(card.getpixel((left, (top + bottom) // 2)), (255, 255, 0))

    def test_transparency_and_camera_orientation(self):
        source = Image.new("RGBA", (100, 300), (255, 0, 0, 128))
        source.getexif()[274] = 6
        stream = BytesIO()
        source.save(stream, format="PNG", exif=source.getexif())
        stream.seek(0)
        with Image.open(BytesIO(render_card(stream, "white"))) as card:
            bounds = ImageChops.difference(card, Image.new("RGB", card.size, "white")).getbbox()
            self.assertGreater(bounds[2] - bounds[0], bounds[3] - bounds[1])
            self.assertEqual(card.getpixel((600, 315)), (255, 127, 127))
