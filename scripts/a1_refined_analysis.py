"""
A1 정제 재분석
- 방법 A: 비교 변수도 log-GDP 잔차화 → 진정한 "GDP 독립" 성공요인 탐색
- 방법 B: GDP 분위별 내부 비교 → 직관적 보조 검증
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import matplotlib
import warnings
warnings.filterwarnings('ignore')

matplotlib.rc('font', family='AppleGothic')
matplotlib.rc('axes', unicode_minus=False)

# ── 데이터 로드 ──────────────────────────────────────
df = pd.read_csv('../data/processed/analysis_ready_v2.csv')
df['log_GDP'] = np.log(df['F1_GDP_per_capita'])
print(f"데이터 로드: {len(df)}개국\n")

# ── 긍정적 이탈자 식별 (log-GDP 잔차 기준) ──────────
X_log = df[['log_GDP']].values
y_lp  = df['Learning_Poverty'].values
model_lp = LinearRegression().fit(X_log, y_lp)
df['LP_Residual'] = df['Learning_Poverty'] - model_lp.predict(X_log)

threshold = df['LP_Residual'].quantile(0.20)
df['Is_Pos_Dev'] = df['LP_Residual'] <= threshold
n_pos = df['Is_Pos_Dev'].sum()
print(f"긍정적 이탈자 {n_pos}개국 (잔차 하위 20%)\n")

# ── 분석 대상 변수 (컬럼명 실제 기준) ────────────────
FACTORS = {
    'N1_Under5_Mortality'  : '유아 사망률',
    'N2_Adolescent_Fertility': '10대 출산율',
    'N3_Electricity_Access': '전기 보급률',
    'N4_Physicians_per_1000': '의사 수',
    'N5_Child_Marriage_Female': '여성 조혼율',
    'F2_Gov_Edu_Exp'       : '교육지출(%GDP)',
    'F3_Pupil_Teacher_Ratio': '교사-학생 비율',
    'F7_Completion_Rate'   : '초등 수료율',
    'G_AVG_Governance'     : '거버넌스 지수(WGI)',
}

# ════════════════════════════════════════════════════
# 방법 A: 비교 변수도 log-GDP 잔차화 후 비교
# ════════════════════════════════════════════════════
print("=" * 60)
print("방법 A: 비교 변수도 log-GDP 잔차화 후 Mann-Whitney + Cohen's d")
print("(GDP 효과를 양쪽에서 제거한 '진정한' 성공요인 탐색)")
print("=" * 60)

results_A = []
for col, label in FACTORS.items():
    tmp = df[['log_GDP', col, 'Is_Pos_Dev']].dropna().copy()
    if len(tmp) < 20:
        continue

    # 각 변수도 log-GDP로 잔차화
    m = LinearRegression().fit(tmp[['log_GDP']].values, tmp[col].values)
    tmp[col + '_resid'] = tmp[col] - m.predict(tmp[['log_GDP']].values)

    pos = tmp[tmp['Is_Pos_Dev']][col + '_resid']
    oth = tmp[~tmp['Is_Pos_Dev']][col + '_resid']

    _, p = stats.mannwhitneyu(pos, oth, alternative='two-sided')
    pool_std = np.sqrt(
        ((len(pos)-1)*pos.var(ddof=1) + (len(oth)-1)*oth.var(ddof=1))
        / (len(pos)+len(oth)-2)
    )
    d = (pos.mean() - oth.mean()) / pool_std if pool_std > 0 else 0

    sig = '✅ 유의' if p < 0.05 else ('⚠️ 경향' if p < 0.10 else '❌')
    results_A.append({
        'Label': label, 'Cohen_d': d, 'p_value': p,
        'Pos_Resid_Mean': pos.mean(), 'Oth_Resid_Mean': oth.mean(),
        'Sig': sig
    })
    print(f"  {label:<18}: d={d:+.2f}, p={p:.4f} {sig} "
          f"| 이탈자_잔차={pos.mean():+.1f}, 나머지_잔차={oth.mean():+.1f}")

res_A_df = pd.DataFrame(results_A).sort_values('p_value')

# ════════════════════════════════════════════════════
# 방법 B: GDP 분위별 내부 비교 (보조 검증)
# ════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("방법 B: GDP 분위별 내부 비교 (직관적 보조 검증)")
print("(같은 소득 구간 안에서 이탈자 vs 나머지 비교)")
print("=" * 60)

df['GDP_Q'] = pd.qcut(df['F1_GDP_per_capita'], 4,
                       labels=['Q1\n(최저소득)', 'Q2\n(저소득)',
                               'Q3\n(중소득)', 'Q4\n(고소득)'])

results_B = []
for q_label in ['Q1\n(최저소득)', 'Q2\n(저소득)', 'Q3\n(중소득)', 'Q4\n(고소득)']:
    q_df = df[df['GDP_Q'] == q_label]
    pos_n = q_df['Is_Pos_Dev'].sum()
    oth_n = len(q_df) - pos_n
    print(f"\n--- {q_label.replace(chr(10), ' ')} (이탈자 {pos_n}명 / 나머지 {oth_n}명) ---")

    if pos_n < 3:
        print("  이탈자 수 부족, 검정 생략")
        continue

    for col, label in FACTORS.items():
        tmp = q_df[['Is_Pos_Dev', col]].dropna()
        pos = tmp[tmp['Is_Pos_Dev']][col]
        oth = tmp[~tmp['Is_Pos_Dev']][col]
        if len(pos) < 3 or len(oth) < 3:
            continue

        _, p = stats.mannwhitneyu(pos, oth, alternative='two-sided')
        if p < 0.10:  # 경향성까지 표시
            pool_std = q_df[col].dropna().std()
            d = (pos.mean() - oth.mean()) / pool_std if pool_std > 0 else 0
            sig = '✅' if p < 0.05 else '⚠️(경향)'
            print(f"  {label:<18}: d={d:+.2f}, p={p:.4f} {sig} "
                  f"| 이탈자={pos.mean():.1f}, 나머지={oth.mean():.1f}")
            results_B.append({'Q': q_label, 'Label': label,
                               'Cohen_d': d, 'p_value': p, 'Sig': sig})

# ════════════════════════════════════════════════════
# 시각화: 방법 A 결과 막대 + 방법 B 히트맵
# ════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('A1 정제 재분석: GDP 잔차화 + 분위별 내부 비교', fontsize=14, fontweight='bold')

# ── 방법 A: Cohen's d 막대그래프 ──
ax = axes[0]
sorted_A = res_A_df.sort_values('Cohen_d')
colors = ['#e74c3c' if (p < 0.05) else ('#f39c12' if p < 0.10 else '#95a5a6')
          for p in sorted_A['p_value']]
bars = ax.barh(sorted_A['Label'], sorted_A['Cohen_d'], color=colors, edgecolor='white', height=0.6)
ax.axvline(0, color='black', linewidth=0.8)
ax.axvline( 0.5, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
ax.axvline(-0.5, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
ax.set_xlabel("Cohen's d (양수=이탈자가 더 높음, 음수=더 낮음)", fontsize=10)
ax.set_title("방법 A: 변수 잔차화 후 Cohen's d\n(빨강=p<0.05, 주황=p<0.10, 회색=비유의)", fontsize=11)
for bar, (_, row) in zip(bars, sorted_A.iterrows()):
    ax.text(bar.get_width() + (0.01 if bar.get_width() >= 0 else -0.01),
            bar.get_y() + bar.get_height()/2,
            f"p={row['p_value']:.3f}", va='center',
            ha='left' if bar.get_width() >= 0 else 'right', fontsize=8)
ax.set_xlim(-1.2, 1.2)
ax.grid(axis='x', alpha=0.3)

# ── 방법 B: 분위 × 변수 히트맵 ──
ax = axes[1]
if results_B:
    res_B_df = pd.DataFrame(results_B)
    pivot = res_B_df.pivot_table(index='Label', columns='Q', values='Cohen_d', aggfunc='mean')
    im = ax.imshow(pivot.values, aspect='auto', cmap='RdYlGn', vmin=-1.2, vmax=1.2)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([c.replace('\n', '\n') for c in pivot.columns], fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                        fontsize=9, fontweight='bold',
                        color='white' if abs(val) > 0.6 else 'black')
    plt.colorbar(im, ax=ax, label="Cohen's d")
    ax.set_title("방법 B: GDP 분위별 내부 비교\n(p<0.10인 변수만 표시, 녹색=이탈자 유리)", fontsize=11)
else:
    ax.text(0.5, 0.5, "유의/경향 결과 없음", ha='center', va='center',
            transform=ax.transAxes, fontsize=14)
    ax.set_title("방법 B: GDP 분위별 내부 비교 — 유의 결과 없음", fontsize=11)

plt.tight_layout()
plt.savefig('../images/a1_refined_comparison.png', dpi=150, bbox_inches='tight')
print("\n[저장] a1_refined_comparison.png")

# ── 최종 요약 ──
print("\n" + "=" * 60)
print("=== 최종 요약: 방법 A 유의/경향 변수 ===")
sig_A = res_A_df[res_A_df['p_value'] < 0.10]
if len(sig_A) == 0:
    print("  방법 A: 유의(p<0.05) 또는 경향(p<0.10) 변수 없음")
else:
    for _, r in sig_A.iterrows():
        print(f"  {r['Label']:<18}: d={r['Cohen_d']:+.2f}, p={r['p_value']:.4f} {r['Sig']}")
print("=" * 60)
