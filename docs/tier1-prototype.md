# Tier 1 프로토타입 — 스펙

> **목적**: 최소 빌드로 **실제 CPQ 숫자**를 뽑는다(§9 최대 리스크 · `cpq-validation.md` Tier 1).
> 게임을 만드는 게 아니라 **측정 장치**를 만든다. 측정 두뇌: `tier1_metrics.py`(80 테스트 중 10).

## 1. 범위 (딱 이만큼만)

- **미니 비행기 슈팅 1스테이지** — 60초 코어 루프 1회.
- 루프: 시작 10초 후 업그레이드 개방 → **부품 스캔** N회(수익 소스 연동) → 업그레이드 → **보스** → 클리어 시 **Spark 보상**.
- 그 이상(10스테이지·행성 이동·펫/조종사·본편 게임)은 **범위 밖** (C3, "나중에 똑디").

## 2. 두 개의 빌드 — 혼동 금지

| 빌드 | 광고 | 산출 | 용도 |
|---|---|---|---|
| **① 루프 데모** (`tier1-prototype.html`) | **모의(simulated)** 수익 | CPQ "숫자"는 **가짜** | UX·루프·부품스캔·Spark 흐름 시연. 투자자/팀 데모 |
| **② 계측 빌드** | **실 rewarded/offerwall SDK** | **진짜 CPQ** | 실측. `tier1_metrics.analyze()`에 실 텔레메트리 투입 |

> 데모의 CPQ는 시뮬레이션이다 — **실 SDK를 붙이기 전까지 진짜 CPQ가 아니다.** 진짜 숫자는 ②에서만 나온다.

## 3. 측정 계획

### 텔레메트리 (퀘스트당 `QuestOutcome`)
`session_id · completed · parts_scans_requested · parts_scans_filled · ad_revenue_usd · trust(Signals)`

### 핵심 지표 (`tier1_metrics.Tier1Report`)
- **honest_cpq** ← 진짜 숫자: 광고 매출 ÷ **진성 인간** 완료 수 (봇은 `trust_score`로 제외).
- gross_cpq(봇 포함, 비교용) · completion_rate · fill_rate · bot_completion_rate.

### 판정 게이트 (honest_cpq 기준, `cpq_model` 임계값과 동일)
```
< $0.0082           → BROKEN   (재설계/피벗)
$0.0082 ~ $0.0300   → GAME     ("용돈이 아니라 게임" — §8대로 진행)
≥ $0.0300           → BUSINESS (수익성 부각, 규제·포지셔닝 재검토)
```

## 4. 계측 빌드(②) 기술 스택

- 클라이언트: 모바일 우선(§12). Unity 또는 웹(경량). 코어 루프만.
- **미디에이션**: rewarded + offerwall SDK **2–3개**(AppLovin MAX / LevelPlay 등) → `ad_mediation` 모델의 `base_ecpm`·`per_source_fill`을 실측으로 교체.
- **안티봇**: 세션마다 `trust_score` 신호 수집 → honest_cpq를 진성 완료 위에서만 집계. `bot_filtered_rate` 노출(§11).
- 서버: 텔레메트리 수집 → `tier1_metrics.analyze()` 배치 → 판정 대시보드.

## 5. 성공/중단 기준

- **성공(최소)**: honest_cpq ≥ $0.0082 관측 → 모델 성립, 다음 단계.
- **강한 성공**: honest_cpq가 목표 $0.03 근접/초과 → 멀티유닛·tier-1 레버(A4·A6)로 도달 확인.
- **중단**: 실 SDK·미디에이션·멀티유닛 다 얹어도 < $0.0082 → 이코노미 파라미터(배분율·유닛 수) 재설계 or 피벗.

## 6. 컴플라이언스 (§ ad-mediation)

부품 스캔은 **시청 완료(rewarded)·액션(offerwall)·직판**에만 기댄다. **표준 CPC 클릭 보상 금지**(무효 트래픽·밴).
유저 화면에 "광고/Ads/시청" 표현 금지(규칙 4) → "부품 스캔 / 에너지 코어".

## 7. 다음

1. 루프 데모(①) 플레이 확인 → UX·부품스캔·Spark 흐름 검증. ✅ `tier1-prototype.html`
2. 계측 빌드(②) 스코프 확정 + SDK 계정 준비.
3. 실측 → `ad_mediation`·`economy_simulator` 보정 → 투자자 덱 §07 갱신.
