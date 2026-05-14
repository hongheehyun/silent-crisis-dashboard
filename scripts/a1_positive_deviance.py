# -*- coding: utf-8 -*-
"""
A1: 긍정적 이탈자 분석 (Positive Deviance Analysis)
- Step 1: GDP 4분위별 학습빈곤 분포 (박스플롯)
- Step 2: GDP 단일변수 회귀 → 잔차 계산 → 이탈자 식별
- Step 3: 이탈자 vs 비이탈자 Mann-Whitney U + Effect Size (9개 변수)
- Step 4: 긍정적 이탈자 TOP 5 케이스 스터디 산점도

※ VIF 점검 결과 반영 (변수 선별 옵션 A):
  - 제거: F4(발육부진·N1과 r=0.867), F5(인터넷·N3과 r=0.817),
          F6(순등록률·VIF=291), F8(성비·VIF=302), G1~G3(서로 r=0.93~0.96)
  - 유지: F2, F3, F7, N1, N2, N3, N4, N5, G_AVG (총 9개 비교변수)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.linear_model import LinearRegression
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ── 경로 설정 ──────────────────────────────────────────────────
DATA_PATH = '../data/processed/analysis_ready_v2.csv'
IMG_DIR   = '../images/'
OUT_CSV   = '../data/processed/a1_deviance_results.csv'

# ── 컬러 팔레트 ─────────────────────────────────────────────────
C_POS  = '#2ecc71'   # 긍정적 이탈자
C_NEG  = '#e74c3c'   # 부정적 이탈자
C_MID  = '#95a5a6'   # 중간 집단
C_MAIN = '#2c3e50'

# ── VIF 결과 반영: 최종 비교 변수 9개 ──────────────────────────
COMPARE_VARS = {
    'F2_Gov_Edu_Exp'          : '교육지출(%GDP)',
    'F3_Pupil_Teacher_Ratio'  : '교사-학생 비율',
    'F7_Completion_Rate'      : '초등 수료율(%)',
    'N1_Under5_Mortality'     : '유아 사망률',
    'N2_Adolescent_Fertility' : '10대 출산율',
    'N3_Electricity_Access'   : '전기 보급률(%)',
    'N4_Physicians_per_1000'  : '의사 수(1000명당)',
    'N5_Child_Marriage_Female': '여성 조혼율(%)',
    'G_AVG_Governance'        : '거버넌스 지수(WGI)',
}

def cohens_d(group1, group2):
    """Cohen's d 효과 크기 계산"""
    n1, n2 = len(group1), len(group2)
    pooled_std = np.sqrt(((n1-1)*np.std(group1, ddof=1)**2 + (n2-1)*np.std(group2, ddof=1)**2) / (n1+n2-2))
    if pooled_std == 0:
        return 0
    return (np.mean(group1) - np.mean(group2)) / pooled_std

# ── 데이터 로드 ──────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
print(f"데이터 로드: {df.shape[0]}개국 × {df.shape[1]}개 컬럼")

# ══════════════════════════════════════════════════════════════
# STEP 1: GDP 4분위별 학습빈곤 분포 (박스플롯)
# ══════════════════════════════════════════════════════════════
print("\n[Step 1] GDP 4분위 슬라이싱...")

df['GDP_Quartile'] = pd.qcut(df['F1_GDP_per_capita'], q=4,
    labels=['Q1\n(최저소득)', 'Q2\n(저소득)', 'Q3\n(중소득)', 'Q4\n(고소득)'])

quartile_stats = df.groupby('GDP_Quartile', observed=True)['Learning_Poverty'].agg(
    ['mean', 'median', 'std', 'count']).round(2)
print(quartile_stats)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 박스플롯
palette = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71']
bp = df.boxplot(column='Learning_Poverty', by='GDP_Quartile', ax=axes[0],
                patch_artist=True, return_type='dict')
for patch, color in zip(bp['Learning_Poverty']['boxes'], palette):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
axes[0].set_title('GDP 분위별 학습 빈곤율 분포', fontsize=12)
axes[0].set_xlabel('GDP 분위')
axes[0].set_ylabel('학습 빈곤율 (%)')
axes[0].set_ylim(0, 105)
plt.sca(axes[0])
plt.title('GDP 분위별 학습 빈곤율 분포', fontsize=12)

# IQR 범위 (분위 내 편차) — 개선 여지 시각화
iqr_data = df.groupby('GDP_Quartile', observed=True)['Learning_Poverty'].apply(
    lambda x: x.quantile(0.75) - x.quantile(0.25))
