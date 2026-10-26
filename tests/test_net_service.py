# -*- coding: utf-8 -*-
"""Unit tests for the WLAN access service (openspec/changes/add-wlan-access)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'net'))
from moonboard_net_service import (DEFAULT_ORIGINS, InvalidProblem, allowed_origin,
                                   validate_problem, validate_show)


class TestValidateProblem(unittest.TestCase):

    def test_valid_problem(self):
        msg = {"START": ["A1"], "MOVES": ["F9"], "TOP": ["K18"]}
        self.assertEqual(validate_problem(msg), msg)

    def test_optional_roles_kept(self):
        msg = {"START": ["A1"], "MOVES": [], "TOP": ["K18"], "FOOT": ["C2"], "LEFT": ["D5"]}
        self.assertEqual(validate_problem(msg)["FOOT"], ["C2"])

    def test_invalid_column(self):
        with self.assertRaisesRegex(InvalidProblem, "L5"):
            validate_problem({"START": ["L5"], "MOVES": [], "TOP": []})

    def test_invalid_row(self):
        with self.assertRaisesRegex(InvalidProblem, "A19"):
            validate_problem({"START": [], "MOVES": ["A19"], "TOP": []})

    def test_row_zero(self):
        with self.assertRaises(InvalidProblem):
            validate_problem({"START": ["A0"], "MOVES": [], "TOP": []})

    def test_missing_key(self):
        with self.assertRaisesRegex(InvalidProblem, "TOP"):
            validate_problem({"START": [], "MOVES": []})

    def test_unknown_key(self):
        with self.assertRaises(InvalidProblem):
            validate_problem({"START": [], "MOVES": [], "TOP": [], "X": []})

    def test_not_a_list(self):
        with self.assertRaises(InvalidProblem):
            validate_problem({"START": "A1", "MOVES": [], "TOP": []})


class TestShow(unittest.TestCase):

    def test_valid_mode(self):
        self.assertEqual(validate_show({"mode": "feuerreifen"}), "feuerreifen")

    def test_invalid_mode(self):
        for bad in ({"mode": "Zelt; rm"}, {"mode": ""}, {"mode": 3}, {}, []):
            with self.assertRaises(InvalidProblem):
                validate_show(bad)


class TestCors(unittest.TestCase):

    def test_manege_app_origin(self):
        self.assertEqual(allowed_origin("manege://app", DEFAULT_ORIGINS), "manege://app")


    def test_app_origin(self):
        self.assertEqual(allowed_origin("https://10.101.2.71:8443", DEFAULT_ORIGINS),
                         "https://10.101.2.71:8443")

    def test_foreign_origin(self):
        self.assertIsNone(allowed_origin("https://example.com", DEFAULT_ORIGINS))

    def test_no_origin(self):
        self.assertIsNone(allowed_origin(None, DEFAULT_ORIGINS))


class TestWallShowState(unittest.TestCase):
    """The show-mode state must not shadow Wall.show(), or no route reaches the wall."""

    def test_show_stays_callable_after_state_message(self):
        import moonboard_net_service as svc

        class Msg:
            topic = svc.SHOW_STATE
            payload = b"zirkus"

        wall = svc.Wall.__new__(svc.Wall)
        wall.show_mode = None
        self.assertTrue(callable(wall.show))
        wall._on_message(None, None, Msg())
        self.assertTrue(callable(wall.show))
        self.assertEqual(wall.show_mode, "zirkus")


if __name__ == '__main__':
    unittest.main()
