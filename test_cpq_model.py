"""Unit tests for the CPQ triangulation model.

Run: python -m unittest test_cpq_model -v
"""
import unittest

import cpq_model as m


class TestConversions(unittest.TestCase):
    def test_ecpm_to_cpq(self):
        # $10 eCPM, 1 view/quest => $0.01
        self.assertAlmostEqual(m.cpq_from_ecpm(10.0, 1.0), 0.01)
        # 2 ad units doubles it
        self.assertAlmostEqual(m.cpq_from_ecpm(10.0, 2.0), 0.02)

    def test_cpc_to_cpq(self):
        self.assertAlmostEqual(m.cpq_from_cpc(0.25, 1.0), 0.25)
        self.assertAlmostEqual(m.cpq_from_cpc(0.25, 2.0), 0.50)

    def test_cpa_to_cpq(self):
        self.assertAlmostEqual(m.cpq_from_cpa(1.0, 0.03), 0.03)

    def test_ecpm_required_is_inverse(self):
        cpq = m.cpq_from_ecpm(18.0, 1.5)
        self.assertAlmostEqual(m.ecpm_required_for(cpq, 1.5), 18.0)

    def test_target_needs_30_ecpm_at_one_unit(self):
        # $0.03 target, 1 view/quest => needs $30 eCPM
        self.assertAlmostEqual(m.ecpm_required_for(m.TARGET_CPQ, 1.0), 30.0)


class TestThresholds(unittest.TestCase):
    def test_breakeven_pulled_from_sim(self):
        # base scenario break-even is ~ $0.0082
        self.assertAlmostEqual(m.BREAKEVEN_CPQ, 0.00817, places=4)

    def test_target_is_three_cents(self):
        self.assertAlmostEqual(m.TARGET_CPQ, 0.03)

    def test_breakeven_range_ordered(self):
        lo, hi = m.BREAKEVEN_RANGE
        self.assertLess(lo, m.BREAKEVEN_CPQ)
        self.assertLess(m.BREAKEVEN_CPQ, hi)


class TestVerdicts(unittest.TestCase):
    def test_global_blended_falls_just_short_of_breakeven(self):
        # KEY FINDING: global-blended rewarded eCPM ($8) => CPQ $0.0080, which
        # is just BELOW break-even ($0.0082). At 1 ad unit/quest the model needs
        # better-than-global traffic, a completion premium, or >1 unit per quest.
        v = [x for x in m.triangulate(1.0)
             if x.method == "rewarded_ecpm" and x.scenario == "global_blended"][0]
        self.assertFalse(v.clears_breakeven)
        self.assertLess(v.cpq, m.BREAKEVEN_CPQ)
        self.assertFalse(v.clears_target)

    def test_tier1_premium_clears_target(self):
        v = [x for x in m.triangulate(1.0)
             if x.method == "rewarded_ecpm" and x.scenario == "tier1_premium"][0]
        self.assertTrue(v.clears_target)  # $30 eCPM => $0.03

    def test_triangulate_covers_all_lenses(self):
        methods = {x.method for x in m.triangulate()}
        self.assertEqual(methods, {"rewarded_ecpm", "cpc", "cpa@3%cvr"})

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            m.cpq_from_ecpm(-1, 1)
        with self.assertRaises(ValueError):
            m.cpq_from_cpa(1.0, 1.5)
        with self.assertRaises(ValueError):
            m.ecpm_required_for(0.03, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