axes[1].bar(['Q1\n(최저소득)', 'Q2\n(저소득)', 'Q3\n(중소득)', 'Q4\n(고소득)'],
            iqr_data.values, color=palette, alpha=0.8, edgecolor='white')
axes[1].set_title('GDP 분위별 학습빈곤 IQR\n(=분위 내 편차, 클수록 개선 여지 큼)', fontsize=12)
axes[1].set_xlabel('GDP 분위')
axes[1].set_ylabel('IQR (75th - 25th percentile)')
for i, v in enumerate(iqr_data.values):
    axes[1].text(i, v + 0.5, f'{v:.1f}%p', ha='center', fontsize=11, fontweight='bold')

plt.suptitle('')
plt.tight_layout()
plt.savefig(IMG_DIR + 'a1_gdp_quartile_boxplot.png', dpi=200)
plt.close()
print("[저장] a1_gdp_quartile_boxplot.png")

# ══════════════════════════════════════════════════════════════
# STEP 2: GDP 단일변수 회귀 → 잔차 계산 → 이탈자 식별
# ══════════════════════════════════════════════════════════════
print("\n[Step 2] 잔차 모델 구축 및 이탈자 식별 (log-GDP 기준)...")

# log(GDP) 사용 — 비선형 관계 보정 (MAE 18.5%p→12.9%p, CV R² ±0.183→±0.039)
df['log_GDP'] = np.log(df['F1_GDP_per_capita'])
X_log = df[['log_GDP']].values
y     = df['Learning_Poverty'].values

model_gdp = LinearRegression()
model_gdp.fit(X_log, y)
df['LP_Predicted_by_GDP'] = model_gdp.predict(X_log)
df['Residual'] = df['Learning_Poverty'] - df['LP_Predicted_by_GDP']

r2   = model_gdp.score(X_log, y)
mae  = np.mean(np.abs(df['Residual']))
from sklearn.model_selection import cross_val_score
cv   = cross_val_score(LinearRegression(), X_log, y, cv=5, scoring='r2')
print(f"  log-GDP 모델 R²={r2:.3f}, MAE={mae:.2f}%p, CV R²={cv.mean():.3f}±{cv.std():.3f}")

# 이탈자 분류 (잔차 기준 하위/상위 20%)
threshold_low  = df['Residual'].quantile(0.20)   # 긍정적 이탈자 기준
threshold_high = df['Residual'].quantile(0.80)   # 부정적 이탈자 기준

df['Deviance_Group'] = 'Middle'
df.loc[df['Residual'] <= threshold_low,  'Deviance_Group'] = 'Positive'
df.loc[df['Residual'] >= threshold_high, 'Deviance_Group'] = 'Negative'

pos_group = df[df['Deviance_Group'] == 'Positive']
neg_group = df[df['Deviance_Group'] == 'Negative']
mid_group = df[df['Deviance_Group'] == 'Middle']

print(f"  긍정적 이탈자: {len(pos_group)}개국")
print(f"  부정적 이탈자: {len(neg_group)}개국")
print(f"  중간 집단:     {len(mid_group)}개국")

# 잔차 산점도 (이탈자 하이라이트)
fig, ax = plt.subplots(figsize=(12, 7))

color_map = {'Positive': C_POS, 'Negative': C_NEG, 'Middle': C_MID}
for group, color in color_map.items():
    sub = df[df['Deviance_Group'] == group]
    ax.scatter(sub['log_GDP'], sub['Learning_Poverty'],
               color=color, alpha=0.75, s=60, zorder=3,
               label={'Positive': f'긍정적 이탈자 (n={len(sub)})',
                      'Negative': f'부정적 이탈자 (n={len(sub)})',
                      'Middle'  : f'중간 집단 (n={len(sub)})'}[group])

# log-GDP 회귀선
x_line = np.linspace(df['log_GDP'].min(), df['log_GDP'].max(), 200)
y_line = model_gdp.predict(x_line.reshape(-1, 1))
ax.plot(x_line, y_line, color=C_MAIN, linewidth=2, linestyle='--',
        label=f'log-GDP 회귀선 (R²={r2:.2f}, MAE={mae:.1f}%p)')

# 국가명 레이블 (긍정적 이탈자 TOP 7)
top_pos = pos_group.nsmallest(7, 'Residual')
for _, row in top_pos.iterrows():
    ax.annotate(row['Country_Name'],
                xy=(row['log_GDP'], row['Learning_Poverty']),
                xytext=(8, 4), textcoords='offset points',
                fontsize=7.5, color='#1a7a3f', fontweight='bold')

