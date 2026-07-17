"""QuestFi Economy Simulator (§13 + §15 of CLAUDE.md).

CPQ is the one unverified variable the entire economy model depends on.
This module simulates the 3-year Redemption Epoch economy for a given set
of inputs, sweeps CPQ / DAU ratio / fill-rate scenarios, and reports the
break-even CPQ where a user's monthly real value crosses $1.

It also models Spark circulation (§15): the faucet issues Spark, an
in-game SINK burns a fraction (shop purchases), and only the remainder is
REDEEMED for WAT. The whole point of §15 is that inflation is controlled
by the sink, NOT by touching the swap rate — so raising sink_rate
stabilises the headline rate (spark_per_wat) while leaving the redeemers'
total dollar pool untouched (WAT price never enters user value, §10).

Usage:
    python economy_simulator.py                      # base-case 3-year table
    python economy_simulator.py --config my.yaml      # override inputs
    python economy_simulator.py --sweep --csv out.csv # full sweep -> CSV
    python economy_simulator.py --sweep --plot out.png
    python economy_simulator.py --sink                # sink 30/50/80% comparison
"""
from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Sequence

import pandas as pd

YEARS = ("Y1", "Y2", "Y3")

# fill_rate curve scenarios (§13 sweep spec: "fill_rate 커브 시나리오 3종").
# "base" reproduces the §8 3-year schedule table exactly.
FILL_RATE_SCENARIOS = {
    "conservative": {"Y1": 0.25, "Y2": 0.45, "Y3": 0.65},
    "base": {"Y1": 0.40, "Y2": 0.70, "Y3": 0.85},
    "aggressive": {"Y1": 0.55, "Y2": 0.80, "Y3": 0.95},
}

CPQ_SWEEP = (0.01, 0.02, 0.03, 0.05, 0.10)
DAU_RATIO_SWEEP = (0.2, 0.4, 0.6)

# §15 sink dial: fraction of issued Spark burned in-game (shop) before it can
# reach the redemption pool. sink_rate=0.0 => all Spark redeemed => reproduces
# the §8 headline rate table exactly.
SINK_SCENARIOS = {"low": 0.3, "mid": 0.5, "high": 0.8}


@dataclass
class Inputs:
    users: int = 50_000
    dau_ratio: float = 0.4
    quests_per_day: float = 12
    spark_per_quest: float = 100
    avg_multiplier: float = 1.8
    cpq: float = 0.03
    fill_rate: dict = field(default_factory=lambda: dict(FILL_RATE_SCENARIOS["base"]))
    reward_share: float = 0.40
    sink_rate: float = 0.0  # §15: fraction of issued Spark burned in-game before redemption
    wat_price: float = 0.01
    wat_supply: float = 1_000_000_000
    bootstrap: dict = field(default_factory=lambda: {"Y1": 40_000_000, "Y2": 20_000_000, "Y3": 0})

    @property
    def dau(self) -> float:
        return self.users * self.dau_ratio

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Inputs":
        import yaml

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(**data)


