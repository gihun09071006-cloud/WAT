"""QuestFi DEX liquidity engine (§10 + §15 of CLAUDE.md).

Decision log: monthly liquidity is provided as a WAT/USDC constant-product
(x*y=k) AMM pool. The USDC side comes from advertiser revenue; the WAT side
comes from the ecosystem fund / treasury — NOT new emission (rule 1).

The IR story this module quantifies: **ad revenue compounds into market
depth.** Every month the operator injects revenue-funded USDC (plus matching
treasury WAT) into the pool, so the pool gets deeper and the slippage a
redeemer eats when selling WAT shrinks month over month.

It also quantifies the honest downside flagged in §15: **impermanent loss**
on the LP position when the WAT price moves.

Pure functions + small dataclasses, no external deps beyond the stdlib.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Pool:
    """A constant-product WAT/USDC pool. Price is quoted as USDC per WAT."""

    reserve_wat: float
    reserve_usdc: float
    fee: float = 0.003  # 0.3% swap fee, Uniswap-v2 style

    def __post_init__(self) -> None:
        if self.reserve_wat <= 0 or self.reserve_usdc <= 0:
            raise ValueError("풀 리저브는 양수여야 한다")
        if not 0 <= self.fee < 1:
            raise ValueError("fee는 [0, 1) 범위여야 한다")

    @property
    def k(self) -> float:
        return self.reserve_wat * self.reserve_usdc

    @property
    def spot_price(self) -> float:
        """USDC per WAT at the margin."""
        return self.reserve_usdc / self.reserve_wat

    @property
    def tvl_usdc(self) -> float:
        """Total value locked, in USDC terms (both sides valued at spot)."""
        return 2 * self.reserve_usdc


@dataclass(frozen=True)
class SwapResult:
    usdc_out: float
    pool_after: Pool
    price_after: float
    slippage: float  # fraction lost vs the pre-trade spot price (incl. fee)


def swap_wat_for_usdc(pool: Pool, wat_in: float) -> SwapResult:
    """Sell `wat_in` WAT into the pool for USDC (a redeemer cashing out).

    Uses the constant-product invariant with a fee retained in the pool.
    """
    if wat_in <= 0:
        raise ValueError("wat_in은 0보다 커야 한다")

    wat_in_after_fee = wat_in * (1 - pool.fee)
    new_reserve_wat = pool.reserve_wat + wat_in_after_fee
    new_reserve_usdc = pool.k / new_reserve_wat
    usdc_out = pool.reserve_usdc - new_reserve_usdc

    # The full wat_in (fee included) stays in the pool reserves.
    pool_after = Pool(
        reserve_wat=pool.reserve_wat + wat_in,
        reserve_usdc=pool.reserve_usdc - usdc_out,
        fee=pool.fee,
    )

    ideal_usdc = wat_in * pool.spot_price  # no-slippage, no-fee benchmark
    slippage = 1 - usdc_out / ideal_usdc if ideal_usdc > 0 else 0.0

    return SwapResult(
        usdc_out=usdc_out,
        pool_after=pool_after,
        price_after=pool_after.spot_price,
        slippage=slippage,
    )


def add_liquidity_price_neutral(pool: Pool, usdc_in: float) -> tuple[Pool, float]:
    """Add `usdc_in` USDC plus the matching WAT at the current ratio, so the
    price does not move. Returns the new pool and the WAT amount drawn from
    the treasury.

    This is how the operator deploys monthly revenue: USDC from ads, WAT from
    the ecosystem fund (rule 1 — no new emission).
    """
    if usdc_in <= 0:
        raise ValueError("usdc_in은 0보다 커야 한다")
    wat_in = usdc_in / pool.spot_price
    new_pool = replace(
        pool,
        reserve_wat=pool.reserve_wat + wat_in,
        reserve_usdc=pool.reserve_usdc + usdc_in,
    )
    return new_pool, wat_in


def impermanent_loss(price_ratio: float) -> float:
    """Impermanent loss of a 50/50 constant-product LP vs simply holding,
    given `price_ratio` = new_price / old_price.

    Returns a non-positive fraction (e.g. -0.057 = 5.7% worse than holding).
    """
    if price_ratio <= 0:
        raise ValueError("price_ratio는 0보다 커야 한다")
    return 2 * math.sqrt(price_ratio) / (1 + price_ratio) - 1


@dataclass(frozen=True)
class MonthState:
    month: int
    tvl_usdc: float
    spot_price: float
    redemption_slippage: float  # slippage on that month's redemption sell
    treasury_wat_used: float    # cumulative WAT pulled from treasury for LP


def simulate_lp_growth(
    *,
    months: int,
    initial_wat: float,
    initial_usdc: float,
    monthly_usdc_injection: float,
    monthly_redeemed_wat: float,
    injection_growth: float = 0.0,
    fee: float = 0.003,
) -> list[MonthState]:
    """Simulate the monthly LP cycle.

    Each month, in order:
      1. Operator injects revenue-funded USDC (+ matching treasury WAT),
         deepening the pool price-neutrally.
      2. Redeemers sell `monthly_redeemed_wat` WAT into the pool; we record
         the slippage they eat. Depth from step 1 makes this shrink over time.

    Args:
        months: number of months to run.
        initial_wat / initial_usdc: seed liquidity.
        monthly_usdc_injection: revenue-funded USDC added in month 1.
        monthly_redeemed_wat: WAT sold by redeemers each month.
        injection_growth: month-over-month growth of the injection (e.g. 0.05
            as ad revenue ramps). Compounds.
        fee: pool swap fee.

    Returns:
        Per-month MonthState list.
    """
    pool = Pool(reserve_wat=initial_wat, reserve_usdc=initial_usdc, fee=fee)
    injection = monthly_usdc_injection
    treasury_wat_used = 0.0
    states: list[MonthState] = []

    for m in range(1, months + 1):
        pool, wat_from_treasury = add_liquidity_price_neutral(pool, injection)
        treasury_wat_used += wat_from_treasury

        swap = swap_wat_for_usdc(pool, monthly_redeemed_wat)
        pool = swap.pool_after

        states.append(
            MonthState(
                month=m,
                tvl_usdc=pool.tvl_usdc,
                spot_price=pool.spot_price,
                redemption_slippage=swap.slippage,
                treasury_wat_used=treasury_wat_used,
            )
        )
        injection *= 1 + injection_growth

    return states


if __name__ == "__main__":
    # IR illustration: seed a shallow pool, drip Y1 monthly revenue in, watch
    # slippage on a fixed redemption sell collapse as depth compounds.
    states = simulate_lp_growth(
        months=12,
        initial_wat=5_000_000,      # $50k WAT side at $0.01
        initial_usdc=50_000,
        monthly_usdc_injection=35_000,   # ~ $420k Y1 reward pool / 12
        monthly_redeemed_wat=1_000_000,  # redeemers cashing out ~$10k/mo
        injection_growth=0.05,
    )
    print(f"{'월':>3} {'TVL($)':>14} {'가격':>10} {'상환 슬리피지':>14}")
    for s in states:
        print(
            f"{s.month:>3} {s.tvl_usdc:>14,.0f} {s.spot_price:>10.5f} "
            f"{s.redemption_slippage:>13.2%}"
        )
    print("\n비영구손실(IL) 민감도:")
    for pr in (0.5, 0.8, 1.0, 1.25, 2.0, 4.0):
        print(f"  가격 {pr:>4.2f}x -> IL {impermanent_loss(pr):>7.2%}")
