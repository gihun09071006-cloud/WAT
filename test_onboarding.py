"""Unit tests for wallet-abstraction onboarding logic (C5).

Run: python -m unittest test_onboarding -v
"""
import unittest

from onboarding import KYC_THRESHOLD_USD, Stage, onboarding_decision


class TestOnboarding(unittest.TestCase):
    def test_browsing_no_wallet(self):
        s = onboarding_decision(has_account=False, is_redeeming=False)
        self.assertIs(s.stage, Stage.BROWSING)
        self.assertFalse(s.needs_wallet)
        self.assertEqual(s.wallet_mode, "none")

    def test_playing_needs_no_wallet(self):
        # §12: play & spend off-chain Spark without any wallet
        s = onboarding_decision(has_account=True, is_redeeming=False)
        self.assertIs(s.stage, Stage.PLAYING)
        self.assertFalse(s.needs_wallet)
        self.assertFalse(s.kyc_required)

    def test_first_small_redemption_embedded_sponsored_no_kyc(self):
        s = onboarding_decision(has_account=True, is_redeeming=True, redemption_value_usd=3.0)
        self.assertIs(s.stage, Stage.REDEEMING)
        self.assertTrue(s.needs_wallet)
        self.assertEqual(s.wallet_mode, "embedded")
        self.assertTrue(s.gas_sponsored)
        self.assertFalse(s.kyc_required)

    def test_large_redemption_triggers_kyc(self):
        s = onboarding_decision(has_account=True, is_redeeming=True,
                                redemption_value_usd=KYC_THRESHOLD_USD + 1)
        self.assertTrue(s.kyc_required)

    def test_threshold_boundary(self):
        below = onboarding_decision(has_account=True, is_redeeming=True,
                                    redemption_value_usd=KYC_THRESHOLD_USD - 0.01)
        at = onboarding_decision(has_account=True, is_redeeming=True,
                                 redemption_value_usd=KYC_THRESHOLD_USD)
        self.assertFalse(below.kyc_required)
        self.assertTrue(at.kyc_required)  # >= threshold

    def test_export_self_custody_unsponsored(self):
        s = onboarding_decision(has_account=True, is_redeeming=False, wants_export=True)
        self.assertIs(s.stage, Stage.SELF_CUSTODY)
        self.assertEqual(s.wallet_mode, "self_custody")
        self.assertFalse(s.gas_sponsored)

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            onboarding_decision(has_account=True, is_redeeming=True, redemption_value_usd=-1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
