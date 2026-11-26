import struct
import unittest

import test_layout as fixture
from scripts.build_brand_assets import render_logo
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QLabel


class BrandAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ResponsiveLayoutTests.setUpClass.__func__(cls)

    def test_logo_has_transparency_safe_edges_and_no_colored_fragments_at_the_bottom(self):
        image = QImage(str(fixture.ROOT / "assets/youtube-sync-logo.png"))
        self.assertFalse(image.isNull())
        self.assertTrue(image.hasAlphaChannel())
        self.assertEqual(image.width(), image.height())
        margin = image.width() // 16
        for position in range(image.width()):
            for x, y in ((position, 0), (position, margin), (position, image.height() - margin),
                         (position, image.height() - 1), (0, position), (margin, position),
                         (image.width() - margin, position), (image.width() - 1, position)):
                self.assertEqual(image.pixelColor(x, y).alpha(), 0)

    def test_ico_contains_eight_valid_size_frames(self):
        path = fixture.ROOT / "assets/youtube-sync.ico"
        data = path.read_bytes()
        self.assertEqual(struct.unpack_from("<HHH", data), (0, 1, 8))
        sizes = []
        for index in range(8):
            width, height, _, _, planes, bits, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + index * 16)
            self.assertEqual(width, height)
            self.assertEqual((planes, bits), (1, 32))
            frame = QImage.fromData(data[offset:offset + length], "PNG")
            size = width or 256
            self.assertEqual((frame.width(), frame.height()), (size, size))
            sizes.append(size)
        self.assertEqual(sizes, [16, 20, 24, 32, 48, 64, 128, 256])
        self.assertFalse(QIcon(str(path)).isNull())

    def test_png_matches_the_canonical_vector_source(self):
        image = QImage(str(fixture.ROOT / "assets/youtube-sync-logo.png"))
        expected = render_logo(fixture.ROOT / "assets/youtube-sync-logo.svg", 1024)
        self.assertEqual(image.convertToFormat(QImage.Format_RGBA8888), expected.convertToFormat(QImage.Format_RGBA8888))

    def test_header_logo_uses_its_own_fixed_frame_and_the_vector_source(self):
        case = fixture.ResponsiveLayoutTests()
        case.app = self.app
        case.setUp()
        try:
            logo = case.window.findChild(QLabel, "AppLogo")
            self.assertIsNotNone(logo)
            self.assertEqual((logo.width(), logo.height()), (64, 64))
            self.assertFalse(logo.pixmap().isNull())
            self.assertEqual(logo.minimumSize(), logo.maximumSize())
        finally:
            case.tearDown()
