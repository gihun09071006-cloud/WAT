"""Unit tests for the DEX liquidity engine (§10 + §15).

Run: python -m unittest test_dex_lp -v
"""
import math
import unittest

from dex_lp import (
    Pool,
    add_liquidity_price_neutral,
    impermanent_loss,
    simulate_lp_growth,
    swap_wat_for_usdc,
)


class TestPool(unittest.TestCase):
    def test_spot_price_and_tvl(self):
        p = Pool(reserve_wat=1_000_000, reserve_usdc=10_000)  # $0.01/WAT
        self.assertAlmostEqual(p.spot_price, 0.01)
        self.assertAlmostEqual(p.tvl_usdc, 20_000)

    def test_invalid_reserves_raise(self):
        for w, u in ((0, 100), (100, 0), (-1, 100)):
            with self.assertRaises(ValueError):
                Pool(reserve_wat=w, reserve_usdc=u)


class TestSwap(unittest.TestCase):
    def test_constant_product_holds_after_fee_free_swap(self):
        p = Pool(reserve_wat=1_000_000, reserve_usdc=10_000, fee=0.0)
        s = swap_wat_for_usdc(p, 1000)
        # with zero fee, k is preserved exactly
        self.assertAlmostEqual(s.pool_after.k, p.k, places=2)

    def test_selling_pushes_price_down(self):
        p = Pool(reserve_wat=1_000_000, reserve_usdc=10_000)
        s = swap_wat_for_usdc(p, 50_000)
        self.assertLess(s.price_after, p.spot_price)

    def test_slippage_positive_and_grows_with_size(self):
        p = Pool(reserve_wat=1_000_000, reserve_usdc=10_000)
        small = swap_wat_for_usdc(p, 1_000)
        large = swap_wat_for_usdc(p, 100_000)
        self.assertGreater(small.slippage, 0)
        self.assertGreater(large.slippage, small.slippage)

    def test_deeper_pool_less_slippage(self):
        shallow = Pool(reserve_wat=1_000_000, reserve_usdc=10_000)
        deep = Pool(reserve_wat=10_000_000, reserve_usdc=100_000)  # same price, 10x depth
        wat_in = 50_000
        s_shallow = swap_wat_for_usdc(shallow, wat_in)
        s_deep = swap_wat_for_usdc(deep, wat_in)
        self.assertLess(s_deep.slippage, s_shallow.slippage)

    def test_usdc_out_never_exceeds_reserve(self):
        p = Pool(reserve_wat=1_000_000, reserve_usdc=10_000)
        s = swap_wat_for_usdc(p, 10_000_000)  # huge sell
        self.assertLess(s.usdc_out, p.reserve_usdc)
        self.assertGreater(s.pool_after.reserve_usdc, 0)

    def test_invalid_swap_raises(self):
        p = Pool(reserve_wat=1_000_000, reserve_usdc=10_000)
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                swap_wat_for_usdc(p, bad)


class TestAddLiquidity(unittest.TestCase):
    def test_price_neutral_add_keeps_price(self):
        p = Pool(reserve_wat=1_000_000, reserve_usdc=10_000)
        new_pool, wat_used = add_liquidity_price_neutral(p, 5_000)
        self.assertAlmostEqual(new_pool.spot_price, p.spot_price)
        # 5000 USDC at $0.01 needs 500,000 WAT
        self.assertAlmostEqual(wat_used, 500_000)
        self.assertGreater(new_pool.tvl_usdc, p.tvl_usdc)

    def test_invalid_add_raises(self):
        p = Pool(reserve_wat=1_000_000, reserve_usdc=10_000)
        with self.assertRaises(ValueError):
            add_liquidity_price_neutral(p, 0)


class TestImpermanentLoss(unittest.TestCase):
    def test_no_move_no_loss(self):
        self.assertAlmostEqual(impermanent_loss(1.0), 0.0)

    def test_known_values(self):
        # classic reference points
        self.assertAlmostEqual(impermanent_loss(2.0), -0.0572, places=4)
        self.assertAlmostEqual(impermanent_loss(4.0), -0.2000, places=4)

    def test_symmetric_in_ratio(self):
        # a 2x up and a 2x down give the same IL
        self.assertAlmostEqual(impermanent_loss(2.0), impermanent_loss(0.5))

    def test_always_nonpositive(self):
        for pr in (0.1, 0.5, 1.0, 2.0, 10.0):
            self.assertLessEqual(impermanent_loss(pr), 1e-12)

    def test_invalid_ratio_raises(self):
        with self.assertRaises(ValueError):
            impermanent_loss(0)


class TestSimulation(unittest.TestCase):
    def test_depth_grows_and_slippage_shrinks(self):
        """The core IR claim: revenue compounds into depth, slippage falls."""
        states = simulate_lp_growth(
            months=12,
            initial_wat=5_000_000,
            initial_usdc=50_000,
            monthly_usdc_injection=35_000,
            monthly_redeemed_wat=1_000_000,
            injection_growth=0.05,
        )
        self.assertEqual(len(states), 12)
        self.assertGreater(states[-1].tvl_usdc, states[0].tvl_usdc)
        self.assertLess(states[-1].redemption_slippage, states[0].redemption_slippage)
        self.assertGreater(states[-1].treasury_wat_used, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
