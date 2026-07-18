"""Unit tests for the sink & shop economy model (§15).

Run: python -m unittest test_sink_shop -v
"""
import math
import unittest

import sink_shop as ss
from sink_shop import ShopItem


class TestShopItem(unittest.TestCase):
    def test_invalid_rarity(self):
        with self.assertRaises(ValueError):
            ShopItem("x", "plane", "Ultra", 100, 0.5)

    def test_invalid_appeal_or_price(self):
        with self.assertRaises(ValueError):
            ShopItem("x", "plane", "Rare", 100, 1.5)
        with self.assertRaises(ValueError):
            ShopItem("x", "plane", "Rare", 0, 0.5)


class TestSpendCurve(unittest.TestCase):
    def test_zero_appeal_zero_spend(self):
        it = ShopItem("x", "pet", "Rare", 500, 0.0)
        self.assertEqual(ss.expected_spend_per_user(it, 2000), 0.0)

    def test_spend_peaks_at_sweet_spot(self):
        # sweet spot price = budget * k
        budget, k = 2000.0, 0.5
        sweet = budget * k
        below = ShopItem("a", "pet", "Rare", sweet * 0.5, 0.6)
        at = ShopItem("b", "pet", "Rare", sweet, 0.6)
        above = ShopItem("c", "pet", "Rare", sweet * 2, 0.6)
        s_below = ss.expected_spend_per_user(below, budget, k)
        s_at = ss.expected_spend_per_user(at, budget, k)
        s_above = ss.expected_spend_per_user(above, budget, k)
        self.assertGreater(s_at, s_below)
        self.assertGreater(s_at, s_above)

    def test_rarity_pull_increases_spend(self):
        budget = 2000
        rare = ShopItem("r", "pet", "Rare", 800, 0.5)
        genesis = ShopItem("g", "pet", "Genesis", 800, 0.5)
        self.assertGreater(ss.expected_spend_per_user(genesis, budget),
                           ss.expected_spend_per_user(rare, budget))


class TestSinkRate(unittest.TestCase):
    def test_richer_catalog_burns_more(self):
        budget = 2000
        sparse = ss.DEFAULT_CATALOG[:2]
        full = ss.DEFAULT_CATALOG
        self.assertGreater(ss.sink_rate(full, budget), ss.sink_rate(sparse, budget))

    def test_bounded(self):
        budget = 2000
        huge = [ShopItem(f"i{i}", "cosmetic", "Genesis", 1000, 1.0) for i in range(50)]
        sr = ss.sink_rate(huge, budget, max_frac=0.9)
        self.assertLessEqual(sr, 0.9)
        self.assertGreaterEqual(sr, 0.0)

    def test_empty_catalog_zero(self):
        self.assertEqual(ss.sink_rate([], 2000), 0.0)


class TestPriceDial(unittest.TestCase):
    def test_scales_prices(self):
        scaled = ss.apply_price_dial(ss.DEFAULT_CATALOG, 2.0)
        for orig, new in zip(ss.DEFAULT_CATALOG, scaled):
            self.assertAlmostEqual(new.price, orig.price * 2.0)

    def test_above_sweet_spot_raising_reduces_burn(self):
        # DEFAULT_CATALOG is priced above the sweet spot, so raising cuts burn
        budget = 2000
        base = ss.sink_rate(ss.DEFAULT_CATALOG, budget)
        raised = ss.sink_rate(ss.apply_price_dial(ss.DEFAULT_CATALOG, 2.0), budget)
        self.assertLess(raised, base)

    def test_invalid_multiplier(self):
        with self.assertRaises(ValueError):
            ss.apply_price_dial(ss.DEFAULT_CATALOG, 0)


class TestEconomyIntegration(unittest.TestCase):
    def test_sink_feeds_simulator_and_dollars_invariant(self):
        from dataclasses import replace
        from economy_simulator import Inputs, simulate
        low = ss.sink_rate(ss.DEFAULT_CATALOG[:2], 2000)
        high = ss.sink_rate(ss.DEFAULT_CATALOG, 2000)
        d_low = simulate(replace(Inputs(), sink_rate=low))
        d_high = simulate(replace(Inputs(), sink_rate=high))
        # more sink -> lower spark_per_wat rate
        self.assertLess(d_high["implied_rate"]["Y1"], d_low["implied_rate"]["Y1"])
        # but user dollars unchanged (§10)
        self.assertAlmostEqual(d_high["user_monthly_usd"]["Y1"], d_low["user_monthly_usd"]["Y1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
