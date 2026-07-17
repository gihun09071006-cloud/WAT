"""QuestFi Redemption Epoch engine (§4 + §13 priority 2 of CLAUDE.md).

The monthly settlement is a PURE FUNCTION, isolated so it can be tested
and audited independently of the game, the AMM, or any UI:

    settle_epoch(pool_usd, wat_price, total_spark_redeemed) -> EpochResult

Non-negotiable properties this module guarantees (and test_redemption_epoch
verifies):

  1. The rate is a RESULT, never an announced peg (§ rule 3). It falls out
     of pool_wat and the Spark that showed up — nothing is promised.
  2. Payout can never exceed the pool (§ rule 1). Sum of all users' WAT
     equals pool_wat exactly; the system is structurally solvent.
  3. A user's DOLLAR value is independent of wat_price (§10). Price only
     changes how many WAT tokens represent the same dollars.

Everything is denominated the way §4 mandates: rate = Spark per WAT.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EpochResult:
    """The settled state of one Redemption Epoch. Disclosed AFTER the fact
    (§ rule 3) — never pre-announced."""

    pool_usd: float
    wat_price: float
    total_spark_redeemed: float
    pool_wat: float          # WAT distributable this epoch (revenue-sourced, not emitted)
    spark_per_wat: float     # the emergent headline rate — "이번 달 190 Spark = 1 WAT"
    usd_per_spark: float     # §10 real value; provably wat_price-independent

    def wat_for(self, user_spark: float) -> float:
        """WAT a user receives for redeeming `user_spark`."""
        if user_spark < 0:
            raise ValueError("user_spark는 음수일 수 없다")
        if self.spark_per_wat == 0:
            return 0.0
        return user_spark / self.spark_per_wat

    def usd_for(self, user_spark: float) -> float:
        """Dollar value a user realizes. Equals user_spark * usd_per_spark and
        does NOT depend on wat_price (§10)."""
        return self.wat_for(user_spark) * self.wat_price


def settle_epoch(
    pool_usd: float, wat_price: float, total_spark_redeemed: float
) -> EpochResult:
    """Settle one epoch. Pure: same inputs -> same output, no side effects.

    Args:
        pool_usd: dollar reward pool for this epoch = ad_revenue * reward_share.
        wat_price: WAT market price at settlement (USD per WAT).
        total_spark_redeemed: total Spark all users submitted this epoch (S).

    Returns:
        EpochResult with the emergent rate and per-Spark dollar value.

    Raises:
        ValueError: on inputs that make settlement undefined.
    """
    if wat_price <= 0:
        raise ValueError("wat_price는 0보다 커야 한다")
    if pool_usd < 0:
        raise ValueError("pool_usd는 음수일 수 없다")
    if total_spark_redeemed <= 0:
        raise ValueError("정산할 상환 신청 Spark가 없다 (total_spark_redeemed <= 0)")

    pool_wat = pool_usd / wat_price
    # rate = Spark per WAT. Emergent (§4): S divided by the WAT the revenue buys.
    spark_per_wat = total_spark_redeemed / pool_wat if pool_wat > 0 else 0.0
    # §10: usd_per_spark = pool_usd / S — wat_price cancels out entirely.
    usd_per_spark = pool_usd / total_spark_redeemed

    return EpochResult(
        pool_usd=pool_usd,
        wat_price=wat_price,
        total_spark_redeemed=total_spark_redeemed,
        pool_wat=pool_wat,
        spark_per_wat=spark_per_wat,
        usd_per_spark=usd_per_spark,
    )


if __name__ == "__main__":
    # Illustration: the §8 Y1 monthly slice, and the §10 price-invariance.
    monthly_pool = 420_480 / 12          # Y1 reward pool spread over 12 epochs
    monthly_spark = 15_768_000_000 / 12  # Y1 Spark issued, monthly

    for price in (0.01, 0.10):  # WAT price 10x
        r = settle_epoch(monthly_pool, price, monthly_spark)
        print(
            f"WAT=${price:.2f}: rate={r.spark_per_wat:,.1f} Spark/WAT · "
            f"pool={r.pool_wat:,.0f} WAT · "
            f"유저 1,000 Spark => {r.wat_for(1000):.2f} WAT = ${r.usd_for(1000):.4f}"
        )
    print("→ 가격이 10배여도 유저 달러값 동일 (§10). 수량만 1/10.")
