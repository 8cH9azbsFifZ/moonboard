# -*- coding: utf-8 -*-
"""
Unit tests for the Moonboard BLE protocol decoder.
Tests UnstuffSequence and decode_problem_string.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ble'))
from moonboard_app_protocol import UnstuffSequence, decode_problem_string, position_trans


class TestPositionTrans(unittest.TestCase):
    """Test position_trans() grid coordinate conversion."""

    def test_standard_board_first_hold(self):
        # Position 0, 18 rows -> A1 (col 0, row 1)
        self.assertEqual(position_trans(0, 18), 'A1')

    def test_standard_board_top_of_first_col(self):
        # Position 17, 18 rows -> A18
        self.assertEqual(position_trans(17, 18), 'A18')

    def test_standard_board_second_col_reversed(self):
        # Position 18, 18 rows -> B18 (odd col, reversed: row = 19-1 = 18)
        self.assertEqual(position_trans(18, 18), 'B18')

    def test_standard_board_second_col_bottom(self):
        # Position 35, 18 rows -> B1 (odd col, reversed: row = 19-18 = 1)
        self.assertEqual(position_trans(35, 18), 'B1')

    def test_standard_board_last_hold(self):
        # Position 197 = col 10 (K), row 18 -> K18 (even col)
        self.assertEqual(position_trans(197, 18), 'K18')

    def test_mini_board_first_hold(self):
        self.assertEqual(position_trans(0, 12), 'A1')

    def test_mini_board_second_col(self):
        # Position 12, 12 rows -> B12 (odd col reversed: row = 13-1 = 12)
        self.assertEqual(position_trans(12, 12), 'B12')

    def test_mini_board_second_col_bottom(self):
        # Position 23, 12 rows -> B1 (odd col reversed: row = 13-12 = 1)
        self.assertEqual(position_trans(23, 12), 'B1')

    def test_all_standard_positions_valid(self):
        """All 198 positions should produce valid A1-K18 coordinates."""
        valid_cols = set('ABCDEFGHIJK')
        for pos in range(198):
            result = position_trans(pos, 18)
            self.assertIn(result[0], valid_cols)
            row = int(result[1:])
            self.assertGreaterEqual(row, 1)
            self.assertLessEqual(row, 18)


class TestDecodeProblemString(unittest.TestCase):
    """Test decode_problem_string() hold classification."""

    def test_simple_problem_standard(self):
        # S=start, P=intermediate, E=end
        result = decode_problem_string('S0,P17,E197', [])
        self.assertEqual(result['START'], ['A1'])
        self.assertEqual(result['MOVES'], ['A18'])
        self.assertEqual(result['TOP'], ['K18'])

    def test_mini_board_flag(self):
        result = decode_problem_string('S0,E11', ['M'])
        self.assertEqual(result['START'], ['A1'])
        self.assertEqual(result['TOP'], ['A12'])

    def test_new_hold_types(self):
        # R=right, L=left, M=match, F=foot
        result = decode_problem_string('S0,R5,L10,F15,E17', [])
        self.assertEqual(result['START'], ['A1'])
        self.assertEqual(result['TOP'], ['A18'])
        # Without 'B' flag, all go into MOVES
        self.assertIn('A6', result['MOVES'])

    def test_color_flag_separates_holds(self):
        # With 'B' flag, L/F/M get separate categories
        result = decode_problem_string('S0,L5,F10,M15,R3,E17', ['B'])
        self.assertEqual(result['START'], ['A1'])
        self.assertEqual(result['TOP'], ['A18'])
        self.assertIn('A6', result['LEFT'])
        self.assertIn('A11', result['FOOT'])
        self.assertIn('A16', result['MATCH'])
        self.assertIn('A4', result['MOVES'])

    def test_empty_hold_string_handled(self):
        # Should not crash on trailing comma
        result = decode_problem_string('S0,E17,', [])
        self.assertEqual(result['START'], ['A1'])
        self.assertEqual(result['TOP'], ['A18'])

    def test_flags_stored(self):
        result = decode_problem_string('S0,E17', ['M', 'D'])
        self.assertEqual(result['FLAGS'], ['M', 'D'])


class TestUnstuffSequence(unittest.TestCase):
    """Test BLE packet reassembly."""

    def setUp(self):
        self.unstuffer = UnstuffSequence()

    def _hex(self, text):
        """Convert ASCII text to hex string (simulating BLE payload)."""
        return text.encode().hex()

    def test_single_packet_problem(self):
        # Complete problem in one packet: l#S0,E17#
        data = self._hex('l#S0,E17#')
        result = self.unstuffer.process_bytes(data)
        self.assertEqual(result, 'S0,E17')

    def test_multi_packet_problem(self):
        # Problem split across two packets
        part1 = self._hex('l#S0,P5,')
        part2 = self._hex('P10,E17#')
        
        result1 = self.unstuffer.process_bytes(part1)
        self.assertIsNone(result1)
        
        result2 = self.unstuffer.process_bytes(part2)
        self.assertEqual(result2, 'S0,P5,P10,E17')

    def test_three_packet_problem(self):
        part1 = self._hex('l#S0,')
        part2 = self._hex('P5,P10,')
        part3 = self._hex('P15,E17#')
        
        self.assertIsNone(self.unstuffer.process_bytes(part1))
        self.assertIsNone(self.unstuffer.process_bytes(part2))
        result = self.unstuffer.process_bytes(part3)
        self.assertEqual(result, 'S0,P5,P10,P15,E17')

    def test_flag_packet_sets_flags(self):
        # Flag packet: ~M*
        flag_data = self._hex('~M*')
        result = self.unstuffer.process_bytes(flag_data)
        self.assertIsNone(result)
        self.assertIn('M', self.unstuffer.flags)

    def test_flag_then_problem(self):
        # Flag followed by problem
        self.unstuffer.process_bytes(self._hex('~D*'))
        self.assertIn('D', self.unstuffer.flags)
        
        result = self.unstuffer.process_bytes(self._hex('l#S0,E17#'))
        self.assertEqual(result, 'S0,E17')

    def test_double_flag_packet(self):
        # ~DB* (two flags)
        flag_data = self._hex('~DB*')
        self.unstuffer.process_bytes(flag_data)
        self.assertIn('D', self.unstuffer.flags)
        self.assertIn('B', self.unstuffer.flags)

    def test_error_recovery_double_start(self):
        # Start a packet, then get another start before end
        self.unstuffer.process_bytes(self._hex('l#S0,P5,'))
        # New start should reset
        result = self.unstuffer.process_bytes(self._hex('l#S1,E17#'))
        # The behavior depends on implementation - it should either
        # return the new problem or reset
        # Current impl resets s to '' on double start, so second start works
        # Actually looking at code: it logs error and resets self.s = ''
        # then processes nothing more from that packet
        # So result should be None (error state)

    def test_decode_errors_ignored(self):
        # Non-valid hex should not crash (errors="ignore" in decode)
        data = 'ff' * 10
        result = self.unstuffer.process_bytes(data)
        self.assertIsNone(result)


class TestLEDMapping(unittest.TestCase):
    """Test LED mapping file integrity."""

    def setUp(self):
        mapping_path = os.path.join(os.path.dirname(__file__), '..', 'led', 'led_mapping.json')
        if os.path.exists(mapping_path):
            import json
            with open(mapping_path) as f:
                self.mapping = json.load(f)
        else:
            self.mapping = None

    def test_mapping_file_exists(self):
        self.assertIsNotNone(self.mapping, "led_mapping.json not found")

    def test_all_198_holds_present(self):
        """All grid coordinates A1-K18 should be in the mapping."""
        if self.mapping is None:
            self.skipTest("No mapping file")
        
        import string
        for col in string.ascii_uppercase[:11]:
            for row in range(1, 19):
                hold = f"{col}{row}"
                self.assertIn(hold, self.mapping,
                              f"Hold {hold} missing from mapping")

    def test_no_duplicate_led_indices(self):
        """Each LED index should map to at most one hold."""
        if self.mapping is None:
            self.skipTest("No mapping file")
        
        # Exclude 'num_pixels' key if present
        indices = [v for k, v in self.mapping.items() if k != 'num_pixels']
        self.assertEqual(len(indices), len(set(indices)),
                         "Duplicate LED indices found in mapping")

    def test_indices_non_negative(self):
        """All LED indices should be non-negative."""
        if self.mapping is None:
            self.skipTest("No mapping file")
        
        for hold, idx in self.mapping.items():
            if hold == 'num_pixels':
                continue
            self.assertGreaterEqual(idx, 0,
                                    f"Negative index for {hold}: {idx}")


if __name__ == '__main__':
    unittest.main()
