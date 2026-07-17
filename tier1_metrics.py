"""Tier 1 CPQ measurement harness (docs/cpq-validation.md · docs/tier1-prototype.md).

The Tier 1 prototype (a mini plane-shooter + rewarded/offerwall mediation)
exists for ONE reason: turn real play into a real CPQ number. This module
is the scientific backbone — it consumes per-quest telemetry and computes
the metrics that decide go/no-go, feeding the same thresholds as
cpq_model and filtering bots with trust_score so the number is honest.

It deliberately holds no game logic; the game only emits QuestOutcome
records. That separation keeps the measurement auditable and lets us swap
the front-end (mock-ad demo vs live-SDK build) without touching the math.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cpq_model import BREAKEVEN_CPQ, TARGET_CPQ
from trust_score import Signals, Tier, classify, trust_score


@dataclass(frozen=True)
class QuestOutcome:
    """One quest attempt's telemetry, emitted by the prototype."""

    session_id: str
    completed: bool               # boss cleared = quest completed
    parts_scans_requested: int    # "부품 스캔" opportunities offered
    parts_scans_filled: int       # opportunities a demand source actually filled
    ad_revenue_usd: float         # rewarded/offerwall revenue realized this quest
    trust: Signals                # signals for bot filtering (see trust_score)

    def __post_init__(self) -> None:
        if self.parts_scans_filled > self.parts_scans_requested:
            raise ValueError("filled는 requested를 초과할 수 없다")
        if self.parts_scans_requested < 0 or self.ad_revenue_usd < 0:
            raise ValueError("음수 입력 불가")


class Verdict(str, Enum):
    BROKEN = "broken"      # honest CPQ < break-even -> redesign / pivot
    GAME = "game"          # break-even <= CPQ < target -> "용돈이 아니라 게임"
    BUSINESS = "business"  # CPQ >= target -> monetization is a business


def _is_bot(o: QuestOutcome) -> bool:
    return classify(trust_score(o.trust)) in (Tier.RESTRICTED, Tier.BLOCKED)


@dataclass(frozen=True)
class Tier1Report:
    n_quests: int
    completion_rate: float          # completed / attempted
    fill_rate: float                # scans filled / scans requested
    gross_cpq: float                # revenue / all completions (bot-inflated)
    honest_cpq: float               # revenue / human completions (the real number)
    bot_completion_rate: float      # share of completions that were bots
    verdict: Verdict

    @property
    def clears_breakeven(self) -> bool:
        return self.honest_cpq >= BREAKEVEN_CPQ

    @property
    def clears_target(self) -> bool:
        return self.honest_cpq >= TARGET_CPQ


def _verdict_for(cpq: float) -> Verdict:
    if cpq < BREAKEVEN_CPQ:
        return Verdict.BROKEN
    if cpq < TARGET_CPQ:
        return Verdict.GAME
    return Verdict.BUSINESS


def analyze(outcomes: list[QuestOutcome]) -> Tier1Report:
    """Aggregate prototype telemetry into the Tier 1 decision report.

    honest_cpq — the number that matters — is advertiser revenue per genuine
    HUMAN completion (bot completions filtered via trust_score). Compared to
    the same break-even/target as the rest of the model.
    """
    if not outcomes:
        return Tier1Report(0, 0.0, 0.0, 0.0, 0.0, 0.0, Verdict.BROKEN)

    n = len(outcomes)
    completed = [o for o in outcomes if o.completed]
    scans_req = sum(o.parts_scans_requested for o in outcomes)
    scans_fill = sum(o.parts_scans_filled for o in outcomes)

    all_completions = len(completed)
    bot_completions = [o for o in completed if _is_bot(o)]
    human_completions = [o for o in completed if not _is_bot(o)]

    gross_rev = sum(o.ad_revenue_usd for o in completed)
    human_rev = sum(o.ad_revenue_usd for o in human_completions)

    gross_cpq = gross_rev / all_completions if all_completions else 0.0
    honest_cpq = human_rev / len(human_completions) if human_completions else 0.0

    return Tier1Report(
        n_quests=n,
        completion_rate=all_completions / n,
        fill_rate=scans_fill / scans_req if scans_req else 0.0,
        gross_cpq=gross_cpq,
        honest_cpq=honest_cpq,
        bot_completion_rate=len(bot_completions) / all_completions if all_completions else 0.0,
        verdict=_verdict_for(honest_cpq),
    )


if __name__ == "__main__":
    # Synthetic cohort: mostly humans, a few bot farms.
    human = Signals(0.85, 0.9, 0.8, 0.7, 0.9, 0.8)
    bot = Signals(0.1, 0.05, 0.1, 0.1, 0.1, 0.1, device_account_count=40)
    outcomes = []
    for i in range(90):
        outcomes.append(QuestOutcome(f"h{i}", completed=i % 5 != 0,  # 80% completion
                                     parts_scans_requested=10, parts_scans_filled=9,
                                     ad_revenue_usd=0.011, trust=human))
    for i in range(10):
        outcomes.append(QuestOutcome(f"b{i}", completed=True,
                                     parts_scans_requested=10, parts_scans_filled=10,
                                     ad_revenue_usd=0.011, trust=bot))
    r = analyze(outcomes)
    print(f"퀘스트 {r.n_quests} · 완료율 {r.completion_rate:.0%} · fill {r.fill_rate:.0%}")
    print(f"gross CPQ ${r.gross_cpq:.4f}  vs  honest CPQ ${r.honest_cpq:.4f}  "
          f"(봇 완료 {r.bot_completion_rate:.0%} 제외)")
    print(f"손익분기 ${BREAKEVEN_CPQ:.4f} / 목표 ${TARGET_CPQ:.4f} → 판정: {r.verdict.value.upper()}")
