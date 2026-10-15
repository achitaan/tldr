import unittest

from source_focus import box_in_view


class SourceFocusTests(unittest.TestCase):
    def assertBox(self, actual, expected):
        self.assertIsNotNone(actual)
        for value, target in zip(actual, expected):
            self.assertAlmostEqual(value, target)

    def test_receiving_endpoint_maps_to_detail(self):
        self.assertBox(box_in_view((.33, .245, .04, .045), (.005, .16, .42, .59)),
                       (.325 / .42, .085 / .59, .04 / .42, .045 / .59))

    def test_partial_overlay_stops_at_crop_boundary(self):
        self.assertBox(box_in_view((.735, .50, .20, .05), (.39, .47, .47, .31)),
                       (.345 / .47, .03 / .31, .125 / .47, .05 / .31))

    def test_full_view_preserves_page_annotation(self):
        self.assertBox(box_in_view((.1, .2, .3, .4), (0, 0, 1, 1)), (.1, .2, .3, .4))

    def test_disjoint_and_touching_have_no_visible_area(self):
        self.assertIsNone(box_in_view((.7, .7, .1, .1), (.1, .1, .2, .2)))
        self.assertIsNone(box_in_view((.5, 0, .2, .2), (0, 0, .5, 1)))

    def test_invalid_geometry_is_rejected(self):
        for bounds in ((0, 0, 0, .1), (0, 0, -1, .1), (.9, 0, .2, .1), (float('nan'), 0, .1, .1), (True, 0, .1, .1)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                box_in_view(bounds, (0, 0, 1, 1))
