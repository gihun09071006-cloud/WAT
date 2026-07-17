"""Ad demand aggregation / mediation model (§1 thesis · CPQ mechanism).

QuestFi is demand-source-agnostic. CPQ (revenue per verified quest
completion) is an ABSTRACTION over every ad source that pays — rewarded
video (CPCV), offerwall (CPA/CPI), programmatic (CPM), CPC networks,
and direct CPQ deals. Each source pays in its native unit; the mediation
layer normalizes all of it to "revenue per quest" and passes one reward
through.

Aggregating ALL sources is not a preference — it's how the economics
clear. `cpq_model.py` showed a single global-blended source sits right at
break-even. Stacking sources lifts CPQ two ways this module quantifies:

  1. FILL RATE  — 1 - Π(1 - f_i): more sources, more opportunities filled
     (this is the §8 fill_rate lever, Y1 40% -> Y3 85%).
  2. eCPM       — sources bid competitively; the winning bid rises with the
     number of bidders (why real mediation / header bidding exists).

Thresholds (break-even, target) are imported from cpq_model so there is a
single source of truth.

⚠️ Compliance note baked into the design (see docs/ad-mediation.md):
   Rewarding a user for *clicking* standard-network ads violates many ad
   policies (Google/AdMob invalid traffic) and risks bans. Rewarded VIDEO
   (reward for watching) and OFFERWALL (reward for an action) are the
   incentive-friendly primitives. So "부품 스캔" leans on view/action
   sources, not incentivized clicks on CPC networks.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cpq_model import BREAKEVEN_CPQ, TARGET_CPQ, cpq_from_ecpm


def combined_fill_rate(fill_rates: list[float]) -> float:
    """Probability at least one source fills = 1 - Π(1 - f_i)."""
    p_none = 1.0
    for f in fill_rates:
        if not 0.0 <= f <= 1.0:
            raise ValueError("fill_rate는 [0,1] 범위여야 한다")
        p_none *= 1.0 - f
    return 1.0 - p_none


def effective_ecpm(
    base_ecpm: float,
    n_sources: int,
    per_source_fill: float = 0.55,
    dispersion: float = 0.6,
    trials: int = 40_000,
    seed: int = 0,
) -> float:
    """Expected winning eCPM per impression opportunity under a first-price
    auction across `n_sources` competing demand sources.

    Each source independently fills with `per_source_fill` and, if it fills,
    bids ~ lognormal(median = base_ecpm, sigma = dispersion). The auction
    takes the max bid (0 if none fill). More bidders -> higher expected max
    (order statistics) -> higher realized eCPM.

    `base_ecpm` is the per-source MEDIAN bid. Deterministic given `seed`.
    """
    if n_sources < 1:
        raise ValueError("n_sources는 1 이상")
    if base_ecpm < 0 or not 0.0 <= per_source_fill <= 1.0 or dispersion < 0:
        raise ValueError("입력 범위 오류")
    rng = np.random.default_rng(seed)
    fills = rng.random((trials, n_sources)) < per_source_fill
    bids = rng.lognormal(mean=np.log(base_ecpm), sigma=dispersion, size=(trials, n_sources))
    bids = np.where(fills, bids, 0.0)
    winning = bids.max(axis=1)
    return float(winning.mean())


def cpq_under_mediation(
    base_ecpm: float,
    n_sources: int,
    ad_units_per_quest: float = 1.0,
    **kw,
) -> float:
    """CPQ delivered when a quest monetizes `ad_units_per_quest` opportunities,
    each auctioned across `n_sources` sources."""
    return cpq_from_ecpm(effective_ecpm(base_ecpm, n_sources, **kw), ad_units_per_quest)


@dataclass(frozen=True)
class MediationRow:
    n_sources: int
    fill_rate: float
    effective_ecpm: float
    cpq: float
    clears_breakeven: bool
    clears_target: bool


def mediation_curve(
    base_ecpm: float,
    max_sources: int,
    per_source_fill: float = 0.55,
    ad_units_per_quest: float = 1.0,
    **kw,
) -> list[MediationRow]:
    """CPQ / fill / eCPM as the number of stacked demand sources grows 1..N."""
    rows = []
    for n in range(1, max_sources + 1):
        e = effective_ecpm(base_ecpm, n, per_source_fill=per_source_fill, **kw)
        cpq = cpq_from_ecpm(e, ad_units_per_quest)
        rows.append(
            MediationRow(
                n_sources=n,
                fill_rate=combined_fill_rate([per_source_fill] * n),
                effective_ecpm=e,
                cpq=cpq,
                clears_breakeven=cpq >= BREAKEVEN_CPQ,
                clears_target=cpq >= TARGET_CPQ,
            )
        )
    return rows


def _flag(b: bool) -> str:
    return "✓" if b else "·"


if __name__ == "__main__":
    # Start from the borderline case: global-blended per-source median eCPM $8.
    print("QuestFi — 광고 미디에이션: 소스를 쌓으면 CPQ가 손익분기를 넘는다")
    print(f"  per-source median eCPM=$8 · fill=55% · 손익분기=${BREAKEVEN_CPQ:.4f} · 목표=${TARGET_CPQ:.4f}\n")
    print(f"{'소스수':>5}{'fill률':>9}{'유효 eCPM':>12}{'CPQ':>10}{'손익분기':>9}{'목표':>6}")
    print("-" * 54)
    for r in mediation_curve(base_ecpm=8.0, max_sources=10):
        print(f"{r.n_sources:>5}{r.fill_rate:>8.0%}${r.effective_ecpm:>10.2f}"
              f"${r.cpq:>8.4f}{_flag(r.clears_breakeven):>8}{_flag(r.clears_target):>6}")
    print("\n판정: 단일 소스는 손익분기 근처, 소스를 다 싸잡으면 fill·eCPM이 함께 올라 목표에 근접.")
