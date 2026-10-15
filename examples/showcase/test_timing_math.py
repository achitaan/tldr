import unittest
from timing_math import timing_window


class TimingWindowTests(unittest.TestCase):
    def test_both_endpoints_and_margin(self):
        result=timing_window(10,2,1,6,12)
        self.assertEqual((result['required_start'],result['required_end']),(8,11))
        self.assertEqual((result['setup_margin'],result['hold_margin']),(2,1))
        self.assertTrue(result['passes'])

    def test_late_arrival_fails_setup_even_before_edge(self):
        result=timing_window(10,2,1,8.5,12)
        self.assertEqual(result['setup_margin'],-.5)
        self.assertFalse(result['passes'])

    def test_early_change_fails_hold_with_good_setup(self):
        result=timing_window(10,2,1,6,10.5)
        self.assertEqual((result['setup_margin'],result['hold_margin']),(2,-.5))
        self.assertFalse(result['passes'])

    def test_prediction_and_equality_boundaries(self):
        result=timing_window(10,2,1,7,11.5)
        self.assertEqual((result['setup_margin'],result['hold_margin']),(1,.5))
        self.assertTrue(result['passes'])
        self.assertTrue(timing_window(10,2,1,8,11)['passes'])

    def test_invalid_domains(self):
        for args in ((10,2,1,12,6),(1,2,1,0,3),(10,-1,1,6,12),(10,2,1,float('nan'),12),(True,2,1,6,12)):
            with self.subTest(args=args),self.assertRaises(ValueError):timing_window(*args)
