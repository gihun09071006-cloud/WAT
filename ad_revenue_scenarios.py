"""Ad revenue scenario calculator (extends cpq_model / ad_mediation).

Answers "10,000명이 하루 N회 광고를 보면 기대 매출은?" honestly — modeling the
things a flat eCPM x views misses:

  1. FREQUENCY DECAY  — rewarded eCPM falls as daily impressions/user rise
     (the 40th ad is worth far less than the 1st).
  2. OFFERWALL as a SEPARATE stream — not per-view; a fraction of users
     complete an action/day worth a CPA (the high-value lever, per research:
     offerwall ARPDAU is 3-8x rewarded-only).
  3. REWARD SPLIT     — gross ad revenue x reward_share (40%) is the pool.

All quantities are transparent and tunable.
"""
from __future__ import annotations

from dataclasses import dataclass


def effective_ecpm(base_ecpm: float, views_per_user: float,
                   comfort_freq: float = 10.0, gamma: float = 0.5) -> float:
    """Average rewarded eCPM once a user is served `views_per_user`/day.

    At/below comfort_freq there's no decay; above it the average eCPM decays
    as (comfort_freq / views)^gamma. gamma=0.5 roughly halves eCPM at 5x the
    comfortable frequency.
    """
    if base_ecpm < 0 or views_per_user <= 0 or comfort_freq <= 0 or gamma < 0:
        raise ValueError("입력 범위 오류")
    decay = min(1.0, (comfort_freq / views_per_user) ** gamma)
    return base_ecpm * decay


@dataclass(frozen=True)
class RevenueResult:
    gross_day: float
    gross_month: float
    gross_year: float
    reward_pool_month: float
    per_user_pool_month: float
    rewarded_share: float       # fraction of gross from rewarded video
    offerwall_share: float      # fraction of gross from offerwall
    eff_ecpm: float


def scenario_revenue(
    *,
    users: int,
    rewarded_views_per_user: float,
    rewarded_ecpm: float,
    offerwall_completion_rate: float = 0.0,  # share of users completing an offer/day
    offerwall_cpa: float = 0.0,              # publisher net $ per completed action
    reward_share: float = 0.40,
    comfort_freq: float = 10.0,
    gamma: float = 0.5,
) -> RevenueResult:
    """Daily/monthly/yearly gross ad revenue and the QuestFi reward pool."""
    if users < 0 or not 0 <= offerwall_completion_rate <= 1:
        raise ValueError("입력 범위 오류")
    eff = effective_ecpm(rewarded_ecpm, rewarded_views_per_user, comfort_freq, gamma)
    rewarded_day = users * rewarded_views_per_user * eff / 1000.0
    offerwall_day = users * offerwall_completion_rate * offerwall_cpa
    gross_day = rewarded_day + offerwall_day
    gross_month = gross_day * 30
    return RevenueResult(
        gross_day=gross_day,
        gross_month=gross_month,
        gross_year=gross_day * 365,
        reward_pool_month=gross_month * reward_share,
        per_user_pool_month=(gross_month * reward_share / users) if users else 0.0,
        rewarded_share=rewarded_day / gross_day if gross_day else 0.0,
        offerwall_share=offerwall_day / gross_day if gross_day else 0.0,
        eff_ecpm=eff,
    )


# named scenarios at the asked-for 10,000 users x 50 views/day
SCENARIOS = {
    "농사 함정 (전부 시청)": dict(rewarded_views_per_user=50, rewarded_ecpm=8.0,
                                offerwall_completion_rate=0.0, offerwall_cpa=0.0, gamma=0.7),
    "글로벌 혼합 (+소량 오퍼월)": dict(rewarded_views_per_user=50, rewarded_ecpm=8.0,
                                offerwall_completion_rate=0.015, offerwall_cpa=2.0),
    "미디에이션 + 오퍼월": dict(rewarded_views_per_user=50, rewarded_ecpm=12.0,
                                offerwall_completion_rate=0.025, offerwall_cpa=2.5),
    "Tier-1 + 오퍼월": dict(rewarded_views_per_user=50, rewarded_ecpm=18.0,
                                offerwall_completion_rate=0.03, offerwall_cpa=3.0),
}


if __name__ == "__main__":
    USERS = 10_000
    print(f"기준: {USERS:,}명 · 하루 50회 rewarded 시청 (+ 오퍼월은 별도 스트림)\n")
    print(f"{'시나리오':<24}{'유효eCPM':>9}{'매출/월':>12}{'보상풀/월':>12}{'1인/월':>9}{'오퍼월비중':>10}")
    print("-" * 78)
    for name, kw in SCENARIOS.items():
        r = scenario_revenue(users=USERS, **kw)
        print(f"{name:<24}${r.eff_ecpm:>7.2f}${r.gross_month:>10,.0f}"
              f"${r.reward_pool_month:>10,.0f}${r.per_user_pool_month:>7.2f}{r.offerwall_share:>10.0%}")

    print("\n[빈도 민감도] 글로벌 $8·오퍼월 1.5%×$2, 하루 시청 횟수만 바꾸면:")
    for v in (10, 25, 50, 80):
        r = scenario_revenue(users=USERS, rewarded_views_per_user=v, rewarded_ecpm=8.0,
                             offerwall_completion_rate=0.015, offerwall_cpa=2.0)
        print(f"  {v:>3}회/일 → 유효eCPM ${r.eff_ecpm:>5.2f} · 매출/월 ${r.gross_month:>9,.0f} · 보상풀 ${r.reward_pool_month:>8,.0f}")
    print("\n※ 시청 횟수를 늘려도 유효 eCPM이 깎여 매출은 선형으로 안 오른다.")
    print("  진짜 레버 = eCPM 티어(트래픽 질) + 오퍼월 비중, 횟수 강요가 아님.")