ax.set_xlabel('log(1인당 GDP)', fontsize=11)
ax.set_ylabel('학습 빈곤율 (%)', fontsize=11)
ax.set_title('log-GDP vs 학습 빈곤율 — 긍정적/부정적 이탈자 식별\n(잔차 기준 상·하위 20%, log-GDP 모델 적용)', fontsize=13)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(IMG_DIR + 'a1_residual_scatter.png', dpi=200)
plt.close()
print("[저장] a1_residual_scatter.png")

# ══════════════════════════════════════════════════════════════
# STEP 3: 이탈자 vs 비이탈자 Mann-Whitney U + Effect Size
# ══════════════════════════════════════════════════════════════
print("\n[Step 3] Mann-Whitney U 검정 + Cohen's d (9개 변수)...")

results = []
for col, label in COMPARE_VARS.items():
    pos_vals = pos_group[col].dropna().values
    oth_vals = df[df['Deviance_Group'] != 'Positive'][col].dropna().values

    stat, p_val = stats.mannwhitneyu(pos_vals, oth_vals, alternative='two-sided')
    d = cohens_d(pos_vals, oth_vals)
    results.append({
        'Variable'   : col,
        'Label'      : label,
        'Pos_Mean'   : round(pos_vals.mean(), 3),
        'Others_Mean': round(oth_vals.mean(), 3),
        'Diff'       : round(pos_vals.mean() - oth_vals.mean(), 3),
        'Cohen_d'    : round(d, 3),
        'p_value'    : round(p_val, 4),
        'Significant': '✅' if p_val < 0.05 else '❌'
    })

results_df = pd.DataFrame(results).sort_values('Cohen_d', key=abs, ascending=False)
print(results_df[['Label', 'Pos_Mean', 'Others_Mean', 'Cohen_d', 'p_value', 'Significant']].to_string(index=False))

# Effect Size 수평 바 차트
fig, ax = plt.subplots(figsize=(11, 7))

colors = []
for _, row in results_df.iterrows():
    if row['p_value'] < 0.05:
        colors.append(C_POS if row['Cohen_d'] < 0 else C_NEG)
    else:
        colors.append('#bdc3c7')

bars = ax.barh(results_df['Label'], results_df['Cohen_d'], color=colors, alpha=0.85, edgecolor='white', height=0.6)
ax.axvline(x=0, color=C_MAIN, linewidth=1.5)
ax.axvline(x=0.5,  color='orange', linewidth=1, linestyle=':', alpha=0.7, label='중간 효과 (d=0.5)')
ax.axvline(x=-0.5, color='orange', linewidth=1, linestyle=':', alpha=0.7)
ax.axvline(x=0.8,  color='red', linewidth=1, linestyle=':', alpha=0.5, label='큰 효과 (d=0.8)')
ax.axvline(x=-0.8, color='red', linewidth=1, linestyle=':', alpha=0.5)

for bar, (_, row) in zip(bars, results_df.iterrows()):
    sig_mark = '★' if row['p_value'] < 0.05 else ''
    ax.text(bar.get_width() + (0.02 if bar.get_width() >= 0 else -0.02),
            bar.get_y() + bar.get_height()/2,
            f'{row["Cohen_d"]:+.2f} {sig_mark}  p={row["p_value"]:.3f}',
            va='center', ha='left' if bar.get_width() >= 0 else 'right', fontsize=8.5)

ax.set_xlabel("Cohen's d  (음수: 긍정적 이탈자에서 낮음, 양수: 높음)", fontsize=10)
ax.set_title("긍정적 이탈자 vs 나머지 집단 — 변수별 Effect Size\n(★ p<0.05 유의)", fontsize=13)
ax.legend(fontsize=9, loc='lower right')
ax.grid(True, axis='x', alpha=0.3)

patch_pos = mpatches.Patch(color=C_POS, alpha=0.85, label='긍정 이탈자에서 낮음 (유리)')
patch_neg = mpatches.Patch(color=C_NEG, alpha=0.85, label='긍정 이탈자에서 높음 (불리)')
patch_ns  = mpatches.Patch(color='#bdc3c7', alpha=0.85, label='비유의 (p≥0.05)')
ax.legend(handles=[patch_pos, patch_neg, patch_ns], fontsize=8.5, loc='lower right')

