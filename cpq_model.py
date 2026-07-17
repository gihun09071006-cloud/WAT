"""CPQ triangulation model (§9 + §13 "다음 관문" of CLAUDE.md).

CPQ (Cost Per Quest — what an advertiser pays for one verified quest
completion) is the single unverified variable the whole economy hangs on.
Advertisers don't quote a "CPQ" directly, so we triangulate it from the
ad-industry primitives they DO quote, and check the result against the
economy simulator's break-even and target.

A quest completion is bounded:
    impression floor  <=  CPQ  <=  action ceiling
i.e. worth more than a passive view (it's opt-in, completed, verified —
the §1 thesis) but less than a full acquisition. The closest existing
analog is REWARDED VIDEO (opt-in, watch-to-completion, in-game reward),
so rewarded eCPM is the primary anchor.

Break-even and target are imported from the economy sim so there is one
source of truth for the numbers.

Benchmarks below are APPROXIMATE industry planning anchors, not quotes —
replace them with measured data from the experiment ladder in
docs/cpq-validation.md.
"""
from __future__ import annotations

from dataclasses import dataclass

from economy_simulator import Inputs, breakeven_cpq

# --- single source of truth: pull the thresholds from the economy model ---
_BASE = Inputs()
BREAKEVEN_CPQ = breakeven_cpq(_BASE.quests_per_day, _BASE.fill_rate["Y3"], _BASE.reward_share)
BREAKEVEN_RANGE = (
    breakeven_cpq(_BASE.quests_per_day, 0.95, _BASE.reward_share),  # aggressive fill
    breakeven_cpq(_BASE.quests_per_day, 0.65, _BASE.reward_share),  # conservative fill
)
TARGET_CPQ = _BASE.cpq  # 0.03 — the §8 assumption we want to reach

# --- approximate industry benchmarks (PLANNING ANCHORS, replace w/ measured) ---
# Rewarded-video eCPM: USD per 1000 completed opt-in views.
REWARDED_ECPM = {"global_blended": 8.0, "tier1_us": 18.0, "tier1_premium": 30.0}
# Offerwall / rewarded-action payout to publisher: USD per completed action.
OFFERWALL_CPA = {"low": 0.20, "mid": 0.80, "high": 2.50}
# Typical in-app CPC: USD per click.
IN_APP_CPC = {"low": 0.05, "mid": 0.25, "high": 1.00}


def cpq_from_ecpm(ecpm: float, ad_units_per_quest: float = 1.0) -> float:
    """CPQ if a quest is worth `ad_units_per_quest` completed rewarded views."""
    if ecpm < 0 or ad_units_per_quest < 0:
        raise ValueError("음수 입력 불가")
    return ecpm / 1000.0 * ad_units_per_quest


def cpq_from_cpc(cpc: float, clicks_per_quest: float = 1.0) -> float:
    """CPQ if a quest delivers `clicks_per_quest` high-intent clicks."""
    if cpc < 0 or clicks_per_quest < 0:
        raise ValueError("음수 입력 불가")
    return cpc * clicks_per_quest


def cpq_from_cpa(cpa: float, quest_to_action_cvr: float) -> float:
    """CPQ if a quest converts to a paid action at rate `quest_to_action_cvr`."""
    if cpa < 0 or not 0 <= quest_to_action_cvr <= 1:
        raise ValueError("cpa>=0, cvr in [0,1]")
    return cpa * quest_to_action_cvr


def ecpm_required_for(target_cpq: float, ad_units_per_quest: float = 1.0) -> float:
    """Inverse: the rewarded eCPM needed to reach `target_cpq`."""
    if ad_units_per_quest <= 0:
        raise ValueError("ad_units_per_quest는 0보다 커야 한다")
    return target_cpq / ad_units_per_quest * 1000.0


@dataclass(frozen=True)
class CPQVerdict:
    method: str
    scenario: str
    cpq: float
    clears_breakeven: bool
    clears_target: bool


def _verdict(method: str, scenario: str, cpq: float) -> CPQVerdict:
    return CPQVerdict(
        method=method,
        scenario=scenario,
        cpq=cpq,
        clears_breakeven=cpq >= BREAKEVEN_CPQ,
        clears_target=cpq >= TARGET_CPQ,
    )


def triangulate(ad_units_per_quest: float = 1.0) -> list[CPQVerdict]:
    """Derive CPQ across every lens/scenario and flag what clears the bars."""
    out: list[CPQVerdict] = []
    for name, ecpm in REWARDED_ECPM.items():
        out.append(_verdict("rewarded_ecpm", name, cpq_from_ecpm(ecpm, ad_units_per_quest)))
    for name, cpc in IN_APP_CPC.items():
        out.append(_verdict("cpc", name, cpq_from_cpc(cpc, clicks_per_quest=1.0)))
    # CPA lens: assume a modest 3% quest->action conversion
    for name, cpa in OFFERWALL_CPA.items():
        out.append(_verdict("cpa@3%cvr", name, cpq_from_cpa(cpa, 0.03)))
    return out


def _fmt(b: bool) -> str:
    return "✓" if b else "·"


if __name__ == "__main__":
    lo, hi = BREAKEVEN_RANGE
    print("QuestFi — CPQ 삼각검증 (§9 다음 관문)")
    print(f"  손익분기 CPQ = ${BREAKEVEN_CPQ:.4f}  (fill별 범위 ${lo:.4f}–${hi:.4f})")
    print(f"  목표 CPQ     = ${TARGET_CPQ:.4f}")
    print(f"  목표 도달에 필요한 rewarded eCPM (quest=1 view) = ${ecpm_required_for(TARGET_CPQ):.1f}")
    print()
    print(f"{'방법':<14}{'시나리오':<16}{'CPQ':>10}{'손익분기':>10}{'목표':>7}")
    print("-" * 58)
    for v in triangulate(ad_units_per_quest=1.0):
        print(
            f"{v.method:<14}{v.scenario:<16}${v.cpq:>8.4f}"
            f"{_fmt(v.clears_breakeven):>9}{_fmt(v.clears_target):>7}"
        )
    print()
    print("판정: quest=1 rewarded view 기준, global-blended eCPM은 손익분기 근처,")
    print("      목표 $0.03은 tier-1 트래픽 또는 완료 프리미엄/멀티유닛이 필요.")
