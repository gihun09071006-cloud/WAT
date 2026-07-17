"""Unit tests for the ad revenue scenario calculator.

Run: python -m unittest test_ad_revenue_scenarios -v
"""
import unittest

import ad_revenue_scenarios as s


class TestDecay(unittest.TestCase):
    def test_no_decay_at_comfort_freq(self):
        self.assertAlmostEqual(s.effective_ecpm(8.0, 10, comfort_freq=10), 8.0)

    def test_no_decay_below_comfort(self):
        self.assertAlmostEqual(s.effective_ecpm(8.0, 5, comfort_freq=10), 8.0)

    def test_decay_above_comfort(self):
        # (10/50)^0.5 = 0.4472 -> $3.58
        self.assertAlmostEqual(s.effective_ecpm(8.0, 50, comfort_freq=10, gamma=0.5), 8.0 * (0.2 ** 0.5))

    def test_more_views_lower_ecpm(self):
        self.assertGreater(s.effective_ecpm(8.0, 25), s.effective_ecpm(8.0, 50))

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            s.effective_ecpm(8.0, 0)


class TestScenarioRevenue(unittest.TestCase):
    def test_rewarded_only_math(self):
        r = s.scenario_revenue(users=10_000, rewarded_views_per_user=10, rewarded_ecpm=8.0)
        # no decay at 10 views: 10000*10*8/1000 = $800/day
        self.assertAlmostEqual(r.gross_day, 800.0)
        self.assertAlmostEqual(r.gross_month, 24_000.0)
        self.assertAlmostEqual(r.reward_pool_month, 9_600.0)   # 40%
        self.assertEqual(r.offerwall_share, 0.0)

    def test_offerwall_adds_stream(self):
        base = s.scenario_revenue(users=10_000, rewarded_views_per_user=50, rewarded_ecpm=8.0)
        withow = s.scenario_revenue(users=10_000, rewarded_views_per_user=50, rewarded_ecpm=8.0,
                                    offerwall_completion_rate=0.02, offerwall_cpa=2.0)
        self.assertGreater(withow.gross_day, base.gross_day)
        self.assertGreater(withow.offerwall_share, 0)

    def test_offerwall_is_separate_from_views(self):
        # offerwall revenue = users * rate * cpa, independent of views
        r = s.scenario_revenue(users=10_000, rewarded_views_per_user=1, rewarded_ecpm=0.0,
                               offerwall_completion_rate=0.02, offerwall_cpa=2.5)
        self.assertAlmostEqual(r.gross_day, 10_000 * 0.02 * 2.5)  # $500/day

    def test_per_user_pool(self):
        r = s.scenario_revenue(users=10_000, rewarded_views_per_user=10, rewarded_ecpm=8.0)
        self.assertAlmostEqual(r.per_user_pool_month, 9_600.0 / 10_000)

    def test_invalid_completion_rate(self):
        with self.assertRaises(ValueError):
            s.scenario_revenue(users=100, rewarded_views_per_user=10, rewarded_ecpm=8.0,
                               offerwall_completion_rate=1.5)

    def test_all_named_scenarios_run(self):
        for name, kw in s.SCENARIOS.items():
            r = s.scenario_revenue(users=10_000, **kw)
            self.assertGreater(r.gross_month, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
