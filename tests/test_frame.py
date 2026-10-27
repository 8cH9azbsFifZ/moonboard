# -*- coding: utf-8 -*-
"""Unit tests for free-colour frames (openspec/changes/add-pixel-display)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'led'))
from frame import InvalidFrame, apply_color_order, load_color_order, parse_frame


class TestParseFrame(unittest.TestCase):

    def test_valid_frame(self):
        self.assertEqual(parse_frame({"pixels": {"A1": [255, 190, 0], "K18": [0, 0, 255]}}),
                         {"A1": (255, 190, 0), "K18": (0, 0, 255)})

    def test_empty_frame_clears(self):
        self.assertEqual(parse_frame({"pixels": {}}), {})

    def test_invalid_position(self):
        with self.assertRaisesRegex(InvalidFrame, "L3"):
            parse_frame({"pixels": {"L3": [1, 2, 3]}})

    def test_colour_out_of_range(self):
        with self.assertRaises(InvalidFrame):
            parse_frame({"pixels": {"A1": [256, 0, 0]}})

    def test_colour_wrong_shape(self):
        with self.assertRaises(InvalidFrame):
            parse_frame({"pixels": {"A1": [1, 2]}})

    def test_bool_is_not_a_colour(self):
        with self.assertRaises(InvalidFrame):
            parse_frame({"pixels": {"A1": [True, 0, 0]}})

    def test_missing_pixels(self):
        with self.assertRaises(InvalidFrame):
            parse_frame({"START": []})


class TestColorOrder(unittest.TestCase):

    def setUp(self):
        self.order = load_color_order(os.path.join(os.path.dirname(__file__), '..', 'led', 'color_order.json'))

    def test_all_strips_rgb(self):
        # Geprüft 2026-10-27 an der Wand: linke und rechte Streifen zeigen rohe Werte gleich.
        for index in (0, 268, 271, 412, 593):
            self.assertEqual(apply_color_order(index, (0, 255, 0), self.order), (0, 255, 0))
            self.assertEqual(apply_color_order(index, (255, 0, 0), self.order), (255, 0, 0))

    def test_grb_range_still_supported(self):
        order = {"default": "RGB", "ranges": [{"from": 10, "to": 20, "order": "GRB"}]}
        self.assertEqual(apply_color_order(15, (0, 255, 0), order), (255, 0, 0))
        self.assertEqual(apply_color_order(25, (0, 255, 0), order), (0, 255, 0))

    def test_blue_unaffected(self):
        self.assertEqual(apply_color_order(400, (0, 0, 255), self.order), (0, 0, 255))

    def test_missing_file_means_rgb(self):
        order = load_color_order('/nonexistent.json')
        self.assertEqual(apply_color_order(400, (1, 2, 3), order), (1, 2, 3))


if __name__ == '__main__':
    unittest.main()
