# -*- coding: utf-8 -*-
"""
WB_LPGD 데이터셋 EDA - 3단계: 시각화 (그래프 6~12)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import koreanize_matplotlib
import os, warnings
warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
IMG_DIR = os.path.join(os.path.dirname(__file__), '..', 'images')
df = pd.read_csv(os.path.join(DATA_DIR, 'WB_LPGD.csv'))

# 퍼센트 지표만 필터링
pct_indicators = [
    'WB_LPGD_SE_LPV_PRIM', 'WB_LPGD_SE_LPV_PRIM_LD', 'WB_LPGD_SE_LPV_PRIM_SD',
    'WB_LPGD_SE_LPV_PRIM_LDGAP', 'WB_LPGD_SE_LPV_PRIM_LDSEV',
    'WB_LPGD_SE_LPV_PRIM_LPGAP', 'WB_LPGD_SE_LPV_PRIM_LPSEV'
]
ind_short = {
    'WB_LPGD_SE_LPV_PRIM': '학습빈곤율',
    'WB_LPGD_SE_LPV_PRIM_LD': '읽기미달성률',
    'WB_LPGD_SE_LPV_PRIM_SD': '비재학률',
    'WB_LPGD_SE_LPV_PRIM_LDGAP': '학습결핍격차',
    'WB_LPGD_SE_LPV_PRIM_LDSEV': '학습결핍심각도',
    'WB_LPGD_SE_LPV_PRIM_LPGAP': '학습빈곤격차',
    'WB_LPGD_SE_LPV_PRIM_LPSEV': '학습빈곤심각도',
}

# ========== 그래프 6: 성별 학습빈곤율 비교 ==========
lp = df[df['INDICATOR'] == 'WB_LPGD_SE_LPV_PRIM']
sex_data = lp[lp['SEX_LABEL'].isin(['Male', 'Female'])]
latest = sex_data.sort_values('TIME_PERIOD').groupby(['REF_AREA_LABEL','SEX_LABEL']).last().reset_index()
pivot = latest.pivot(index='REF_AREA_LABEL', columns='SEX_LABEL', values='OBS_VALUE').dropna()

fig, ax = plt.subplots(figsize=(10, 10))
ax.scatter(pivot['Male'], pivot['Female'], alpha=0.6, s=50, c='#6366f1', edgecolors='white')
lim = max(pivot['Male'].max(), pivot['Female'].max()) + 5
ax.plot([0, lim], [0, lim], 'k--', alpha=0.4, linewidth=1)
ax.set_xlabel('남성 학습빈곤율 (%)', fontsize=12)
ax.set_ylabel('여성 학습빈곤율 (%)', fontsize=12)
ax.set_title('국가별 성별 학습빈곤율 비교 (대각선 위=여성 높음)', fontsize=13, fontweight='bold')
ax.set_xlim(0, lim); ax.set_ylim(0, lim)
above = (pivot['Female'] > pivot['Male']).sum()
below = (pivot['Female'] <= pivot['Male']).sum()
ax.text(0.05, 0.95, f'여성>남성: {above}개국\n남성≥여성: {below}개국',
    transform=ax.transAxes, fontsize=11, va='top',
    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot06_gender_comparison.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 6 저장: 성별 학습빈곤율 비교")

# ========== 그래프 7: 주요 지표 간 상관관계 히트맵 ==========
df_pct = df[df['INDICATOR'].isin(pct_indicators) & (df['SEX_LABEL'] == 'Total')]
latest_pct = df_pct.sort_values('TIME_PERIOD').groupby(['REF_AREA_LABEL','INDICATOR']).last().reset_index()
pivot_corr = latest_pct.pivot(index='REF_AREA_LABEL', columns='INDICATOR', values='OBS_VALUE')
pivot_corr.columns = [ind_short.get(c, c) for c in pivot_corr.columns]
corr = pivot_corr.corr()

fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(corr.values, cmap='RdYlBu_r', vmin=-1, vmax=1, aspect='auto')
ax.set_xticks(range(len(corr.columns)))
ax.set_yticks(range(len(corr.columns)))
ax.set_xticklabels(corr.columns, rotation=45, ha='right', fontsize=10)
ax.set_yticklabels(corr.columns, fontsize=10)
for i in range(len(corr)):
    for j in range(len(corr)):
        ax.text(j, i, f'{corr.values[i,j]:.2f}', ha='center', va='center', fontsize=9,
                color='white' if abs(corr.values[i,j]) > 0.6 else 'black')
plt.colorbar(im, ax=ax, label='상관계수')
ax.set_title('학습빈곤 관련 지표 간 상관관계', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot07_correlation_heatmap.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 7 저장: 지표 간 상관관계 히트맵")

# ========== 그래프 8: 학습빈곤율 vs 비재학률 산점도 ==========
lp_data = latest_pct[latest_pct['INDICATOR']=='WB_LPGD_SE_LPV_PRIM'][['REF_AREA_LABEL','OBS_VALUE']].rename(columns={'OBS_VALUE':'학습빈곤율'})
sd_data = latest_pct[latest_pct['INDICATOR']=='WB_LPGD_SE_LPV_PRIM_SD'][['REF_AREA_LABEL','OBS_VALUE']].rename(columns={'OBS_VALUE':'비재학률'})
merged = lp_data.merge(sd_data, on='REF_AREA_LABEL')

fig, ax = plt.subplots(figsize=(10, 8))
sc = ax.scatter(merged['비재학률'], merged['학습빈곤율'], s=60, alpha=0.7, c='#e11d48', edgecolors='white')
z = np.polyfit(merged['비재학률'], merged['학습빈곤율'], 1)
p = np.poly1d(z)
x_line = np.linspace(merged['비재학률'].min(), merged['비재학률'].max(), 100)
ax.plot(x_line, p(x_line), '--', color='#1e40af', linewidth=2, alpha=0.7)
r = merged['비재학률'].corr(merged['학습빈곤율'])
ax.set_xlabel('초등 비재학률 (%)', fontsize=12)
ax.set_ylabel('학습빈곤율 (%)', fontsize=12)
ax.set_title(f'비재학률 vs 학습빈곤율 (r={r:.3f})', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot08_oos_vs_lp.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 8 저장: 비재학률 vs 학습빈곤율")

# ========== 그래프 9: 퍼센트 지표 박스플롯 비교 ==========
fig, ax = plt.subplots(figsize=(12, 7))
box_data = []
box_labels = []
for ind in pct_indicators:
    vals = df[(df['INDICATOR']==ind) & (df['SEX_LABEL']=='Total')]['OBS_VALUE'].dropna()
    if len(vals) > 0:
        box_data.append(vals.values)
        box_labels.append(ind_short.get(ind, ind))

bp = ax.boxplot(box_data, vert=True, patch_artist=True, labels=box_labels,
    medianprops=dict(color='#1e293b', linewidth=2))
colors_box = ['#ef4444','#f97316','#eab308','#22c55e','#06b6d4','#3b82f6','#8b5cf6']
for patch, color in zip(bp['boxes'], colors_box):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax.set_ylabel('값 (%)', fontsize=12)
ax.set_title('학습빈곤 관련 7개 퍼센트 지표 분포 비교', fontsize=14, fontweight='bold')
ax.tick_params(axis='x', rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot09_indicator_boxplots.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 9 저장: 지표별 박스플롯 비교")

# ========== 그래프 10: 연도별 평균 학습빈곤율 추이 (성별) ==========
lp_yearly = lp.groupby(['TIME_PERIOD','SEX_LABEL'])['OBS_VALUE'].mean().reset_index()
fig, ax = plt.subplots(figsize=(12, 6))
for sex, color, marker in [('Total','#1e40af','o'), ('Male','#2563eb','s'), ('Female','#ec4899','^')]:
    sub = lp_yearly[lp_yearly['SEX_LABEL']==sex].sort_values('TIME_PERIOD')
    if len(sub) > 0:
        ax.plot(sub['TIME_PERIOD'], sub['OBS_VALUE'], marker=marker, color=color,
                linewidth=2, markersize=6, label=sex, alpha=0.85)
ax.set_xlabel('연도', fontsize=12)
ax.set_ylabel('평균 학습빈곤율 (%)', fontsize=12)
ax.set_title('연도별 평균 학습빈곤율 추이 (성별)', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot10_yearly_trend_sex.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 10 저장: 연도별 평균 학습빈곤율 추이 (성별)")

# ========== 그래프 11: 대륙/지역별 학습빈곤율 (REF_AREA 코드 기반 그룹) ==========
# 지역 분류 (세계은행 기준 주요 국가 코드)
region_map = {
    'AFG':'남아시아','BGD':'남아시아','IND':'남아시아','PAK':'남아시아','NPL':'남아시아','LKA':'남아시아',
    'CHN':'동아시아','KHM':'동아시아','IDN':'동아시아','LAO':'동아시아','MMR':'동아시아','PHL':'동아시아',
    'THA':'동아시아','VNM':'동아시아','MYS':'동아시아',
    'BRA':'중남미','MEX':'중남미','COL':'중남미','PER':'중남미','ARG':'중남미','CHL':'중남미',
    'CRI':'중남미','GTM':'중남미','HND':'중남미','NIC':'중남미','SLV':'중남미','DOM':'중남미','PRY':'중남미',
    'NGA':'사하라이남','GHA':'사하라이남','KEN':'사하라이남','TZA':'사하라이남','UGA':'사하라이남',
    'ETH':'사하라이남','ZAF':'사하라이남','SEN':'사하라이남','CMR':'사하라이남','MOZ':'사하라이남',
    'MWI':'사하라이남','ZMB':'사하라이남','TCD':'사하라이남','BFA':'사하라이남','MLI':'사하라이남',
    'NER':'사하라이남','COD':'사하라이남','COG':'사하라이남','RWA':'사하라이남','MDG':'사하라이남',
    'EGY':'중동/북아프리카','MAR':'중동/북아프리카','TUN':'중동/북아프리카','JOR':'중동/북아프리카','IRQ':'중동/북아프리카',
    'GBR':'유럽/북미','FRA':'유럽/북미','DEU':'유럽/북미','ITA':'유럽/북미','ESP':'유럽/북미',
    'PRT':'유럽/북미','GRC':'유럽/북미','POL':'유럽/북미','ROU':'유럽/북미','USA':'유럽/북미',
    'CAN':'유럽/북미','AUS':'유럽/북미','NZL':'유럽/북미','JPN':'동아시아','KOR':'동아시아',
}
lp_total = lp[lp['SEX_LABEL']=='Total'].copy()
lp_total['지역'] = lp_total['REF_AREA'].map(region_map)
lp_region = lp_total.dropna(subset=['지역'])
latest_region = lp_region.sort_values('TIME_PERIOD').groupby(['REF_AREA_LABEL','지역']).last().reset_index()

if len(latest_region) > 0:
    fig, ax = plt.subplots(figsize=(12, 7))
    regions = latest_region.groupby('지역')['OBS_VALUE'].agg(['mean','median','count']).sort_values('mean', ascending=False)
    region_colors = {'사하라이남':'#dc2626','남아시아':'#f97316','중동/북아프리카':'#eab308',
                     '중남미':'#22c55e','동아시아':'#3b82f6','유럽/북미':'#6366f1'}
    bars = ax.bar(regions.index, regions['mean'],
        color=[region_colors.get(r,'gray') for r in regions.index], alpha=0.85, edgecolor='white', linewidth=1.5)
    for bar, (idx, row) in zip(bars, regions.iterrows()):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                f'{row["mean"]:.1f}%\n(n={int(row["count"])})', ha='center', fontsize=10)
    ax.set_ylabel('평균 학습빈곤율 (%)', fontsize=12)
    ax.set_title('지역별 평균 학습빈곤율', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'plot11_region_lp.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 그래프 11 저장: 지역별 평균 학습빈곤율")

# ========== 그래프 12: 학습빈곤율 vs 읽기미달성률 산점도 ==========
ld_data = latest_pct = df[(df['INDICATOR'].isin(['WB_LPGD_SE_LPV_PRIM','WB_LPGD_SE_LPV_PRIM_LD'])) & (df['SEX_LABEL']=='Total')]
latest_pct2 = ld_data.sort_values('TIME_PERIOD').groupby(['REF_AREA_LABEL','INDICATOR']).last().reset_index()
lp2 = latest_pct2[latest_pct2['INDICATOR']=='WB_LPGD_SE_LPV_PRIM'][['REF_AREA_LABEL','OBS_VALUE']].rename(columns={'OBS_VALUE':'학습빈곤율'})
ld2 = latest_pct2[latest_pct2['INDICATOR']=='WB_LPGD_SE_LPV_PRIM_LD'][['REF_AREA_LABEL','OBS_VALUE']].rename(columns={'OBS_VALUE':'읽기미달성률'})
merged2 = lp2.merge(ld2, on='REF_AREA_LABEL')

fig, ax = plt.subplots(figsize=(10, 8))
ax.scatter(merged2['읽기미달성률'], merged2['학습빈곤율'], s=60, alpha=0.7, c='#7c3aed', edgecolors='white')
z2 = np.polyfit(merged2['읽기미달성률'], merged2['학습빈곤율'], 1)
p2 = np.poly1d(z2)
x2 = np.linspace(merged2['읽기미달성률'].min(), merged2['읽기미달성률'].max(), 100)
ax.plot(x2, p2(x2), '--', color='#dc2626', linewidth=2, alpha=0.7)
r2 = merged2['읽기미달성률'].corr(merged2['학습빈곤율'])
ax.plot([0,100],[0,100],'k--',alpha=0.3)
ax.set_xlabel('읽기미달성률 (%)', fontsize=12)
ax.set_ylabel('학습빈곤율 (%)', fontsize=12)
ax.set_title(f'읽기미달성률 vs 학습빈곤율 (r={r2:.3f})', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, 'plot12_ld_vs_lp.png'), dpi=150, bbox_inches='tight')
plt.close()
print("✅ 그래프 12 저장: 읽기미달성률 vs 학습빈곤율")

print("\n✅ 3단계(그래프 6~12) 완료")
