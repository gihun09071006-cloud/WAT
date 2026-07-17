"""Unit tests for the Tier 1 measurement harness.

Run: python -m unittest test_tier1_metrics -v
"""
import unittest

from tier1_metrics import QuestOutcome, Tier1Report, Verdict, analyze
from trust_score import Signals

HUMAN = Signals(0.85, 0.9, 0.8, 0.7, 0.9, 0.8)
BOT = Signals(0.1, 0.05, 0.1, 0.1, 0.1, 0.1, device_account_count=40)


def q(completed=True, req=10, fill=9, rev=0.011, trust=HUMAN, sid="s"):
    return QuestOutcome(sid, completed, req, fill, rev, trust)


class TestOutcomeGuards(unittest.TestCase):
    def test_fill_over_requested_raises(self):
        with self.assertRaises(ValueError):
            q(req=5, fill=6)

    def test_negative_revenue_raises(self):
        with self.assertRaises(ValueError):
            q(rev=-0.01)


class TestAnalyze(unittest.TestCase):
    def test_empty_is_broken(self):
        r = analyze([])
        self.assertEqual(r.verdict, Verdict.BROKEN)
        self.assertEqual(r.n_quests, 0)

    def test_completion_and_fill_rates(self):
        outs = [q(completed=True), q(completed=False), q(completed=True), q(completed=True)]
        r = analyze(outs)
        self.assertAlmostEqual(r.completion_rate, 0.75)
        self.assertAlmostEqual(r.fill_rate, 0.9)  # 9/10 each

    def test_honest_cpq_excludes_bots(self):
        # 1 human completion @ $0.02, 1 bot completion @ $0.02
        outs = [q(rev=0.02, trust=HUMAN, sid="h"), q(rev=0.02, trust=BOT, sid="b")]
        r = analyze(outs)
        self.assertAlmostEqual(r.gross_cpq, 0.02)     # both counted
        self.assertAlmostEqual(r.honest_cpq, 0.02)    # per-human still 0.02
        self.assertAlmostEqual(r.bot_completion_rate, 0.5)

    def test_bot_inflation_detected(self):
        # bots complete cheaply and would drag the honest number if not filtered
        outs = [q(rev=0.03, trust=HUMAN, sid="h")]
        outs += [q(rev=0.001, trust=BOT, sid=f"b{i}") for i in range(9)]
        r = analyze(outs)
        # gross is dragged down by cheap bot completions; honest is the human value
        self.assertLess(r.gross_cpq, r.honest_cpq)
        self.assertAlmostEqual(r.honest_cpq, 0.03)

    def test_verdict_broken(self):
        r = analyze([q(rev=0.004) for _ in range(10)])  # below break-even
        self.assertEqual(r.verdict, Verdict.BROKEN)
        self.assertFalse(r.clears_breakeven)

    def test_verdict_game(self):
        r = analyze([q(rev=0.015) for _ in range(10)])  # between break-even and target
        self.assertEqual(r.verdict, Verdict.GAME)
        self.assertTrue(r.clears_breakeven)
        self.assertFalse(r.clears_target)

    def test_verdict_business(self):
        r = analyze([q(rev=0.05) for _ in range(10)])  # above target
        self.assertEqual(r.verdict, Verdict.BUSINESS)
        self.assertTrue(r.clears_target)

    def test_report_type(self):
        self.assertIsInstance(analyze([q()]), Tier1Report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
