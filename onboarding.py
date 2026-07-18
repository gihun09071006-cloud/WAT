"""Wallet-abstraction onboarding logic (§12 · C5).

Principle: defer and hide the wallet. Spark is off-chain, so playing and
spending need NO wallet at all. A wallet only materialises — silently,
behind the scenes — at a user's first Spark->WAT redemption. Most users
never touch a seed phrase; a small monthly reward never triggers KYC.

This module is the progressive-disclosure decision core: given where a
user is in their journey, it decides whether a wallet is needed, the
custody mode, gas sponsorship, and whether KYC step-up applies. It
composes with trust_score (which gates WHETHER a user may redeem); this
decides HOW the wallet behaves once they do.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# KYC step-up only above this redemption value; small rewards (~$3/mo, §8)
# never trigger it. Aggregated large withdrawals do.
KYC_THRESHOLD_USD = 200.0


class Stage(str, Enum):
    BROWSING = "browsing"          # no account — wallet concept absent
    PLAYING = "playing"            # off-chain Spark, NO wallet needed
    REDEEMING = "redeeming"        # embedded wallet auto-provisioned, gas sponsored
    SELF_CUSTODY = "self_custody"  # advanced user exported to self-custody


@dataclass(frozen=True)
class OnboardingState:
    stage: Stage
    needs_wallet: bool
    wallet_mode: str        # "none" | "embedded" | "self_custody"
    gas_sponsored: bool
    kyc_required: bool
    reason: str


def onboarding_decision(
    *,
    has_account: bool,
    is_redeeming: bool,
    redemption_value_usd: float = 0.0,
    wants_export: bool = False,
) -> OnboardingState:
    """Decide the wallet/custody/gas/KYC state for a user's current step."""
    if redemption_value_usd < 0:
        raise ValueError("redemption_value_usd는 음수 불가")

    if not has_account:
        return OnboardingState(Stage.BROWSING, False, "none", False, False,
                               "계정 전 — 지갑 개념이 화면에 없음")

    if wants_export:
        kyc = redemption_value_usd >= KYC_THRESHOLD_USD
        return OnboardingState(Stage.SELF_CUSTODY, True, "self_custody", False, kyc,
                               "자가수탁 export — 유저가 키·가스 부담(비수탁 이탈 경로)")

    if not is_redeeming:
        # the whole point of §12: play and spend with off-chain Spark, no wallet
        return OnboardingState(Stage.PLAYING, False, "none", False, False,
                               "오프체인 Spark — 지갑 없이 플레이·소비")

    # first/ongoing redemption -> wallet materialises silently
    kyc = redemption_value_usd >= KYC_THRESHOLD_USD
    reason = "첫 상환 시 임베디드 지갑 자동 생성 · 가스 스폰서(페이마스터)"
    if kyc:
        reason += " · 고액이라 KYC step-up"
    return OnboardingState(Stage.REDEEMING, True, "embedded", True, kyc, reason)


if __name__ == "__main__":
    cases = [
        ("둘러보는 방문자", dict(has_account=False, is_redeeming=False)),
        ("플레이 중(상환 전)", dict(has_account=True, is_redeeming=False)),
        ("첫 상환 $3", dict(has_account=True, is_redeeming=True, redemption_value_usd=3.0)),
        ("고액 상환 $500", dict(has_account=True, is_redeeming=True, redemption_value_usd=500.0)),
        ("자가수탁 export", dict(has_account=True, is_redeeming=False, wants_export=True)),
    ]
    print(f"{'상황':<18}{'지갑':>8}{'모드':>13}{'가스스폰서':>10}{'KYC':>6}   설명")
    print("-" * 84)
    for name, kw in cases:
        s = onboarding_decision(**kw)
        print(f"{name:<18}{('필요' if s.needs_wallet else '불필요'):>8}{s.wallet_mode:>13}"
              f"{('예' if s.gas_sponsored else '—'):>9}{('예' if s.kyc_required else '—'):>6}   {s.reason}")
    print("\n※ 대부분 유저는 PLAYING에 머물러 지갑을 아예 안 만짐. 지갑은 첫 상환 순간에만 뒤에서 생성.")
