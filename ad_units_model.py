"""Ad units per quest optimization (A4).

How many "부품 스캔" (ad units) should one quest ask for? More units raise
CPQ (revenue per completed quest), but they also:
  - trigger frequency decay (per ad_revenue_scenarios) -> lower eCPM/unit, and
  - fatigue players -> lower quest completion -> fewer completed quests.

So daily revenue per user is a trade-off with an interior optimum, while CPQ
itself keeps rising with N. This module finds both: the CPQ-clearing minimum
and the UX-aware revenue optimum.

Ties to the founder's original design ("10 scans -> stage upgrade").
"""
from __future__ import annotations

from dataclasses import dataclass

from ad_revenue_scenarios import effective_ecpm
from cpq_model import BREAKEVEN_CPQ, TARGET_CPQ


def completion_rate(n: int, n_free: int = 2, retention: float = 0.93) -> float:
    """Quest completion probability vs number of scans. Users tolerate `n_free`
    freely; each extra scan multiplies completion by `retention` (fatigue)."""
    if n < 0:
        raise ValueError("n은 음수 불가")
    return retention ** max(0, n - n_free)


@dataclass(frozen=True)
class UnitPoint:
    n: int
    completion: float
    eff_ecpm: float
    cpq: float
    daily_rev_per_user: float
    monthly_pool_per_user: float
    clears_breakeven: bool
    clears_target: bool


def evaluate(
    n: int,
    *,
    base_ecpm: float = 12.0,
    quests_attempted: float = 10.0,
    offerwall_per_quest: float = 0.0,
    reward_share: float = 0.40,
    n_free: int = 2,
    retention: float = 0.93,
) -> UnitPoint:
    comp = completion_rate(n, n_free, retention)
    completed = quests_attempted * comp
    daily_views = max(1e-9, completed * n)
    eff = effective_ecpm(base_ecpm, daily_views)
    cpq = n * eff / 1000.0 + offerwall_per_quest
    daily_rev = completed * cpq
    monthly_pool = daily_rev * 30 * reward_share
    return UnitPoint(
        n=n, completion=comp, eff_ecpm=eff, cpq=cpq,
        daily_rev_per_user=daily_rev, monthly_pool_per_user=monthly_pool,
        clears_breakeven=cpq >= BREAKEVEN_CPQ, clears_target=cpq >= TARGET_CPQ,
    )


def curve(max_n: int = 15, **kw) -> list[UnitPoint]:
    return [evaluate(n, **kw) for n in range(1, max_n + 1)]


def optimal_units(max_n: int = 15, **kw) -> dict:
    """Return the revenue-maximising N, the min N clearing target, and a
    balanced recommendation (clears target, near/under the revenue peak)."""
    pts = curve(max_n, **kw)
    rev_opt = max(pts, key=lambda p: p.daily_rev_per_user)
    target_hits = [p for p in pts if p.clears_target]
    min_target = target_hits[0] if target_hits else None
    # balanced: clears target if possible, capped at the revenue optimum
    if min_target and min_target.n <= rev_opt.n:
        balanced = min_target
    elif target_hits:
        balanced = rev_opt if rev_opt.clears_target else target_hits[0]
    else:
        balanced = rev_opt  # target unreachable -> maximize revenue
    return {"revenue_opt": rev_opt, "min_clears_target": min_target, "balanced": balanced}


def _f(b): return "✓" if b else "·"


if __name__ == "__main__":
    print("A4 — 퀘스트당 부품 스캔(광고 유닛) 최적화")
    print("기준: base eCPM $12(미디에이션) · 하루 10 퀘스트 시도 · 완료 피로도 retention 0.93\n")
    print(f"{'유닛N':>5}{'완료율':>8}{'유효eCPM':>10}{'CPQ':>10}{'일매출/인':>11}{'월풀/인':>9}{'손익':>6}{'목표':>5}")
    print("-" * 66)
    for p in curve(15):
        mark = "  ← 10회(원안)" if p.n == 10 else ""
        print(f"{p.n:>5}{p.completion:>7.0%}${p.eff_ecpm:>8.2f}${p.cpq:>8.4f}"
              f"${p.daily_rev_per_user:>9.4f}${p.monthly_pool_per_user:>7.2f}"
              f"{_f(p.clears_breakeven):>5}{_f(p.clears_target):>5}{mark}")

    o = optimal_units(15)
    print("\n판정:")
    print(f"  · 매출 최적 N = {o['revenue_opt'].n}  (일매출/인 ${o['revenue_opt'].daily_rev_per_user:.4f})")
    mt = o['min_clears_target']
    print(f"  · 목표 CPQ 달성 최소 N = {mt.n if mt else '없음(도달 불가)'}")
    b = o['balanced']
    print(f"  · 권고(균형) N = {b.n}  → CPQ ${b.cpq:.4f} · 완료율 {b.completion:.0%} · 월풀/인 ${b.monthly_pool_per_user:.2f}")
    print("\n※ CPQ만 보면 N↑ 유리하지만, 완료율·빈도감쇠 때문에 일매출은 중간에서 꺾인다.")
