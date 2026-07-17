"""Unit tests for the anti-bot Trust Score (§4/§11/§15).

Run: python -m unittest test_trust_score -v
"""
import unittest

import trust_score as t
from trust_score import Action, Signals, Tier


def human(**over):
    base = dict(behavioral_humanity=0.85, device_integrity=0.9, network_reputation=0.8,
                account_maturity=0.7, graph_independence=0.9, ad_interaction_quality=0.8)
    base.update(over)
    return Signals(**base)


class TestScore(unittest.TestCase):
    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(t.WEIGHTS.values()), 1.0)

    def test_perfect_human_is_trusted(self):
        s = human()
        self.assertGreaterEqual(t.trust_score(s), t.TRUSTED_MIN)
        self.assertIs(t.classify(t.trust_score(s)), Tier.TRUSTED)

    def test_all_zero_is_blocked(self):
        s = Signals(0, 0, 0, 0, 0, 0)
        self.assertEqual(t.trust_score(s), 0.0)
        self.assertIs(t.classify(0.0), Tier.BLOCKED)

    def test_score_bounded(self):
        s = human()
        sc = t.trust_score(s)
        self.assertGreaterEqual(sc, 0.0)
        self.assertLessEqual(sc, 1.0)

    def test_device_farm_crushes_score(self):
        clean = human()
        farm = human(device_account_count=40)
        self.assertLess(t.trust_score(farm), t.trust_score(clean))
        # a strong-signal account gets pushed out of trusted by the farm flag
        self.assertLess(t.trust_score(farm), t.TRUSTED_MIN)

    def test_geo_velocity_caps_score(self):
        s = human(geo_velocity_violation=True)
        self.assertLessEqual(t.trust_score(s), t.GEO_VELOCITY_SCORE_CAP)

    def test_invalid_signal_raises(self):
        with self.assertRaises(ValueError):
            human(device_integrity=1.5)
        with self.assertRaises(ValueError):
            human(device_account_count=0)


class TestRedemptionGate(unittest.TestCase):
    def test_trusted_full_approval(self):
        d = t.redemption_decision(0.9, 8.0)
        self.assertIs(d.action, Action.ALLOW)
        self.assertEqual(d.approved_usd, 8.0)
        self.assertFalse(d.step_up_required)

    def test_provisional_within_cap(self):
        d = t.redemption_decision(0.6, 3.0)
        self.assertIs(d.action, Action.ALLOW_CAPPED)
        self.assertEqual(d.approved_usd, 3.0)

    def test_provisional_over_cap_triggers_stepup(self):
        d = t.redemption_decision(0.6, 20.0)
        self.assertIs(d.action, Action.STEP_UP_REQUIRED)
        self.assertTrue(d.step_up_required)
        self.assertEqual(d.approved_usd, t.PROVISIONAL_EPOCH_CAP_USD)

    def test_restricted_can_earn_not_redeem(self):
        d = t.redemption_decision(0.3, 1.0)
        self.assertIs(d.action, Action.RESTRICT)
        self.assertEqual(d.approved_usd, 0.0)
        self.assertTrue(d.step_up_required)  # appeal path exists

    def test_blocked_gets_nothing(self):
        d = t.redemption_decision(0.1, 1.0)
        self.assertIs(d.action, Action.BLOCK)
        self.assertEqual(d.approved_usd, 0.0)
        self.assertFalse(d.step_up_required)  # confirmed bot, no appeal here

    def test_negative_amount_raises(self):
        with self.assertRaises(ValueError):
            t.redemption_decision(0.9, -1.0)


class TestPoolIntegrity(unittest.TestCase):
    def test_bot_spark_excluded_from_S(self):
        bot = Signals(0.1, 0.05, 0.1, 0.1, 0.1, 0.1, device_account_count=50)
        rpt = t.pool_integrity([(1000, human()), (99000, bot)])
        # honest S is only the human's spark; the bot's 99k is filtered out
        self.assertEqual(rpt.redeemable_spark, 1000)
        self.assertEqual(rpt.filtered_spark, 99000)
        self.assertGreater(rpt.filtered_rate, 0.98)
        self.assertEqual(rpt.blocked_accounts, 1)

    def test_totals_add_up(self):
        rpt = t.pool_integrity([(500, human()), (300, human()),
                                (200, Signals(0, 0, 0, 0, 0, 0))])
        self.assertEqual(rpt.total_spark, 1000)
        self.assertAlmostEqual(rpt.redeemable_spark + rpt.filtered_spark, rpt.total_spark)

    def test_empty_pool(self):
        rpt = t.pool_integrity([])
        self.assertEqual(rpt.total_spark, 0)
        self.assertEqual(rpt.filtered_rate, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
