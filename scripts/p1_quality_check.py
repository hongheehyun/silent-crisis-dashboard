# -*- coding: utf-8 -*-
"""
Phase 1 품질 점검 스크립트
1. N1~N5 + F1~F8 + G1~G3 간 다중공선성 히트맵 + VIF 점검
2. Imputation 전후 분포 비교 KDE Plot (N5 조혼율 중심)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = '../'
DATA_V2  = '../data/processed/analysis_ready_v2.csv'
DATA_V1  = '../data/processed/analysis_ready.csv'
IMG_DIR  = '../images/'

# ── 1. 데이터 로드 ──────────────────────────────────────────────
v2 = pd.read_csv(DATA_V2)
v1 = pd.read_csv(DATA_V1)

# 분석 변수 컬럼만 추출
feature_cols = [c for c in v2.columns if c.startswith(('F','N','G')) and c != 'G_AVG_Governance']
target_col   = 'Learning_Poverty'

print(f"분석 변수 수: {len(feature_cols)}")
print(f"변수 목록: {feature_cols}")

# ── 2. 다중공선성 히트맵 ────────────────────────────────────────
corr_matrix = v2[feature_cols + [target_col]].corr(method='spearman')

fig, ax = plt.subplots(figsize=(14, 11))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(
    corr_matrix, mask=mask, annot=True, fmt='.2f',
    cmap='coolwarm', vmin=-1, vmax=1, center=0,
    square=True, linewidths=0.5, ax=ax,
    annot_kws={'size': 7}
)
ax.set_title('Spearman Correlation: All v2.0 Features (F + N + G)', fontsize=13, pad=15)
plt.tight_layout()
plt.savefig(IMG_DIR + 'p1_multicollinearity_heatmap.png', dpi=200)
plt.close()
print("[저장] p1_multicollinearity_heatmap.png")

# ── 3. VIF 계산 ──────────────────────────────────────────────────
vif_data = v2[feature_cols].dropna()
vif_results = []
for i, col in enumerate(feature_cols):
    vif = variance_inflation_factor(vif_data.values, i)
    vif_results.append({'Variable': col, 'VIF': round(vif, 2)})

vif_df = pd.DataFrame(vif_results).sort_values('VIF', ascending=False)
print("\n=== VIF 결과 (10 이상 = 다중공선성 위험) ===")
print(vif_df.to_string(index=False))

# VIF 시각화
fig, ax = plt.subplots(figsize=(10, 6))
colors = ['#e74c3c' if v >= 10 else '#f39c12' if v >= 5 else '#2ecc71' for v in vif_df['VIF']]
bars = ax.barh(vif_df['Variable'], vif_df['VIF'], color=colors)
ax.axvline(x=10, color='red', linestyle='--', linewidth=1.5, label='VIF=10 (위험)')
ax.axvline(x=5,  color='orange', linestyle='--', linewidth=1.0, label='VIF=5 (주의)')
ax.set_xlabel('VIF (Variance Inflation Factor)')
ax.set_title('VIF Analysis — v2.0 Feature Variables')
ax.legend()
# 값 레이블
for bar, val in zip(bars, vif_df['VIF']):
    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}', va='center', fontsize=9)
plt.tight_layout()
plt.savefig(IMG_DIR + 'p1_vif_analysis.png', dpi=200)
plt.close()
print("[저장] p1_vif_analysis.png")

# ── 4. 다중공선성 위험 변수 쌍 식별 ────────────────────────────
print("\n=== 상관계수 |r| > 0.80 인 변수 쌍 (다중공선성 위험) ===")
high_corr_pairs = []
for i in range(len(feature_cols)):
    for j in range(i+1, len(feature_cols)):
        r = corr_matrix.loc[feature_cols[i], feature_cols[j]]
        if abs(r) > 0.80:
            high_corr_pairs.append((feature_cols[i], feature_cols[j], round(r, 3)))
            print(f"  {feature_cols[i]} ↔ {feature_cols[j]}: r = {r:.3f}")

if not high_corr_pairs:
    print("  → 위험 수준 쌍 없음")

# ── 5. Imputation 전후 KDE Plot ────────────────────────────────
# v1 원본 조혼율 결측 패턴과 v2 imputed 비교
# N5는 원래 44개 결측이었음 → imputation으로 채워진 국가 확인
# v1에는 N5가 없으므로, imputed 여부를 직접 계산
# 원래 Step 0 스캔 시 수집된 값(61개) vs 0으로 채워진 44개
# 근사: 0 근처 값이 imputed된 값일 가능성 높음

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# KDE 비교: N5(조혼율), G1(거버넌스), N1(유아사망률)
check_vars = ['N5_Child_Marriage_Female', 'G1_Gov_Effectiveness', 'N1_Under5_Mortality']
original_counts = {'N5_Child_Marriage_Female': 61, 'G1_Gov_Effectiveness': 102, 'N1_Under5_Mortality': 103}
titles = ['N5: 여성 조혼율 (결측 41.9%→0%)', 'G1: 정부효과성 WGI (결측 2.9%→0%)', 'N1: 유아 사망률 (결측 1.9%→0%)']

for ax, var, title, orig_n in zip(axes, check_vars, titles, original_counts.values()):
    data_full = v2[var].dropna()
    # 원본 보유 vs KNN 보정분 구분은 불가 → 전체 분포만 표시
    ax.hist(data_full, bins=20, color='#3498db', alpha=0.6, edgecolor='white', label=f'KNN 보정 후 (n={len(data_full)})')
    data_full.plot.kde(ax=ax, color='#2c3e50', linewidth=2)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel(var)
    ax.legend(fontsize=8)

plt.suptitle('Imputation 후 변수 분포 (KDE + 히스토그램)', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig(IMG_DIR + 'p1_imputation_distribution.png', dpi=200, bbox_inches='tight')
plt.close()
print("[저장] p1_imputation_distribution.png")

print("\n=== Phase 1 품질 점검 완료 ===")
print("핵심 확인 사항:")
high_vif = vif_df[vif_df['VIF'] >= 10]
if len(high_vif) > 0:
    print(f"  ⚠️  VIF >= 10 변수: {high_vif['Variable'].tolist()}")
else:
    print("  ✅ VIF 10 이상 변수 없음")
print(f"  ⚠️  |r| > 0.80 고상관 쌍 수: {len(high_corr_pairs)}개")
