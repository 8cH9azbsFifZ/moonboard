# -*- coding: utf-8 -*-
"""Unit tests for free-colour frames (openspec/changes/add-pixel-display)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'led'))
from frame import InvalidFrame, parse_frame


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


if __name__ == '__main__':
    unittest.main()
