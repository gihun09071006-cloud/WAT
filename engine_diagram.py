"""QuestFi 경제 엔진 시각화 → PDF.

지금까지 설계한 엔진 전체(수요 미디에이션 → 매출 분배 → 게임 발행 → Spark 순환 →
소각/상환 → WAT, + 안티봇 게이트 · Redemption Epoch · 인플레 제어)를 한 장으로.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# --- Korean font ---
fp = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
fpb = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
fm.fontManager.addfont(fp); fm.fontManager.addfont(fpb)
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

# --- palette ---
INK = "#0E131C"; PANEL = "#182130"; LINE = "#2E3A4D"
TEXT = "#EAECF2"; SOFT = "#9AA2B4"
GOLD = "#E8B44A"; TEAL = "#3FD3C6"; CORAL = "#E5735B"; VIOLET = "#9B8CFF"

fig, ax = plt.subplots(figsize=(16, 10.5))
fig.patch.set_facecolor(INK); ax.set_facecolor(INK)
ax.set_xlim(0, 160); ax.set_ylim(0, 105); ax.axis("off")

def box(x, y, w, h, title, lines, edge=LINE, tcolor=TEXT, fc=PANEL, title_c=None, fs=10):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.4",
                       linewidth=1.6, edgecolor=edge, facecolor=fc, zorder=2)
    ax.add_patch(p)
    ax.text(x + w/2, y + h - 3.4, title, ha="center", va="top",
            fontsize=fs+1, fontweight="bold", color=title_c or tcolor, zorder=3)
    if lines:
        ax.text(x + w/2, y + h - 8.2, "\n".join(lines), ha="center", va="top",
                fontsize=fs-1.5, color=SOFT, zorder=3, linespacing=1.5)

def arrow(x1, y1, x2, y2, color=GOLD, style="-|>", lw=2.2, rad=0.0, ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
                        linewidth=lw, color=color, zorder=1,
                        connectionstyle=f"arc3,rad={rad}", linestyle=ls)
    ax.add_patch(a)

def label(x, y, t, color=SOFT, fs=8.5, style="italic", weight="normal", ha="center"):
    ax.text(x, y, t, ha=ha, va="center", fontsize=fs, color=color, style=style, fontweight=weight, zorder=4)

# ===== title =====
ax.text(3, 101, "QuestFi — 경제 엔진", fontsize=22, fontweight="bold", color=TEXT)
ax.text(3, 96.5, "광고 매출을 게임 보상으로: 검증된 퀘스트 완료(CPQ) → Spark → 월간 상환 → WAT.  발행 아닌 매출 지급.",
        fontsize=10.5, color=SOFT)
ax.plot([3, 157], [93.5, 93.5], color=LINE, lw=1)

# ===== ZONE A: 수요 (광고 미디에이션) — top-left =====
label(3, 89.5, "① 수요 — 광고 미디에이션", color=GOLD, fs=11, style="normal", weight="bold", ha="left")
box(3, 68, 34, 19, "광고 수요 소스", [
    "Rewarded 시청 · Offerwall 액션",
    "Playable · Programmatic · 직판 CPQ",
    "→ 경쟁 입찰로 최적가 낙찰",
], edge=GOLD, title_c=GOLD)
label(20, 65.5, "인센티브 = 시청·액션만 (클릭보상 X)", color=SOFT, fs=8)

# ===== ZONE B: 광고주 법정화폐 분배 — top-center =====
box(46, 70, 30, 17, "광고주 법정화폐 100%", [
    "카드·인보이스 (토큰 안 만짐)",
    "운영사 100% 수령",
], edge=TEAL, title_c=TEAL)
box(83, 80, 34, 7, "① 운영 40%", [], edge=LINE, fc="#141b28", fs=9)
box(83, 71, 34, 7, "② 보상 재원 40%", [], edge=GOLD, title_c=GOLD, fs=9)
box(83, 62, 34, 7, "③ 생태계 기금 20%", [], edge=LINE, fc="#141b28", fs=9)
arrow(76, 81, 83, 83.5, color=SOFT); arrow(76, 79, 83, 74.5, color=GOLD); arrow(76, 76, 83, 65.5, color=SOFT)

# ===== ZONE C: DEX LP / 바이백 → WAT 풀 =====
box(123, 63, 34, 22, "DEX LP · WAT 풀", [
    "월 1회 유동성 공급",
    "USDC = 광고매출",
    "WAT = 생태계기금 (신규발행 X)",
    "매출↑ → 풀 깊이↑ → 슬리피지↓",
], edge=TEAL, title_c=TEAL)
arrow(117, 74.5, 123, 73, color=GOLD)
label(120, 77, "40%", color=GOLD, fs=9, style="normal", weight="bold")

# ===== ZONE D: 게임 루프 (Faucet) — mid-left =====
label(3, 61, "② 발행 — 게임 루프 (Faucet)", color=TEAL, fs=11, style="normal", weight="bold", ha="left")
box(3, 40, 34, 18, "비행기 슈팅 · 부품 스캔", [
    "플레이 → 부품 스캔(검증된 완료)",
    "보스 클리어 → Spark 지급",
    "배율(Lv·길드·펫·패스) = 획득량만",
], edge=TEAL, title_c=TEAL)
arrow(20, 68, 20, 58, color=GOLD)         # demand -> game (ads served in scan)
label(28, 63, "부품 스캔 = 광고 서빙", color=SOFT, fs=8)

# Spark node
box(46, 44, 24, 12, "Spark", ["인앱 재화 · 캡 없음", "시즌 스코프"], edge=GOLD, title_c=GOLD, fs=11)
arrow(37, 49, 46, 50, color=GOLD)

# ===== ZONE E: Spark 순환 — 소각 vs 상환 =====
label(80, 59.5, "③ 순환 — 소각 · 상환 (§15)", color=GOLD, fs=11, style="normal", weight="bold", ha="left")
# sink
box(80, 44, 33, 12, "소각 — 상점(Sink)", [
    "비행기·조종사·펫·코스메틱",
    "구매 시 소각 · 인플레 완충 다이얼",
], edge=VIOLET, title_c=VIOLET)
arrow(70, 51, 80, 50, color=VIOLET)
label(75, 53.5, "소비", color=VIOLET, fs=8)
# anti-bot gate + redemption
box(80, 27, 33, 13, "안티봇 신뢰도 게이트", [
    "봇 Spark는 상환 풀에 못 들어옴",
    "출구(월 상환)만 차단, 플레이는 허용",
], edge=CORAL, title_c=CORAL)
arrow(58, 44, 90, 40, color=GOLD, rad=-0.15)
label(66, 40.5, "상환 신청", color=GOLD, fs=8)

# ===== ZONE F: Redemption Epoch (환율) =====
box(123, 30, 34, 20, "Redemption Epoch (월간)", [
    "P = (매출×40%) ÷ WAT 시장가",
    "S = 상환 신청 Spark (봇 제외)",
    "환율 = P ÷ S",
    "← 발표 아닌 결과 (사후 공개)",
], edge=GOLD, title_c=GOLD)
arrow(113, 33.5, 123, 35, color=CORAL)     # gated spark -> epoch
arrow(140, 63, 140, 50, color=TEAL)        # WAT pool -> epoch (P)
label(146, 56.5, "P (WAT)", color=TEAL, fs=8)

# ===== ZONE G: WAT =====
box(123, 8, 34, 16, "WAT — 온체인 자산", [
    "10억 고정 · 보상용 발행 영구금지",
    "부트스트랩 6%만(Y3=0)",
    "거래소 시장가 존재",
], edge=TEAL, title_c=TEAL)
arrow(140, 30, 140, 24, color=GOLD)
label(148, 27, "유저 WAT 수령", color=GOLD, fs=8)

# ===== ZONE H: 방화벽 (랜덤 경로) — bottom-left =====
box(3, 8, 52, 20, "방화벽 (§5) — 랜덤 경로는 절대 교차 안 함", [
    "체스트 · Lucky Wheel  →  NFT·코스메틱·XP·배율·칭호",
    "※ Spark 지급 안 함 · 영구 상환 불가",
    "확정 경로(위)와 분리: 랜덤+환전 = 사행성 차단",
], edge=CORAL, title_c=CORAL, fs=9.5)

# ===== guardrail strip — bottom-center =====
box(60, 8, 55, 16, "절대 규칙 (엔진에 코드로 강제)", [
    "① 보상=매출 지급(발행 아님)   ② 랜덤보상 환전불가",
    "③ 환율 사전발표 금지(페그 X)   ④ 광고표현 금지→'부품 스캔'",
    "⑤ 시세조종 금지   · 완충 다이얼은 소각에, 환율 X",
], edge=LINE, title_c=SOFT, fs=9)

# §10 invariant — clean callout in the open left-middle band
box(3, 30.5, 52, 8, "핵심 불변식 (§10)", [
    "유저 실질 달러 = (광고매출 × 40%) ÷ S   — WAT 가격 무관",
    "소각↑ → 환율(Spark/WAT)만 안정, 유저 달러 풀 불변",
], edge=TEAL, title_c=TEAL, fs=9.5)

# footer
ax.text(3, 3.2, "내부 설계 · 약속 아님 · 파라미터 조정 가능   |   모델: economy·redemption·dex·cpq·trust·mediation·sink (테스트 103)",
        fontsize=8, color=SOFT)

plt.tight_layout()
out = "/home/user/WAT/docs/engine-diagram.pdf"
fig.savefig(out, facecolor=INK, bbox_inches="tight", pad_inches=0.3)
print("saved", out)
