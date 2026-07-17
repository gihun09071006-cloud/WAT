"""Unit tests for the ad mediation / demand-aggregation model.

Run: python -m unittest test_ad_mediation -v
"""
import unittest

import ad_mediation as a


class TestFillRate(unittest.TestCase):
    def test_single_source(self):
        self.assertAlmostEqual(a.combined_fill_rate([0.5]), 0.5)

    def test_two_sources(self):
        # 1 - 0.5*0.5 = 0.75
        self.assertAlmostEqual(a.combined_fill_rate([0.5, 0.5]), 0.75)

    def test_monotonic_and_bounded(self):
        one = a.combined_fill_rate([0.55])
        five = a.combined_fill_rate([0.55] * 5)
        self.assertLess(one, five)
        self.assertLessEqual(five, 1.0)

    def test_empty_is_zero(self):
        self.assertEqual(a.combined_fill_rate([]), 0.0)

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            a.combined_fill_rate([1.2])


class TestEffectiveEcpm(unittest.TestCase):
    def test_more_sources_lift_ecpm(self):
        one = a.effective_ecpm(8.0, 1)
        eight = a.effective_ecpm(8.0, 8)
        self.assertLess(one, eight)

    def test_deterministic_with_seed(self):
        self.assertEqual(a.effective_ecpm(8.0, 4, seed=7), a.effective_ecpm(8.0, 4, seed=7))

    def test_positive(self):
        self.assertGreater(a.effective_ecpm(8.0, 1), 0)

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            a.effective_ecpm(8.0, 0)
        with self.assertRaises(ValueError):
            a.effective_ecpm(-1.0, 3)


class TestCPQMediation(unittest.TestCase):
    def test_single_source_below_breakeven(self):
        cpq1 = a.cpq_under_mediation(8.0, 1, ad_units_per_quest=1.0)
        self.assertLess(cpq1, a.BREAKEVEN_CPQ)

    def test_stacking_clears_breakeven(self):
        cpq_multi = a.cpq_under_mediation(8.0, 4, ad_units_per_quest=1.0)
        self.assertGreaterEqual(cpq_multi, a.BREAKEVEN_CPQ)

    def test_ad_units_scale_cpq(self):
        one_unit = a.cpq_under_mediation(8.0, 6, ad_units_per_quest=1.0)
        two_unit = a.cpq_under_mediation(8.0, 6, ad_units_per_quest=2.0)
        self.assertAlmostEqual(two_unit, 2 * one_unit)

    def test_target_reachable_with_multi_unit(self):
        # target $0.03 reachable by combining many sources + >1 ad unit/quest
        cpq = a.cpq_under_mediation(8.0, 8, ad_units_per_quest=2.0)
        self.assertGreaterEqual(cpq, a.TARGET_CPQ)


class TestCurve(unittest.TestCase):
    def test_curve_length_and_monotonic_cpq(self):
        rows = a.mediation_curve(8.0, max_sources=6)
        self.assertEqual(len(rows), 6)
        cpqs = [r.cpq for r in rows]
        self.assertEqual(cpqs, sorted(cpqs))  # non-decreasing

    def test_curve_flags(self):
        rows = a.mediation_curve(8.0, max_sources=6)
        self.assertFalse(rows[0].clears_breakeven)  # 1 source
        self.assertTrue(rows[-1].clears_breakeven)   # 6 sources


if __name__ == "__main__":
    unittest.main(verbosity=2)
