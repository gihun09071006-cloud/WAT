"""Unit tests for the ad-units-per-quest model (A4).

Run: python -m unittest test_ad_units_model -v
"""
import unittest

import ad_units_model as m


class TestCompletion(unittest.TestCase):
    def test_free_tolerance(self):
        self.assertEqual(m.completion_rate(2, n_free=2), 1.0)
        self.assertEqual(m.completion_rate(1, n_free=2), 1.0)

    def test_decays_above_free(self):
        self.assertAlmostEqual(m.completion_rate(4, n_free=2, retention=0.9), 0.81)

    def test_monotonic_decreasing(self):
        rates = [m.completion_rate(n) for n in range(1, 12)]
        self.assertEqual(rates, sorted(rates, reverse=True))

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            m.completion_rate(-1)


class TestEvaluate(unittest.TestCase):
    def test_cpq_rises_with_units(self):
        c5 = m.evaluate(5).cpq
        c10 = m.evaluate(10).cpq
        self.assertGreater(c10, c5)

    def test_completion_falls_with_units(self):
        self.assertGreater(m.evaluate(3).completion, m.evaluate(10).completion)

    def test_target_cleared_around_six(self):
        self.assertFalse(m.evaluate(5).clears_target)
        self.assertTrue(m.evaluate(6).clears_target)

    def test_revenue_has_interior_peak(self):
        # exponential fatigue eventually beats linear units -> revenue declines
        peak = max(range(1, 40), key=lambda n: m.evaluate(n).daily_rev_per_user)
        self.assertLess(m.evaluate(40).daily_rev_per_user, m.evaluate(peak).daily_rev_per_user)
        self.assertLess(peak, 40)


class TestOptimal(unittest.TestCase):
    def test_structure(self):
        o = m.optimal_units(15)
        self.assertIn("revenue_opt", o)
        self.assertIn("balanced", o)
        self.assertTrue(o["balanced"].clears_target)

    def test_min_target_is_first_clearing(self):
        o = m.optimal_units(15)
        self.assertTrue(o["min_clears_target"].clears_target)
        self.assertFalse(m.evaluate(o["min_clears_target"].n - 1).clears_target)

    def test_balanced_not_beyond_revenue_peak(self):
        o = m.optimal_units(15)
        self.assertLessEqual(o["balanced"].n, o["revenue_opt"].n)


if __name__ == "__main__":
    unittest.main(verbosity=2)
