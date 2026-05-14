# -*- coding: utf-8 -*-
"""
WB_LPGD 데이터셋 EDA - 2단계: 시각화 (그래프 1~5)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import koreanize_matplotlib
import json, glob, os, warnings
warnings.filterwarnings('ignore')

# === 데이터 로딩 ===
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
IMG_DIR = os.path.join(os.path.dirname(__file__), '..', 'images')
os.makedirs(IMG_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(DATA_DIR, 'WB_LPGD.csv'))

# 지표명 매핑 (짧은 이름)
ind_short = {
    'WB_LPGD_SE_LPV_POP': '인구(2019 기준)',
    'WB_LPGD_SE_LPV_POP_PRIM': '초등학령인구(2019)',
    'WB_LPGD_SE_LPV_PRIM': '학습빈곤율(%)',
    'WB_LPGD_SE_LPV_PRIM_LD': '읽기미달성률(%)',
    'WB_LPGD_SE_LPV_PRIM_LDGAP': '학습결핍격차',
    'WB_LPGD_SE_LPV_PRIM_LDSEV': '학습결핍심각도',
    'WB_LPGD_SE_LPV_PRIM_LPGAP': '학습빈곤격차',
    'WB_LPGD_SE_LPV_PRIM_LPSEV': '학습빈곤심각도',
    'WB_LPGD_SE_LPV_PRIM_SD': '비재학률(%)',
}

# 색상 팔레트
colors = ['#2563eb', '#dc2626', '#16a34a', '#f59e0b', '#8b5cf6',
          '#ec4899', '#06b6d4', '#84cc16', '#f97316']

# ========== 그래프 1: 지표별 데이터 건수 ==========
fig, ax = plt.subplots(figsize=(12, 6))
ind_counts = df['INDICATOR'].value_counts()
bars = ax.barh([ind_short.get(x, x) for x in ind_counts.index], ind_counts.values, color=colors[:len(ind_counts)])
ax.set_xlabel('데이터 건수')
ax.set_title('지표별 데이터 건수 분포', fontsize=14, fontweight='bold')
for bar, v in zip(bars, ind_counts.values):
    ax.text(v + 20, bar.get_y() + bar.get_height()/2, f'{v:,}', va='center', fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot01_indicator_counts.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 1 저장: 지표별 데이터 건수 분포")

# ========== 그래프 2: 성별 분포 (파이차트) ==========
fig, ax = plt.subplots(figsize=(8, 8))
sex_counts = df['SEX_LABEL'].value_counts()
wedges, texts, autotexts = ax.pie(sex_counts.values, labels=sex_counts.index,
    autopct='%1.1f%%', colors=['#3b82f6', '#f472b6', '#a78bfa'],
    startangle=90, textprops={'fontsize': 12})
ax.set_title('성별 데이터 분포', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot02_sex_distribution.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 2 저장: 성별 데이터 분포")

# ========== 그래프 3: 연도별 데이터 건수 추이 ==========
fig, ax = plt.subplots(figsize=(12, 6))
year_counts = df['TIME_PERIOD'].value_counts().sort_index()
ax.bar(year_counts.index, year_counts.values, color='#6366f1', alpha=0.85, edgecolor='white')
ax.set_xlabel('연도')
ax.set_ylabel('데이터 건수')
ax.set_title('연도별 관측 데이터 건수', fontsize=14, fontweight='bold')
ax.set_xticks(year_counts.index)
ax.set_xticklabels(year_counts.index, rotation=45, ha='right')
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot03_year_counts.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 3 저장: 연도별 관측 데이터 건수")

# ========== 그래프 4: 학습빈곤율 분포 (히스토그램+박스플롯) ==========
lp = df[df['INDICATOR'] == 'WB_LPGD_SE_LPV_PRIM']
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
ax1.hist(lp['OBS_VALUE'].dropna(), bins=30, color='#ef4444', alpha=0.75, edgecolor='white')
ax1.set_xlabel('학습빈곤율 (%)')
ax1.set_ylabel('빈도')
ax1.set_title('학습빈곤율(Learning Poverty) 분포', fontsize=14, fontweight='bold')
ax1.axvline(lp['OBS_VALUE'].median(), color='#1e40af', linestyle='--', linewidth=2, label=f"중앙값: {lp['OBS_VALUE'].median():.1f}%")
ax1.legend(fontsize=11)
bp = ax2.boxplot(lp['OBS_VALUE'].dropna(), vert=False, widths=0.6,
    patch_artist=True, boxprops=dict(facecolor='#fca5a5', edgecolor='#dc2626'),
    medianprops=dict(color='#1e40af', linewidth=2))
ax2.set_xlabel('학습빈곤율 (%)')
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot04_learning_poverty_dist.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 4 저장: 학습빈곤율 분포")

# ========== 그래프 5: 상위/하위 15개국 학습빈곤율 ==========
lp_total = lp[lp['SEX_LABEL'] == 'Total']
latest = lp_total.sort_values('TIME_PERIOD').groupby('REF_AREA_LABEL').last().reset_index()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

# 상위 15 (학습빈곤율 높은 국가)
top15 = latest.nlargest(15, 'OBS_VALUE')
ax1.barh(top15['REF_AREA_LABEL'], top15['OBS_VALUE'], color='#dc2626', alpha=0.85)
ax1.set_xlabel('학습빈곤율 (%)')
ax1.set_title('학습빈곤율 상위 15개국 (최악)', fontsize=13, fontweight='bold')
for i, (v, y) in enumerate(zip(top15['OBS_VALUE'], top15['REF_AREA_LABEL'])):
    ax1.text(v + 0.5, i, f'{v:.1f}%', va='center', fontsize=9)
ax1.invert_yaxis()

# 하위 15 (학습빈곤율 낮은 국가)
bot15 = latest.nsmallest(15, 'OBS_VALUE')
ax2.barh(bot15['REF_AREA_LABEL'], bot15['OBS_VALUE'], color='#16a34a', alpha=0.85)
ax2.set_xlabel('학습빈곤율 (%)')
ax2.set_title('학습빈곤율 하위 15개국 (최선)', fontsize=13, fontweight='bold')
for i, (v, y) in enumerate(zip(bot15['OBS_VALUE'], bot15['REF_AREA_LABEL'])):
    ax2.text(v + 0.3, i, f'{v:.1f}%', va='center', fontsize=9)
ax2.invert_yaxis()

plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot05_top_bottom_countries.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 5 저장: 상위/하위 15개국 학습빈곤율")
print("\n✅ 2단계(그래프 1~5) 완료")
