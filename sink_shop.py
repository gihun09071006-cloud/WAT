"""Sink & Shop economy — the active inflation dial (§15 · §6 · §12).

§15 says inflation is buffered on the SINK (shop prices / new cosmetics),
never on the WAT swap rate. But the economy model so far only had a bare
`sink_rate` parameter — no actual sinks. This module gives it substance:
a shop catalog (planes / pilots / pets / cosmetics) whose demand and prices
determine how much Spark is burned, and thus the effective sink_rate that
feeds economy_simulator.

Key property demonstrated: adding desirable items or tuning shop prices
raises the burn -> stabilises the redemption rate, WITHOUT touching the
Spark->WAT exchange rate (rule 3). The price dial has a revenue-maximising
sweet spot, so "raise prices to soak up inflation" has a real optimum.

Multipliers (§6) affect Spark EARNING, not this sink; the sink is priced in
Spark and burns on purchase (§3: Spark is destroyed when spent).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# §12 rarity ladder. Weight = intensity/prestige pull of the tier.
RARITY_PULL = {"Rare": 1.0, "Epic": 1.3, "Legendary": 1.7, "Mythic": 2.1, "Genesis": 2.6}


@dataclass(frozen=True)
class ShopItem:
    name: str
    category: str          # plane / pilot / pet / cosmetic
    rarity: str            # §12 ladder
    price: float           # in the item's currency
    appeal: float          # base demand breadth in [0,1]
    currency: str = "spark"  # "spark"(프리미엄 등급) | "coin"(일반 등급, 게임머니)

    def __post_init__(self) -> None:
        if self.rarity not in RARITY_PULL:
            raise ValueError(f"알 수 없는 등급: {self.rarity}")
        if not 0.0 <= self.appeal <= 1.0 or self.price <= 0:
            raise ValueError("appeal은 [0,1], price는 양수")
        if self.currency not in ("spark", "coin"):
            raise ValueError("currency는 'spark' 또는 'coin'")


def expected_spend_per_user(item: ShopItem, budget: float, k: float = 0.5) -> float:
    """Expected Spark a user burns on `item` per period.

    Demand curve: spend = pull * price * exp(-price / (budget*k)). Cheap items
    sell broadly; expensive items sell rarely. Spend is maximised at
    price = budget*k (the price sweet spot), so raising prices soaks up Spark
    only up to that point.
    """
    if budget <= 0:
        return 0.0
    pull = item.appeal * RARITY_PULL[item.rarity]
    return pull * item.price * math.exp(-item.price / (budget * k))


def sink_rate(catalog: list[ShopItem], budget: float, k: float = 0.5,
              max_frac: float = 0.9, currency: str = "spark") -> float:
    """Effective fraction of issued Spark burned in the shop, in [0, max_frac].

    Only PREMIUM (Spark-priced) items count toward the Spark sink — normal
    (coin/game-money) items sit outside the value economy (§3 3-currency split).
    `budget` = Spark a user earns per period. Capped because users won't spend
    everything (some redeems or holds)."""
    total = sum(expected_spend_per_user(i, budget, k)
                for i in catalog if i.currency == currency)
    return min(max_frac, total / budget) if budget > 0 else 0.0


def apply_price_dial(catalog: list[ShopItem], multiplier: float) -> list[ShopItem]:
    """The §15 active dial: scale all shop prices by `multiplier`. Legal
    (store prices), never touches the WAT rate."""
    if multiplier <= 0:
        raise ValueError("multiplier는 양수")
    from dataclasses import replace
    return [replace(i, price=i.price * multiplier) for i in catalog]


# a starter catalog. §3: 일반 등급 = 게임머니(coin), 프리미엄 등급 = Spark.
# Only spark items are the Spark sink; coin items are pure game-money balance.
DEFAULT_CATALOG = [
    ShopItem("기본 도색", "cosmetic", "Rare", 300, 0.55, currency="coin"),     # 일반=게임머니
    ShopItem("일반 조종사", "pilot", "Rare", 500, 0.45, currency="coin"),      # 일반=게임머니
    ShopItem("정예 조종사", "pilot", "Epic", 900, 0.45),                        # 프리미엄=Spark
    ShopItem("부스터 트레일", "cosmetic", "Epic", 700, 0.40),
    ShopItem("레전더리 펫", "pet", "Legendary", 1800, 0.55),
    ShopItem("미식 기체 스킨", "plane", "Mythic", 3200, 0.45),
    ShopItem("제네시스 기체", "plane", "Genesis", 9000, 0.30),
]


if __name__ == "__main__":
    budget = 2000.0  # ~ daily Spark per active user (100 x 12 quests x 1.8 mult ≈ 2160)

    print(f"기준 유저 예산 = {budget:,.0f} Spark/기간  (프리미엄=Spark 아이템만 소각에 계산)\n")
    print("■ 프리미엄(Spark) 카탈로그 풍부함 → 소각률")
    spark_items = [i for i in DEFAULT_CATALOG if i.currency == "spark"]
    sparse = spark_items[:2]
    print(f"   빈약(프리미엄 2종)   sink_rate = {sink_rate(sparse, budget):.0%}")
    print(f"   기본(프리미엄 5종)   sink_rate = {sink_rate(DEFAULT_CATALOG, budget):.0%}")
    rich = DEFAULT_CATALOG + [ShopItem("길드 문장", "cosmetic", "Legendary", 1200, 0.5),
                              ShopItem("시즌 패스 스킨", "plane", "Mythic", 2500, 0.5)]
    print(f"   풍부(프리미엄 7종)   sink_rate = {sink_rate(rich, budget):.0%}")

    print("\n■ 가격 다이얼(§15 능동 레버) → 소각률  ※ WAT 환율은 안 건드림")
    for m in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        sr = sink_rate(apply_price_dial(DEFAULT_CATALOG, m), budget)
        print(f"   가격 ×{m:<4}  sink_rate = {sr:.0%}")

    print("\n■ 소각률을 경제 모델에 주입 → 환율 안정화")
    try:
        from economy_simulator import Inputs, simulate
        from dataclasses import replace
        for label, cat in (("빈약", list(sparse)), ("기본", DEFAULT_CATALOG), ("풍부", rich)):
            sr = sink_rate(cat, budget)
            df = simulate(replace(Inputs(), sink_rate=sr))
            print(f"   {label} 상점(sink {sr:.0%}) → Y1 환율 {df['implied_rate']['Y1']:.0f} Spark/WAT "
                  f"· 유저 월$ {df['user_monthly_usd']['Y1']:.2f}(불변)")
    except Exception as e:
        print(f"   (economy_simulator 연동 스킵: {e})")
    print("\n※ 소각을 늘리면 환율(Spark/WAT)만 안정화, 유저 달러 풀은 불변(§10).")
