# 광고 수익화 소스 카탈로그 — "할 수 있는 건 다"

> **목적**: `ad-mediation.md`(A6)의 모델을 **실제 벤더 지형**으로 확장. QuestFi가 붙일 수 있는 모든
> 수익화 소스를 계층별로 정리하고, 인센티브 컴플라이언스와 CPQ 매핑을 명시한다.
> ⚠️ 시장 점유율·eCPM·소유 관계는 2026 업계 리포트 기준 — 연동 시점에 재확인. 벤더 통폐합이 잦다.

## 0. 원칙 (§ad-mediation 재확인)

- QuestFi는 **단일 네트워크에 종속되지 않는다.** 미디에이션 위에 최대한 많은 수요를 경쟁시킨다.
- **인센티브는 시청(rewarded)·액션(offerwall)·직판에만.** 표준 CPC 클릭 보상은 정책 위반·밴(§규칙 4 아님, 무효 트래픽).
- 소스를 겹칠수록 **fill·eCPM이 오른다**(모델 검증 + 업계 데이터: 오퍼월 2개 레이어 = ARPDAU +30~50%).

## 1. Layer 1 — 미디에이션 플랫폼 (이 위에 다 얹는다)

우리가 **하나를 골라 그 위에 모든 네트워크를 경쟁**시킨다. 실시간 인앱 비딩이 핵심.

| 플랫폼 | 특징 | 비고 |
|---|---|---|
| **AppLovin MAX** ⭐ | 최고 eCPM 다수, 2026 Q1 iOS 광고매출 39% 점유. 실시간 비딩 | Tier-1·rewarded/플레이어블 강세 |
| **Unity LevelPlay** (ex-ironSource) ⭐ | 게임 특화, 상위 미국 게임 ~88% 사용, 2.5B MAU. 하이브리드 비딩 | ironSource·Unity Ads·Tapjoy 한 우산 |
| **Google AdMob (mediation)** | 안드 28% 점유, 안정적 fill, 다포맷 | 구글 수요 접근 |
| **Digital Turbine FairBid** | Fyber 계열 미디에이션 | 오퍼월과 묶기 좋음 |

> **권고**: **AppLovin MAX 또는 Unity LevelPlay를 1차 미디에이션**으로. 둘 다 in-app bidding으로 아래 네트워크들을 자동 경쟁시킴.

## 2. Layer 2 — Rewarded Video 네트워크 (부품 스캔 1차 소스)

opt-in·완료율 높음. **eCPM $10–50**(Tier-1), 앱 매출 +20~40%. 미디에이션에 demand로 연결.

| 네트워크 | 단위 | 비고 |
|---|---|---|
| **AppLovin** | CPCV/eCPM | 최상위 eCPM |
| **Unity Ads** | CPCV | 게임 rewarded·플레이어블 강세 |
| **Google AdMob** | CPCV | 광범위 fill |
| **Meta Audience Network** | 비딩 | 강한 타깃팅 수요 |
| **Mintegral (Mobvista)** | CPCV | 아시아·퍼포먼스 강세 |
| **Liftoff (Vungle)** | CPCV | 비디오 특화 |
| **Pangle (ByteDance/TikTok)** | CPCV | 대규모 글로벌 수요 |
| **InMobi · Chartboost · Smadex** | CPCV/CPM | 보조 demand 다변화 |

## 3. Layer 3 — Offerwall / CPE / Playtime ★ 최고 가치 레버 (액션 완료)

**퀘스트 = 액션 완료** 구조의 핵심. 유저가 설치·구독·플레이 등 액션을 완료하면 광고주가 지불.
**오퍼월 유저는 rewarded-only 대비 체류 4배·ARPDAU 3~8배.** CPQ를 목표 위로 밀어올리는 지점.

| 제공자 | 모델 | 비고 |
|---|---|---|
| **Tapjoy** (Unity) ⭐ | CPA/CPE (설치·구독·인앱) | 가장 성숙, 글로벌 수요 |
| **ironSource Offerwall** (Unity) ⭐ | CPA/CPE | Tapjoy와 레이어링 시 ARPDAU +30~50% |
| **Adjoe — Playtime** ⭐ | **CPE·플레이타임** (체류 기반 보상) | 딥 인게이지 유저 유입, QuestFi 결에 최적 |
| **Fyber Offerwall (Digital Turbine)** | CPA | DT 생태계 |
| **BitLabs · ayeT-Studios · TyrAds · Pubscale** | CPA/설문/오퍼 | 다변화·보조 |