plt.tight_layout()
plt.savefig(IMG_DIR + 'a1_deviant_factor_comparison.png', dpi=200)
plt.close()
print("[저장] a1_deviant_factor_comparison.png")

# ══════════════════════════════════════════════════════════════
# STEP 4: 긍정적 이탈자 TOP 5 레이더 차트
# ══════════════════════════════════════════════════════════════
print("\n[Step 4] 긍정적 이탈자 TOP 5 레이더 차트...")

top5 = pos_group.nsmallest(5, 'Residual')[
    ['Country_Name', 'Learning_Poverty', 'LP_Predicted_by_GDP', 'Residual'] + list(COMPARE_VARS.keys())
].copy()

print("\n=== 긍정적 이탈자 TOP 5 ===")
print(top5[['Country_Name', 'Learning_Poverty', 'LP_Predicted_by_GDP', 'Residual']].to_string(index=False))

# 레이더 차트용: 유의한 변수만 선별
sig_vars = results_df[results_df['p_value'] < 0.05].head(6)
radar_cols  = sig_vars['Variable'].tolist()
radar_labels = sig_vars['Label'].tolist()

if len(radar_cols) >= 3:
    # 정규화 (0~1)
    radar_df = top5.copy()
    for col in radar_cols:
        col_min = df[col].min()
        col_max = df[col].max()
        if col_max > col_min:
            radar_df[col] = (radar_df[col] - col_min) / (col_max - col_min)
        # 방향 통일: 높을수록 좋음으로 (유아사망률, 출산율 등은 낮을수록 좋음 → 반전)
        bad_direction = ['N1_Under5_Mortality', 'N2_Adolescent_Fertility',
                         'N5_Child_Marriage_Female', 'F3_Pupil_Teacher_Ratio']
        if col in bad_direction:
            radar_df[col] = 1 - radar_df[col]

    N = len(radar_cols)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    palette_radar = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']

    # 전체 평균 기준선
    avg_vals = [df[col].mean() for col in radar_cols]
    avg_norm = []
    for i, col in enumerate(radar_cols):
        v = (avg_vals[i] - df[col].min()) / (df[col].max() - df[col].min() + 1e-9)
        if col in ['N1_Under5_Mortality', 'N2_Adolescent_Fertility',
                   'N5_Child_Marriage_Female', 'F3_Pupil_Teacher_Ratio']:
            v = 1 - v
        avg_norm.append(v)
    avg_norm += avg_norm[:1]
    ax.plot(angles, avg_norm, color='gray', linewidth=1.5, linestyle='--', label='전체 평균', alpha=0.6)
    ax.fill(angles, avg_norm, color='gray', alpha=0.05)

    for i, (_, row) in enumerate(top5.iterrows()):
        vals = [radar_df.loc[row.name, col] for col in radar_cols]
        vals += vals[:1]
        ax.plot(angles, vals, color=palette_radar[i], linewidth=2, label=row['Country_Name'])
        ax.fill(angles, vals, color=palette_radar[i], alpha=0.08)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(radar_labels, fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_title('긍정적 이탈자 TOP 5 — 유의 성공요인 레이더\n(값이 클수록 학습빈곤에 유리한 방향)', fontsize=12, pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
    plt.tight_layout()
    plt.savefig(IMG_DIR + 'a1_success_country_radar.png', dpi=200)
    plt.close()
    print("[저장] a1_success_country_radar.png")
else:
    print("  유의한 변수 부족 — 레이더 차트 건너뜀")

# ── 결과 CSV 저장 ──────────────────────────────────────────────
df.to_csv(OUT_CSV.replace('.csv', '_full.csv'), index=False)
results_df.to_csv(OUT_CSV, index=False)
print(f"[저장] a1_deviance_results.csv")

# ── 최종 요약 출력 ──────────────────────────────────────────────
print("\n" + "="*60)
print("=== A1 분석 완료 요약 ===")
print(f"  GDP 회귀 R²:        {r2:.3f}")
print(f"  긍정적 이탈자:      {len(pos_group)}개국")
print(f"  유의한 성공요인:    {(results_df['p_value'] < 0.05).sum()}개 / 9개")
print("\n  [성공요인 순위 (|Cohen's d| 기준, p<0.05)]")
sig = results_df[results_df['p_value'] < 0.05].copy()
for _, row in sig.iterrows():
    direction = '↓낮음' if row['Cohen_d'] < 0 else '↑높음'
    print(f"    {row['Label']}: d={row['Cohen_d']:+.2f} ({direction}) p={row['p_value']:.4f}")
print("="*60)