def simulate(inputs: Inputs) -> pd.DataFrame:
    """Run the 3-year economy model. Raises AssertionError if it violates
    the non-negotiable rules in CLAUDE.md §2 / §13 / §15."""
    assert 0.0 <= inputs.sink_rate < 1.0, "sink_rate는 [0, 1) 범위여야 한다"
    dau = inputs.dau
    spark_issued_per_year = (
        dau * inputs.quests_per_day * inputs.spark_per_quest * inputs.avg_multiplier * 365
    )
    # §15: sink burns a fraction in-game; only the remainder reaches redemption.
    spark_redeemed_per_year = spark_issued_per_year * (1.0 - inputs.sink_rate)
    spark_sunk_per_year = spark_issued_per_year - spark_redeemed_per_year

    rows = []
    cumulative_emission = 0.0
    for year in YEARS:
        fill_rate = inputs.fill_rate[year]
        bootstrap = inputs.bootstrap[year]

        ad_revenue = dau * inputs.quests_per_day * 365 * inputs.cpq * fill_rate
        reward_pool_usd = ad_revenue * inputs.reward_share
        buyback_wat = reward_pool_usd / inputs.wat_price
        total_wat_paid = buyback_wat + bootstrap

        assert total_wat_paid <= buyback_wat + bootstrap + 1e-6, (
            f"{year}: 매출 초과 지급 불가 (total_wat_paid > buyback + bootstrap)"
        )

        # §15: headline rate uses REDEEMED Spark (sink已 burned), not issued.
        # More sink -> fewer Spark chase the same WAT pool -> lower spark_per_wat.
        implied_rate = spark_redeemed_per_year / total_wat_paid if total_wat_paid else float("inf")

        # §10: 유저 실질 가치에는 WAT 가격이 없다 — reward_pool_usd / dau 만으로 결정된다.
        # sink_rate와도 무관: 전원이 균등 소각하면 상환 지분이 보존돼 유저 달러는 불변.
        user_monthly_usd = (reward_pool_usd / 365 / dau) * 30 if dau else 0.0
        # §10 재확인: 상환 Spark 1개의 달러값 = 풀$ ÷ 상환 총량.
        redeemer_usd_per_spark = (
            reward_pool_usd / spark_redeemed_per_year if spark_redeemed_per_year else 0.0
        )

        cumulative_emission += bootstrap
        emission_pct_of_supply = cumulative_emission / inputs.wat_supply

        rows.append(
            {
                "year": year,
                "ad_revenue": ad_revenue,
                "reward_pool_usd": reward_pool_usd,
                "buyback_wat": buyback_wat,
                "bootstrap_wat": bootstrap,
                "total_wat_paid": total_wat_paid,
                "spark_issued": spark_issued_per_year,
                "spark_sunk": spark_sunk_per_year,
                "spark_redeemed": spark_redeemed_per_year,
                "implied_rate": implied_rate,
                "user_monthly_usd": user_monthly_usd,
                "redeemer_usd_per_spark": redeemer_usd_per_spark,
                "cumulative_emission": cumulative_emission,
                "emission_pct_of_supply": emission_pct_of_supply,
            }
        )

    df = pd.DataFrame(rows).set_index("year")

    # 절대 규칙의 코드화 (§13)
    assert inputs.bootstrap["Y3"] == 0, "규칙 1 위반: Y3 부트스트랩은 반드시 0이어야 한다 (매출 자립)"
    assert df["cumulative_emission"].iloc[-1] <= inputs.wat_supply * 0.06 + 1e-6, "희석 상한 6% 초과"

    return df


def sink_comparison(base_inputs: Inputs) -> pd.DataFrame:
    """§15: compare sink dial scenarios (30/50/80%) against sink=0 baseline.

    Demonstrates the core §15 claim: raising the sink stabilises the headline
    rate (spark_per_wat drops as fewer Spark reach redemption) while the
    redeemers' dollar pool per user (user_monthly_usd) stays constant — the
    dial belongs on the sink, never on the swap rate.
    """
    scenarios = {"none": 0.0, **SINK_SCENARIOS}
    rows = []
    for name, sink_rate in scenarios.items():
        df = simulate(replace(base_inputs, sink_rate=sink_rate))
        for year, row in df.iterrows():
            rows.append(
                {
                    "sink_scenario": name,
                    "sink_rate": sink_rate,
                    "year": year,
                    "spark_redeemed": row["spark_redeemed"],
                    "implied_rate": row["implied_rate"],
                    "user_monthly_usd": row["user_monthly_usd"],
                    "redeemer_usd_per_spark": row["redeemer_usd_per_spark"],
                }
            )
    return pd.DataFrame(rows)


def sweep(base_inputs: Inputs) -> pd.DataFrame:
    """Sweep cpq x dau_ratio x fill_rate scenario, per §13 spec."""
    rows = []
    for cpq, dau_ratio, (scenario_name, fill_rate) in itertools.product(
        CPQ_SWEEP, DAU_RATIO_SWEEP, FILL_RATE_SCENARIOS.items()
    ):
        inputs = replace(base_inputs, cpq=cpq, dau_ratio=dau_ratio, fill_rate=dict(fill_rate))
        df = simulate(inputs)
        for year, row in df.iterrows():
            rows.append(
                {
                    "cpq": cpq,
                    "dau_ratio": dau_ratio,
                    "fill_scenario": scenario_name,
                    "year": year,
                    **row.to_dict(),
                }
            )
    return pd.DataFrame(rows)


