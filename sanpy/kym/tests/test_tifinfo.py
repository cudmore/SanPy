#!/usr/bin/env python3
"""
Unit tests for TifInfo dataclass
"""

import unittest
from sanpy.kym.tif_info import TifInfo

class TestTifInfo(unittest.TestCase):
    def setUp(self):
        TifInfo.set_possible_conditions(['Control', 'Ivab', 'Thap', 'FCCP'])
        TifInfo.set_possible_regions(['ISAN', 'SSAN'])

    def test_required_examples(self):
        """Test the specific examples provided by the user."""
        test_cases = [
            {
                'filename': '20250312 ISAN FCCP R1 LS1.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'FCCP',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250312 SSAN R1 LS1.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 SSAN R1 LS1',
                    'condition': 'Control',
                    'region': 'SSAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250312 ISAN R1 LS1 FCCP.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'FCCP',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250312 ISAN R1 LS1 Control.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'Control',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250602 ISAN R1 LS1 Ivab.tif',
                'expected': {
                    'date': '20250602',
                    'cellid': '20250602 ISAN R1 LS1',
                    'condition': 'Ivab',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250602 ISAN R1 LS1.tif',
                'expected': {
                    'date': '20250602',
                    'cellid': '20250602 ISAN R1 LS1',
                    'condition': 'Control',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            }
        ]
        for i, test_case in enumerate(test_cases, 1):
            with self.subTest(i=i, filename=test_case['filename']):
                filename = test_case['filename']
                expected = test_case['expected']
                tif_info = TifInfo.from_filename(filename)
                self.assertEqual(tif_info.date, expected['date'])
                self.assertEqual(tif_info.cellid, expected['cellid'])
                self.assertEqual(tif_info.condition, expected['condition'])
                self.assertEqual(tif_info.region, expected['region'])
                self.assertEqual(tif_info.repeat, expected['repeat'])
                self.assertEqual(tif_info.error, expected['error'])

    def test_repeat_numbers(self):
        test_cases = [
            {'filename': '20250312 ISAN R1 LS1_0001.tif', 'expected_repeat': 1},
            {'filename': '20250312 ISAN FCCP R1 LS1_0002.tif', 'expected_repeat': 2},
            {'filename': '20250312 SSAN R2 LS3 Thap_0003.tif', 'expected_repeat': 3},
            {'filename': '20250312 ISAN R1 LS1_0000.tif', 'expected_repeat': 0},
            {'filename': '20250312 ISAN R1 LS1_9999.tif', 'expected_repeat': 9999}
        ]
        for i, test_case in enumerate(test_cases, 1):
            with self.subTest(i=i, filename=test_case['filename']):
                tif_info = TifInfo.from_filename(test_case['filename'])
                self.assertEqual(tif_info.repeat, test_case['expected_repeat'])
                self.assertEqual(tif_info.error, "")

    def test_edge_cases(self):
        test_cases = [
            {
                'filename': 'invalid_filename.tif',
                'description': 'Invalid filename with insufficient parts',
                'expected_error_contains': 'insufficient parts'
            },
            {
                'filename': '20250312 UNKNOWN R1 LS1.tif',
                'description': 'Unknown region',
                'expected_error_contains': 'Region not found'
            },
            {
                'filename': '20250312 ISAN R1 LS1_abc.tif',
                'description': 'Invalid repeat number format (non-digits)',
                'expected_repeat': 0
            },
            {
                'filename': '20250312 ISAN R1 LS1_0001_extra.tif',
                'description': 'Extra text after repeat number (not at end)',
                'expected_repeat': 0
            },
            {
                'filename': '20250312 ISAN R1 LS1.tif',
                'description': 'Valid filename without extension',
                'expected_error': ''
            },
            {
                'filename': '20250312 ISAN R1 LS1_12.tif',
                'description': 'Repeat number too short (2 digits instead of 3-4)',
                'expected_repeat': 0
            },
            {
                'filename': '20250312 ISAN R1 LS1_12345.tif',
                'description': 'Repeat number too long (5 digits instead of 3-4)',
                'expected_repeat': 0
            }
        ]
        for i, test_case in enumerate(test_cases, 1):
            with self.subTest(i=i, filename=test_case['filename']):
                tif_info = TifInfo.from_filename(test_case['filename'])
                if 'expected_error_contains' in test_case:
                    self.assertIn(test_case['expected_error_contains'], tif_info.error)
                elif 'expected_error' in test_case:
                    self.assertEqual(tif_info.error, test_case['expected_error'])
                elif 'expected_repeat' in test_case:
                    self.assertEqual(tif_info.repeat, test_case['expected_repeat'])

    def test_configurable_conditions_and_regions(self):
        TifInfo.set_possible_conditions(['Control', 'Ivab', 'Thap', 'FCCP', 'ATP'])
        tif_info = TifInfo.from_filename('20250312 ISAN R1 LS1 ATP.tif')
        self.assertEqual(tif_info.condition, 'ATP')
        TifInfo.set_possible_regions(['ISAN', 'SSAN', 'ESAN'])
        tif_info = TifInfo.from_filename('20250312 ESAN R1 LS1.tif')
        self.assertEqual(tif_info.region, 'ESAN')
        tif_info = TifInfo.from_filename('20250312 ISAN R1 LS1 FCCP.tif')
        self.assertEqual(tif_info.condition, 'FCCP')

    def test_date_validation(self):
        test_cases = [
            {'filename': '20250312 ISAN R1 LS1.tif', 'should_pass': True},
            {'filename': '2025031 ISAN R1 LS1.tif', 'should_pass': False},
            {'filename': '202503123 ISAN R1 LS1.tif', 'should_pass': False},
            {'filename': '2025031a ISAN R1 LS1.tif', 'should_pass': False}
        ]
        for i, test_case in enumerate(test_cases, 1):
            tif_info = TifInfo.from_filename(test_case['filename'])
            if test_case['should_pass']:
                self.assertNotEqual(tif_info.date, "")
                self.assertEqual(tif_info.error, "")
            else:
                self.assertIn("not a valid 8-digit date", tif_info.error)

    def test_multiple_spaces(self):
        test_cases = [
            {
                'filename': '20250312  ISAN  FCCP  R1  LS1.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'FCCP',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250312   ISAN   R1   LS1.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'Control',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250312 ISAN  FCCP  R1  LS1.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'FCCP',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250312    ISAN    R1    LS1    Control.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'Control',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250312 ISAN R1 LS1  Ivab.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'Ivab',
                    'region': 'ISAN',
                    'repeat': 0,
                    'error': ''
                }
            },
            {
                'filename': '20250312  ISAN  R1  LS1  Thap  0001.tif',
                'expected': {
                    'date': '20250312',
                    'cellid': '20250312 ISAN R1 LS1',
                    'condition': 'Thap',
                    'region': 'ISAN',
                    'repeat': 1,
                    'error': ''
                }
            }
        ]
        for i, test_case in enumerate(test_cases, 1):
            tif_info = TifInfo.from_filename(test_case['filename'])
            expected = test_case['expected']
            self.assertEqual(tif_info.date, expected['date'])
            self.assertEqual(tif_info.cellid, expected['cellid'])
            self.assertEqual(tif_info.condition, expected['condition'])
            self.assertEqual(tif_info.region, expected['region'])
            self.assertEqual(tif_info.repeat, expected['repeat'])
            self.assertEqual(tif_info.error, expected['error'])

if __name__ == '__main__':
    unittest.main() 