> **경제**: 오퍼월 CPI 예시 = 광고주 $3.50, 네트워크 30~40% 수취, 퍼블리셔 순 $2.10~2.45/전환.
> CPQ 관점: 퀘스트당 매출 ≈ **CPA × 전환율**(`cpq_model.cpq_from_cpa`) — 전환 몇 %만 나와도 목표 $0.03을 넘길 수 있는 유일한 레버.

## 4. Layer 4 — Playable / Interactive

인터랙티브 플레이어블(미니 체험). 완료율·eCPM 높음. AppLovin·Unity·Mintegral가 강함. "부품 스캔"을
플레이어블로 감싸면 게임 결과 자연스럽게 어울림(광고 느낌 최소화, §12).

## 5. Layer 5 — Programmatic / Exchange (비인센, 배경 노출)

DSP/SSP·오픈 익스체인지 (Google AdX, Magnite, PubMatic, AppLovin ALX 등). **인센티브 없이** 배경
노출/네이티브로. **클릭 유도 금지.** fill 바닥을 채우는 보조.

## 6. Layer 6 — 직판 CPQ (Tier 2, 우리 상품)

우리 세일즈로 광고주에게 **CPQ를 직접** 판매. 완료 프리미엄(§1 테제)의 상업 검증. 마진 최상, 미디에이션
의존 축소. Tier 1 실측 후 착수.

## 7. 컴플라이언스 매트릭스 — 인센티브 허용 여부

| 소스 | 인센티브 보상 | QuestFi 사용 |
|---|---|---|
| Rewarded video (시청) | ✅ 명시 허용 | 부품 스캔 1차 |
| Offerwall / CPE / Playtime (액션) | ✅ 허용 | 부품 스캔 = 액션, 최고가치 |
| Playable (완료) | ✅ 허용 | 부품 스캔 래핑 |
| 직판 CPQ | ✅ (우리 규칙) | Tier 2 |
| Programmatic 노출 (비인센) | ⚠️ 클릭 유도 금지 | 배경 fill만 |
| **표준 배너/CPC 클릭 보상** | ❌ 정책 위반·밴 | **금지** |

## 8. QuestFi 매핑 — "부품 스캔"이 무엇을 부르나

```
부품 스캔 1회 = { rewarded video 완료  |  offerwall 액션  |  playable 완료 }  중 미디에이션이 최적가로 낙찰
  → 완료당 매출을 CPQ로 정규화 → trust_score 게이트 통과분만 집계 → Spark 지급
```
- **손익분기 돌파** = 멀티소스 rewarded (Layer 2, `ad_mediation.py` 검증).
- **목표 $0.03 돌파** = 오퍼월/CPE 전환(Layer 3) 또는 멀티유닛(A4).

## 9. Tier 1 착수 스택 (권고)

최소로 시작해 실측:
1. **미디에이션 1개**: AppLovin MAX **또는** Unity LevelPlay.
2. **Rewarded 2–3개**: (MAX 기준) AppLovin + Unity Ads + AdMob 자동 비딩.
3. **오퍼월 1–2개**: Tapjoy + Adjoe(Playtime) — 최고가치 레버 실측.
4. 계측: `tier1_metrics`로 소스별 honest CPQ·fill·전환 → `ad_mediation` 상수 보정.

---

## Sources

- [The Game Marketer — Best Ad Networks for Mobile Games 2026](https://www.thegamemarketer.com/insight-posts/top-advertising-networks-for-mobile-gaming-apps)
- [MonetizePros — Highest Paying Ad Networks 2026](https://monetizepros.com/monetization-basics/ad-networks-for-mobile-game-publishers/)
- [Tenjin — Ad Monetization Benchmark Report 2026](https://tenjin.com/blog/ad-mon-gaming-2026/)
- [PubScale — 14 Best Offerwall Ad Networks 2026](https://pubscale.com/blog/offerwall-ad-networks)
- [Unity — Tapjoy Offerwall](https://unity.com/products/tapjoy)
- [MY.GAMES — Offerwalls guide](https://medium.com/my-games-company/offerwalls-a-guide-to-everything-you-ever-wanted-to-know-bd6515860bee)
- [TyrAds — Best Offerwalls 2025](https://tyrads.com/best-offerwalls/)
