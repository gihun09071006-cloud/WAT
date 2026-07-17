"""Unit tests for the Redemption Epoch engine (§13 priority 2).

Run: python -m unittest test_redemption_epoch -v
"""
import unittest

from redemption_epoch import EpochResult, settle_epoch


class TestSettleEpoch(unittest.TestCase):
    def test_rate_is_pool_divided_by_spark(self):
        # pool_wat = 100_000 / 0.01 = 10_000_000 WAT
        # rate = 1_900_000_000 Spark / 10_000_000 WAT = 190 Spark/WAT
        r = settle_epoch(pool_usd=100_000, wat_price=0.01, total_spark_redeemed=1_900_000_000)
        self.assertAlmostEqual(r.pool_wat, 10_000_000)
        self.assertAlmostEqual(r.spark_per_wat, 190.0)

    def test_dollar_value_independent_of_wat_price(self):
        """§10: 10x the WAT price -> same dollars to the user, 1/10 the tokens."""
        cheap = settle_epoch(100_000, 0.01, 1_900_000_000)
        dear = settle_epoch(100_000, 0.10, 1_900_000_000)
        self.assertAlmostEqual(cheap.usd_for(1000), dear.usd_for(1000))
        # tokens differ by exactly the price ratio
        self.assertAlmostEqual(dear.wat_for(1000) * 10, cheap.wat_for(1000))

    def test_solvency_never_pays_more_than_pool(self):
        """§ rule 1: sum of every user's WAT equals pool_wat exactly."""
        total_spark = 1_900_000_000
        r = settle_epoch(100_000, 0.01, total_spark)
        # split the whole S across three users
        users = [900_000_000, 700_000_000, 300_000_000]
        self.assertEqual(sum(users), total_spark)
        paid_wat = sum(r.wat_for(u) for u in users)
        self.assertAlmostEqual(paid_wat, r.pool_wat)
        paid_usd = sum(r.usd_for(u) for u in users)
        self.assertAlmostEqual(paid_usd, r.pool_usd)

    def test_more_spark_worsens_rate(self):
        """Monotonicity: a farming wave (more S) => more Spark per WAT."""
        low = settle_epoch(100_000, 0.01, 1_000_000_000)
        high = settle_epoch(100_000, 0.01, 2_000_000_000)
        self.assertLess(low.spark_per_wat, high.spark_per_wat)
        # but the dollar pool is fixed, so per-spark value halves
        self.assertAlmostEqual(low.usd_per_spark, 2 * high.usd_per_spark)

    def test_sink_improves_rate_without_touching_pool(self):
        """§15: burning half the Spark in-game halves S -> halves the rate,
        pool_usd untouched."""
        no_sink = settle_epoch(100_000, 0.01, 2_000_000_000)
        half_sink = settle_epoch(100_000, 0.01, 1_000_000_000)
        self.assertAlmostEqual(half_sink.spark_per_wat, no_sink.spark_per_wat / 2)
        self.assertEqual(half_sink.pool_usd, no_sink.pool_usd)

    def test_zero_pool_is_degenerate_but_valid(self):
        r = settle_epoch(0.0, 0.01, 1_000_000)
        self.assertEqual(r.pool_wat, 0.0)
        self.assertEqual(r.spark_per_wat, 0.0)
        self.assertEqual(r.usd_for(1000), 0.0)

    def test_purity(self):
        args = (100_000, 0.01, 1_900_000_000)
        self.assertEqual(settle_epoch(*args), settle_epoch(*args))
        self.assertIsInstance(settle_epoch(*args), EpochResult)


class TestGuards(unittest.TestCase):
    def test_nonpositive_wat_price_raises(self):
        for bad in (0.0, -0.01):
            with self.assertRaises(ValueError):
                settle_epoch(100_000, bad, 1_000_000)

    def test_no_redemption_raises(self):
        for bad in (0.0, -5):
            with self.assertRaises(ValueError):
                settle_epoch(100_000, 0.01, bad)

    def test_negative_pool_raises(self):
        with self.assertRaises(ValueError):
            settle_epoch(-1.0, 0.01, 1_000_000)

    def test_negative_user_spark_raises(self):
        r = settle_epoch(100_000, 0.01, 1_000_000)
        with self.assertRaises(ValueError):
            r.wat_for(-1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