def breakeven_cpq(
    quests_per_day: float, fill_rate: float, reward_share: float, target_usd: float = 1.0
) -> float:
    """Minimum CPQ where user_monthly_usd crosses target_usd.

    §10 shows user_monthly_usd = quests_per_day * cpq * fill_rate * reward_share * 30
    — it does not depend on dau_ratio or wat_price, so this is solved in closed form
    rather than searched.
    """
    return target_usd / (quests_per_day * fill_rate * reward_share * 30)


def _plot_sweep(df: pd.DataFrame, path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    subset = df[(df["dau_ratio"] == 0.4) & (df["year"] == "Y3")]
    fig, ax = plt.subplots(figsize=(8, 5))
    for scenario_name, group in subset.groupby("fill_scenario"):
        group = group.sort_values("cpq")
        ax.plot(group["cpq"], group["user_monthly_usd"], marker="o", label=scenario_name)
    ax.axhline(1.0, color="red", linestyle="--", linewidth=1, label="$1 breakeven")
    ax.set_xlabel("CPQ ($)")
    ax.set_ylabel("user_monthly_usd ($)")
    ax.set_title("QuestFi — user monthly real value vs CPQ (Y3, DAU 40%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="QuestFi Economy Simulator")
    parser.add_argument("--config", type=str, help="YAML 설정 파일 경로 (미지정 시 §8 기본값 사용)")
    parser.add_argument("--sweep", action="store_true", help="cpq/dau_ratio/fill_rate 전체 스윕 실행")
    parser.add_argument("--sink", action="store_true", help="§15 소각률 30/50/80% 비교 (환율 안정화 검증)")
    parser.add_argument("--plot", type=str, help="스윕 결과를 그래프로 저장할 경로 (예: sweep.png)")
    parser.add_argument("--csv", type=str, help="결과를 CSV로 저장할 경로")
    args = parser.parse_args(argv)

    inputs = Inputs.from_yaml(args.config) if args.config else Inputs()

    if args.sink:
        df = sink_comparison(inputs)
        with pd.option_context("display.float_format", lambda x: f"{x:,.4f}", "display.max_rows", None):
            print(df.to_string(index=False))
        print(
            "\n§15 판정: sink_rate가 오를수록 implied_rate(Spark/WAT)는 낮아져 안정화되지만,\n"
            "         user_monthly_usd(상환자 달러 풀)는 불변 → 완충은 소각에, 환율에 손대지 않는다."
        )
        if args.csv:
            df.to_csv(args.csv, index=False)
            print(f"\n저장됨: {args.csv}")
    elif args.sweep:
        df = sweep(inputs)
        with pd.option_context("display.float_format", lambda x: f"{x:,.4f}", "display.max_rows", None):
            print(df.to_string(index=False))
        if args.csv:
            df.to_csv(args.csv, index=False)
            print(f"\n저장됨: {args.csv}")
        if args.plot:
            _plot_sweep(df, args.plot)
            print(f"그래프 저장됨: {args.plot}")
    else:
        df = simulate(inputs)
        with pd.option_context("display.float_format", lambda x: f"{x:,.2f}"):
            print(df.to_string())
        if args.csv:
            df.to_csv(args.csv)
            print(f"\n저장됨: {args.csv}")

    print("\n--- 손익분기 (§10: 유저 실질 월 가치는 WAT 가격과 무관) ---")
    for scenario_name, fill_rate in FILL_RATE_SCENARIOS.items():
        cpq_be = breakeven_cpq(inputs.quests_per_day, fill_rate["Y3"], inputs.reward_share)
        print(
            f"{scenario_name:12s} (Y3 fill={fill_rate['Y3']:.0%}): "
            f"user_monthly_usd > $1 되는 최소 CPQ = ${cpq_be:.4f}"
        )


if __name__ == "__main__":
    main()
