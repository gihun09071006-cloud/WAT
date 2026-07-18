"""Wallet-abstraction onboarding logic (§12 · C5).

Principle: defer and hide the wallet. Spark is off-chain, so playing and
spending need NO wallet at all. Two tiers:
  - people who just play the game -> left alone, zero wallet, forever.
  - people who want to monetize -> only THEN prompted into the wallet step.

Gas policy (founder decision): the operator does NOT sponsor gas. Instead
gas is borne by the user and netted out of the WAT payout (ERC-4337 ERC-20
paymaster) so the operator pays nothing AND the user never has to hold a
native gas token. This only works on a cheap chain (L2/appchain, cents per
tx) — at L1 gas ($1-20) a ~$3 reward would be eaten, so a low-gas chain is
now a hard requirement, not a preference (see docs/wallet-abstraction.md).

This module is the progressive-disclosure decision core. It composes with
trust_score (which gates WHETHER a user may redeem); this decides HOW the
wallet behaves once they do.
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
    wallet_mode: str        # "none" | "embedded" | "connected" | "self_custody"
    gas_payer: str          # "none" (no tx) | "user" (netted from WAT payout)
    kyc_required: bool
    reason: str


def onboarding_decision(
    *,
    has_account: bool,
    is_redeeming: bool,
    redemption_value_usd: float = 0.0,
    wants_export: bool = False,
    embedded_wallet: bool = True,
) -> OnboardingState:
    """Decide the wallet/custody/gas/KYC state for a user's current step.

    embedded_wallet=True (recommended) auto-provisions a low-friction embedded
    wallet at the reward step; False means the user connects an external wallet.
    Either way the operator sponsors no gas — the user bears it, netted from
    their WAT payout.
    """
    if redemption_value_usd < 0:
        raise ValueError("redemption_value_usd는 음수 불가")

    if not has_account:
        return OnboardingState(Stage.BROWSING, False, "none", "none", False,
                               "계정 전 — 지갑 개념이 화면에 없음")

    if wants_export:
        kyc = redemption_value_usd >= KYC_THRESHOLD_USD
        return OnboardingState(Stage.SELF_CUSTODY, True, "self_custody", "user", kyc,
                               "자가수탁 export — 유저가 키·가스 전부 부담(비수탁 이탈 경로)")

    if not is_redeeming:
        # tier 1: just here to play -> left alone, no wallet, no gas, no KYC
        return OnboardingState(Stage.PLAYING, False, "none", "none", False,
                               "오프체인 Spark — 지갑 없이 플레이·소비 (그냥 게임)")

    # tier 2: wants rewards -> now (and only now) prompted into the wallet step.
    # Operator sponsors no gas; user bears it, netted from the WAT payout.
    kyc = redemption_value_usd >= KYC_THRESHOLD_USD
    mode = "embedded" if embedded_wallet else "connected"
    how = "임베디드 지갑 자동 생성" if embedded_wallet else "외부 지갑 연동"
    reason = f"보상 상환 시에만 지갑 단계 · {how} · 가스는 유저 부담(WAT에서 차감)"
    if kyc:
        reason += " · 고액이라 KYC step-up"
    return OnboardingState(Stage.REDEEMING, True, mode, "user", kyc, reason)


if __name__ == "__main__":
    cases = [
        ("둘러보는 방문자", dict(has_account=False, is_redeeming=False)),
        ("플레이 중(상환 전)", dict(has_account=True, is_redeeming=False)),
        ("첫 상환 $3", dict(has_account=True, is_redeeming=True, redemption_value_usd=3.0)),
        ("고액 상환 $500", dict(has_account=True, is_redeeming=True, redemption_value_usd=500.0)),
        ("자가수탁 export", dict(has_account=True, is_redeeming=False, wants_export=True)),
    ]
    print(f"{'상황':<18}{'지갑':>8}{'모드':>13}{'가스':>8}{'KYC':>6}   설명")
    print("-" * 92)
    for name, kw in cases:
        s = onboarding_decision(**kw)
        print(f"{name:<18}{('필요' if s.needs_wallet else '불필요'):>8}{s.wallet_mode:>13}"
              f"{s.gas_payer:>8}{('예' if s.kyc_required else '—'):>6}   {s.reason}")
    print("\n※ 대부분 유저는 PLAYING에 머묾 — 지갑 0. 지갑은 '보상 원할 때'만 뒤에서 생성, 가스는 유저 부담(WAT 차감).")
