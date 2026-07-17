"""QuestFi anti-bot Trust Score (§4 unlock · §11 hidden card · §15 gate).

Core idea — gate the EXIT, not the play:
    Bots may play and earn Spark. They are stopped at the single chokepoint
    where money leaves: the monthly Spark -> WAT redemption. This is a batch,
    high-scrutiny decision, so we can afford heavy analysis and never degrade
    the human's play experience with real-time captchas.

Why this protects everything at once:
    - Advertiser ROI (§1): only genuine human completions become billable
      quality; bot completions are filtered out of the redeemed pool.
    - Honest redeemers (§4/§15): bot Spark never enters S (redeemed total),
      so it can't dilute the rate real users get.
    - CPQ measurement (cpq-validation.md): bot completions can't inflate fill
      and produce a false CPQ.

Design stance:
    - Continuous Trust Score in [0,1], not a binary ban. Graduated tiers.
    - Passive / behavioral signals first (privacy, §12 "지갑 개념 없이 진입").
      Step-up friction (captcha, attestation, light proof-of-personhood) is
      applied ONLY when risk × redemption value warrants it. A $3 human never
      sees KYC.
    - False-positive (blocking a real human's earned reward) is the worst
      error -> restrict-with-appeal, never silent hard-ban, for non-confirmed.
    - Transparent rules v1 (launchable, auditable); evolvable to ML later.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# --- signal weights (sum to 1.0). Behavioral is highest: a plane-shooter is a
# rich behavioral-biometrics surface (aim/dodge/timing), our best bot signal. ---
WEIGHTS = {
    "behavioral_humanity": 0.24,
    "device_integrity": 0.22,
    "network_reputation": 0.14,
    "account_maturity": 0.14,
    "graph_independence": 0.14,
    "ad_interaction_quality": 0.12,
}

# hard-flag parameters
MAX_ACCOUNTS_PER_DEVICE = 3          # above this = device farm
DEVICE_FARM_MULTIPLIER = 0.30        # score is multiplicatively crushed
GEO_VELOCITY_SCORE_CAP = 0.40        # impossible travel caps trust

# tier thresholds
TRUSTED_MIN = 0.75
PROVISIONAL_MIN = 0.50
RESTRICTED_MIN = 0.25

# redemption caps (Sybil-abuse guards; humans earn ~$3/mo per §8 anyway)
PROVISIONAL_EPOCH_CAP_USD = 5.0


@dataclass(frozen=True)
class Signals:
    """Per-account signals. Continuous fields are in [0,1], higher = more human.

    Sources (illustrative):
      behavioral_humanity   -- touch dynamics, reaction-time distribution,
                               skill curve, session circadian rhythm.
      device_integrity      -- Play Integrity / App Attest, emulator & root
                               detection, sensor entropy.
      network_reputation    -- residential vs datacenter/VPN/proxy, ASN cluster.
      account_maturity      -- age & sane progression velocity (no instant-max).
      graph_independence    -- 1 = not in a referral/redemption Sybil cluster.
      ad_interaction_quality-- genuine "부품 스캔" engagement vs auto-click.
    """

    behavioral_humanity: float
    device_integrity: float
    network_reputation: float
    account_maturity: float
    graph_independence: float
    ad_interaction_quality: float
    device_account_count: int = 1
    geo_velocity_violation: bool = False

    def __post_init__(self) -> None:
        for k in WEIGHTS:
            v = getattr(self, k)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{k}는 [0,1] 범위여야 한다 (got {v})")
        if self.device_account_count < 1:
            raise ValueError("device_account_count는 1 이상")


class Tier(str, Enum):
    TRUSTED = "trusted"        # full redemption
    PROVISIONAL = "provisional"  # capped redemption; step-up for more
    RESTRICTED = "restricted"  # earn only; must step-up to redeem
    BLOCKED = "blocked"        # bot-confirmed; excluded from S, counted publicly


class Action(str, Enum):
    ALLOW = "allow"
    ALLOW_CAPPED = "allow_capped"
    STEP_UP_REQUIRED = "step_up_required"
    RESTRICT = "restrict"
    BLOCK = "block"


def trust_score(s: Signals) -> float:
    """Weighted-ensemble Trust Score in [0,1], then hard-flag adjustments."""
    score = sum(WEIGHTS[k] * getattr(s, k) for k in WEIGHTS)
    if s.device_account_count > MAX_ACCOUNTS_PER_DEVICE:
        score *= DEVICE_FARM_MULTIPLIER
    if s.geo_velocity_violation:
        score = min(score, GEO_VELOCITY_SCORE_CAP)
    return max(0.0, min(1.0, score))


def classify(score: float) -> Tier:
    if score >= TRUSTED_MIN:
        return Tier.TRUSTED
    if score >= PROVISIONAL_MIN:
        return Tier.PROVISIONAL
    if score >= RESTRICTED_MIN:
        return Tier.RESTRICTED
    return Tier.BLOCKED


@dataclass(frozen=True)
class RedemptionDecision:
    action: Action
    approved_usd: float
    step_up_required: bool
    tier: Tier
    reason: str


def redemption_decision(score: float, requested_usd: float) -> RedemptionDecision:
    """Risk-based gate: friction scales with tier AND requested amount."""
    if requested_usd < 0:
        raise ValueError("requested_usd는 음수 불가")
    tier = classify(score)

    if tier is Tier.BLOCKED:
        return RedemptionDecision(Action.BLOCK, 0.0, False, tier,
                                  "봇 확정 — 상환 불가, 공개 지표(§11)에 집계")
    if tier is Tier.RESTRICTED:
        return RedemptionDecision(Action.RESTRICT, 0.0, True, tier,
                                  "신뢰도 부족 — Spark 획득은 가능, 상환하려면 단계 인증 필요")
    if tier is Tier.PROVISIONAL:
        if requested_usd <= PROVISIONAL_EPOCH_CAP_USD:
            return RedemptionDecision(Action.ALLOW_CAPPED, requested_usd, False, tier,
                                      f"임시 신뢰 — 에폭당 ${PROVISIONAL_EPOCH_CAP_USD:.0f} 한도 내 승인")
        return RedemptionDecision(Action.STEP_UP_REQUIRED, PROVISIONAL_EPOCH_CAP_USD, True, tier,
                                  f"한도 초과 — ${PROVISIONAL_EPOCH_CAP_USD:.0f} 초과분은 단계 인증 필요")
    # TRUSTED
    return RedemptionDecision(Action.ALLOW, requested_usd, False, tier, "신뢰 계정 — 전액 승인")


@dataclass(frozen=True)
class IntegrityReport:
    total_spark: float
    redeemable_spark: float   # enters S (honest redemption pool)
    filtered_spark: float     # bot/blocked/restricted — never dilutes rate
    filtered_rate: float
    blocked_accounts: int     # the §11 "봇 차단 N" number


def pool_integrity(accounts: list[tuple[float, Signals]]) -> IntegrityReport:
    """Given (spark_claimed, signals) per account, split the redemption pool
    into honest S vs filtered. Produces the §11 hidden-card metrics and the
    CPQ-integrity guard: bot Spark is excluded from S entirely."""
    total = redeemable = filtered = 0.0
    blocked = 0
    for spark, sig in accounts:
        if spark < 0:
            raise ValueError("spark는 음수 불가")
        total += spark
        tier = classify(trust_score(sig))
        if tier in (Tier.TRUSTED, Tier.PROVISIONAL):
            redeemable += spark
        else:
            filtered += spark
            if tier is Tier.BLOCKED:
                blocked += 1
    rate = filtered / total if total else 0.0
    return IntegrityReport(total, redeemable, filtered, rate, blocked)


if __name__ == "__main__":
    human = Signals(0.85, 0.9, 0.8, 0.7, 0.9, 0.8)
    emulator_farm = Signals(0.2, 0.05, 0.1, 0.2, 0.1, 0.1, device_account_count=40)
    provisional = Signals(0.6, 0.6, 0.55, 0.5, 0.6, 0.55)

    for name, s in [("human", human), ("emulator_farm", emulator_farm), ("provisional", provisional)]:
        sc = trust_score(s)
        d = redemption_decision(sc, requested_usd=8.0)
        print(f"{name:14s} score={sc:.2f} tier={classify(sc).value:11s} "
              f"→ {d.action.value:16s} 승인 ${d.approved_usd:.2f}  ({d.reason})")

    rpt = pool_integrity([(1000, human), (50000, emulator_farm), (800, provisional)])
    print(f"\n풀 무결성: 총 {rpt.total_spark:,.0f} Spark → 정직 S {rpt.redeemable_spark:,.0f} · "
          f"봇 필터 {rpt.filtered_spark:,.0f} ({rpt.filtered_rate:.0%}) · 봇 차단 {rpt.blocked_accounts}건")
    print("→ 봇 Spark는 S에 진입하지 못해 정직한 유저 환율을 희석하지 않는다 (§15).")
