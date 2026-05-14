# -*- coding: utf-8 -*-
"""
A2: 정책 효율성 역설 분석 (Policy Efficiency Paradox)
- Step 1: 교육지출 vs 학습빈곤 산점도 (전체 + 소득그룹별)
- Step 2: 거버넌스 3분위 조건부 패싯 플롯
- Step 3: 교호작용 회귀 (OLS + 부트스트래핑)
- Step 4: 임계점 탐색 + 히트맵

핵심 가설: 교육 지출이 학습 빈곤을 낮추는 효과는
          거버넌스 수준이 충분히 높을 때만 유의하다.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ── 경로 설정 ──────────────────────────────────────────────────
DATA_PATH = '../data/processed/analysis_ready_v2.csv'
IMG_DIR   = '../images/'

C_LOW  = '#e74c3c'
C_MID  = '#f39c12'
C_HIGH = '#2ecc71'
C_MAIN = '#2c3e50'

df = pd.read_csv(DATA_PATH)
print(f"데이터 로드: {df.shape[0]}개국")

# ══════════════════════════════════════════════════════════════
# STEP 1: 교육지출 vs 학습빈곤 산점도 (전체 + 소득그룹별)
# ══════════════════════════════════════════════════════════════
print("\n[Step 1] 교육지출 단독 효과 검증...")

# GDP 기준 소득 그룹 (World Bank 기준 근사)
df['Income_Group'] = pd.cut(df['F1_GDP_per_capita'],
    bins=[0, 1085, 4255, 13205, float('inf')],
    labels=['저소득', '중하소득', '중상소득', '고소득'])

# 전체 상관
r_all, p_all = stats.spearmanr(df['F2_Gov_Edu_Exp'], df['Learning_Poverty'])
print(f"  전체 상관 (Spearman): r={r_all:.3f}, p={p_all:.4f}")

income_colors = {'저소득': C_LOW, '중하소득': C_MID, '중상소득': '#3498db', '고소득': C_HIGH}

fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# 패널 1: 전체 산점도
for group, color in income_colors.items():
    sub = df[df['Income_Group'] == group]
    axes[0].scatter(sub['F2_Gov_Edu_Exp'], sub['Learning_Poverty'],
                    color=color, alpha=0.75, s=55, label=f'{group} (n={len(sub)})', zorder=3)
# 전체 회귀선
x_all = df['F2_Gov_Edu_Exp'].values
y_all = df['Learning_Poverty'].values
m, b = np.polyfit(x_all, y_all, 1)
x_line = np.linspace(x_all.min(), x_all.max(), 100)
axes[0].plot(x_line, m*x_line+b, color=C_MAIN, linewidth=2, linestyle='--',
             label=f'전체 회귀선 (r={r_all:.2f}, p={p_all:.3f})')
axes[0].set_xlabel('교육지출 (%GDP)', fontsize=11)
axes[0].set_ylabel('학습 빈곤율 (%)', fontsize=11)
axes[0].set_title('교육지출 vs 학습빈곤율 — 전체 국가', fontsize=12)
axes[0].legend(fontsize=8.5)
axes[0].grid(True, alpha=0.3)
axes[0].text(0.05, 0.95, '※ 전체적으로 관계 미약\n(지출 많아도 빈곤 높은 국가 다수)',
             transform=axes[0].transAxes, fontsize=8, color='gray',
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

# 패널 2: 소득 그룹별 회귀선
for group, color in income_colors.items():
    sub = df[df['Income_Group'] == group].dropna(subset=['F2_Gov_Edu_Exp'])
    if len(sub) >= 5:
        r_g, p_g = stats.spearmanr(sub['F2_Gov_Edu_Exp'], sub['Learning_Poverty'])
        m_g, b_g = np.polyfit(sub['F2_Gov_Edu_Exp'], sub['Learning_Poverty'], 1)
        x_g = np.linspace(sub['F2_Gov_Edu_Exp'].min(), sub['F2_Gov_Edu_Exp'].max(), 100)
        axes[1].scatter(sub['F2_Gov_Edu_Exp'], sub['Learning_Poverty'],
                        color=color, alpha=0.6, s=45, zorder=3)
        axes[1].plot(x_g, m_g*x_g+b_g, color=color, linewidth=2.5,
                     label=f'{group}: r={r_g:.2f} (p={p_g:.3f})')

axes[1].set_xlabel('교육지출 (%GDP)', fontsize=11)
axes[1].set_ylabel('학습 빈곤율 (%)', fontsize=11)
axes[1].set_title('소득 그룹별 교육지출 vs 학습빈곤\n(그룹 내 회귀선)', fontsize=12)
axes[1].legend(fontsize=8.5)
axes[1].grid(True, alpha=0.3)

plt.suptitle('Step 1: 교육지출 단독 효과 — "쓴다고 해결되지 않는다"', fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(IMG_DIR + 'a2_edu_exp_scatter.png', dpi=200, bbox_inches='tight')
plt.close()
print("[저장] a2_edu_exp_scatter.png")

# ══════════════════════════════════════════════════════════════
# STEP 2: 거버넌스 3분위 조건부 패싯 플롯
# ══════════════════════════════════════════════════════════════
print("\n[Step 2] 거버넌스 3분위 조건부 분석...")

df['Gov_Tertile'] = pd.qcut(df['G_AVG_Governance'], q=3,
    labels=['低거버넌스\n(하위 1/3)', '中거버넌스\n(중위 1/3)', '高거버넌스\n(상위 1/3)'])

tertile_colors = {
    '低거버넌스\n(하위 1/3)': C_LOW,
    '中거버넌스\n(중위 1/3)': C_MID,
    '高거버넌스\n(상위 1/3)': C_HIGH,
}

fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)

for ax, (tertile, color) in zip(axes, [
    ('低거버넌스\n(하위 1/3)', C_LOW),
    ('中거버넌스\n(중위 1/3)', C_MID),
    ('高거버넌스\n(상위 1/3)', C_HIGH)
]):
    sub = df[df['Gov_Tertile'] == tertile].dropna(subset=['F2_Gov_Edu_Exp'])
    r_t, p_t = stats.spearmanr(sub['F2_Gov_Edu_Exp'], sub['Learning_Poverty'])
    ax.scatter(sub['F2_Gov_Edu_Exp'], sub['Learning_Poverty'],
               color=color, alpha=0.75, s=55, edgecolors='white', linewidth=0.5)
    if len(sub) >= 5:
        m_t, b_t = np.polyfit(sub['F2_Gov_Edu_Exp'], sub['Learning_Poverty'], 1)
        x_t = np.linspace(sub['F2_Gov_Edu_Exp'].min(), sub['F2_Gov_Edu_Exp'].max(), 100)
        ax.plot(x_t, m_t*x_t+b_t, color=C_MAIN, linewidth=2, linestyle='--')
    gov_mean = sub['G_AVG_Governance'].mean()
    ax.set_title(f'{tertile}\n(WGI 평균: {gov_mean:.2f})', fontsize=11)
    ax.set_xlabel('교육지출 (%GDP)', fontsize=10)
    if ax == axes[0]:
        ax.set_ylabel('학습 빈곤율 (%)', fontsize=10)
    ax.text(0.05, 0.95, f'r = {r_t:.3f}\np = {p_t:.3f}\nn = {len(sub)}',
            transform=ax.transAxes, fontsize=9,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax.grid(True, alpha=0.3)
    print(f"  {tertile.replace(chr(10),' ')}: n={len(sub)}, r={r_t:.3f}, p={p_t:.4f}")

plt.suptitle('Step 2: 거버넌스 수준별 교육투자 효과 비교\n"거버넌스가 높아야 교육 투자가 효과를 낸다"',
             fontsize=13, y=1.03)
plt.tight_layout()
plt.savefig(IMG_DIR + 'a2_governance_facet.png', dpi=200, bbox_inches='tight')
plt.close()
print("[저장] a2_governance_facet.png")

# ══════════════════════════════════════════════════════════════
# STEP 3: 교호작용 회귀 (OLS + 부트스트래핑)
# ══════════════════════════════════════════════════════════════
print("\n[Step 3] 교호작용 OLS 회귀...")

reg_df = df[['Learning_Poverty', 'F2_Gov_Edu_Exp', 'G_AVG_Governance', 'F1_GDP_per_capita']].dropna().copy()

# 표준화 (해석 용이성)
for col in ['F2_Gov_Edu_Exp', 'G_AVG_Governance', 'F1_GDP_per_capita']:
    reg_df[f'{col}_z'] = (reg_df[col] - reg_df[col].mean()) / reg_df[col].std()

reg_df['EduGov_Interaction'] = reg_df['F2_Gov_Edu_Exp_z'] * reg_df['G_AVG_Governance_z']

formula = 'Learning_Poverty ~ F2_Gov_Edu_Exp_z + G_AVG_Governance_z + EduGov_Interaction + F1_GDP_per_capita_z'
model = smf.ols(formula, data=reg_df).fit()
print(model.summary())

# 핵심 계수 출력
print("\n=== 핵심 회귀 결과 ===")
for coef_name in ['F2_Gov_Edu_Exp_z', 'G_AVG_Governance_z', 'EduGov_Interaction', 'F1_GDP_per_capita_z']:
    coef = model.params[coef_name]
    pval = model.pvalues[coef_name]
    ci   = model.conf_int().loc[coef_name]
    sig  = '✅ 유의' if pval < 0.05 else '❌ 비유의'
    print(f"  {coef_name:30s}: β={coef:+.3f}, p={pval:.4f}, CI=[{ci[0]:+.3f}, {ci[1]:+.3f}]  {sig}")
print(f"  모델 R²: {model.rsquared:.3f},  Adj-R²: {model.rsquared_adj:.3f}")

# 부트스트래핑 (B=1000)
print("\n  부트스트래핑 신뢰구간 계산 (B=1000)...")
np.random.seed(42)
boot_coefs = {'EduGov_Interaction': [], 'G_AVG_Governance_z': []}
for _ in range(1000):
    sample = reg_df.sample(n=len(reg_df), replace=True)
    try:
        m_boot = smf.ols(formula, data=sample).fit()
        boot_coefs['EduGov_Interaction'].append(m_boot.params['EduGov_Interaction'])
        boot_coefs['G_AVG_Governance_z'].append(m_boot.params['G_AVG_Governance_z'])
    except Exception:
        pass

for key, vals in boot_coefs.items():
    ci_low  = np.percentile(vals, 2.5)
    ci_high = np.percentile(vals, 97.5)
    print(f"  Boot 95% CI [{key}]: [{ci_low:+.3f}, {ci_high:+.3f}]"
          f"  {'0 불포함 → 안정적' if ci_low * ci_high > 0 else '0 포함 → 불안정'}")

# 회귀계수 시각화
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

coef_labels = {
    'F2_Gov_Edu_Exp_z'   : '교육지출\n(표준화)',
    'G_AVG_Governance_z' : '거버넌스\n(표준화)',
    'EduGov_Interaction' : '교육지출\n×거버넌스\n(교호작용)',
    'F1_GDP_per_capita_z': '1인당 GDP\n(통제변수)',
}
coefs = [model.params[k] for k in coef_labels]
errors = [(model.params[k] - model.conf_int().loc[k, 0]) for k in coef_labels]
pvals  = [model.pvalues[k] for k in coef_labels]
colors_bar = [C_HIGH if p < 0.05 else '#bdc3c7' for p in pvals]

bars = axes[0].bar(list(coef_labels.values()), coefs, color=colors_bar,
                   alpha=0.85, edgecolor='white', yerr=errors, capsize=4)
axes[0].axhline(y=0, color=C_MAIN, linewidth=1.5)
axes[0].set_ylabel('표준화 회귀계수 (β)', fontsize=10)
axes[0].set_title('OLS 교호작용 회귀계수\n(녹색 = p<0.05 유의)', fontsize=11)
for bar, pval, coef in zip(bars, pvals, coefs):
    mark = '★' if pval < 0.05 else ''
    axes[0].text(bar.get_x() + bar.get_width()/2,
                 coef + (0.3 if coef >= 0 else -0.6),
                 f'β={coef:+.2f}{mark}', ha='center', fontsize=8.5)
axes[0].grid(True, axis='y', alpha=0.3)

# 부트스트래핑 분포
axes[1].hist(boot_coefs['EduGov_Interaction'], bins=40, color='#3498db', alpha=0.7, edgecolor='white')
ci_vals = [np.percentile(boot_coefs['EduGov_Interaction'], 2.5),
           np.percentile(boot_coefs['EduGov_Interaction'], 97.5)]
axes[1].axvline(x=model.params['EduGov_Interaction'], color=C_MAIN, linewidth=2.5, label=f'OLS 추정값: {model.params["EduGov_Interaction"]:+.3f}')
axes[1].axvline(x=ci_vals[0], color='red', linewidth=1.5, linestyle='--', label=f'95% CI: [{ci_vals[0]:+.3f}, {ci_vals[1]:+.3f}]')
axes[1].axvline(x=ci_vals[1], color='red', linewidth=1.5, linestyle='--')
axes[1].axvline(x=0, color='gray', linewidth=1, linestyle=':', alpha=0.7, label='β=0 기준선')
axes[1].set_xlabel('교호작용 계수 (β₃)', fontsize=10)
axes[1].set_ylabel('빈도 (B=1000)', fontsize=10)
axes[1].set_title('교호작용항 부트스트래핑 분포\n(신뢰구간에 0 포함 여부 확인)', fontsize=11)
axes[1].legend(fontsize=8.5)

plt.suptitle('Step 3: 교육투자 × 거버넌스 교호작용 회귀 결과', fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(IMG_DIR + 'a2_interaction_coef.png', dpi=200, bbox_inches='tight')
plt.close()
print("[저장] a2_interaction_coef.png")

# ══════════════════════════════════════════════════════════════
# STEP 4: 임계점 탐색 + 히트맵
# ══════════════════════════════════════════════════════════════
print("\n[Step 4] 임계점 탐색 + 교육투자×거버넌스 히트맵...")

df['Edu_Quartile'] = pd.qcut(df['F2_Gov_Edu_Exp'], q=4, labels=['Q1\n낮음', 'Q2', 'Q3', 'Q4\n높음'])
df['Gov_Quartile'] = pd.qcut(df['G_AVG_Governance'], q=4, labels=['G1\n低', 'G2', 'G3', 'G4\n高'])

# 히트맵용 피벗
pivot = df.groupby(['Gov_Quartile', 'Edu_Quartile'], observed=True)['Learning_Poverty'].mean().unstack()
count_pivot = df.groupby(['Gov_Quartile', 'Edu_Quartile'], observed=True)['Learning_Poverty'].count().unstack()

fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# 히트맵
im = axes[0].imshow(pivot.values, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=100)
plt.colorbar(im, ax=axes[0], label='평균 학습 빈곤율 (%)')
axes[0].set_xticks(range(len(pivot.columns)))
axes[0].set_xticklabels(pivot.columns, fontsize=9)
axes[0].set_yticks(range(len(pivot.index)))
axes[0].set_yticklabels(pivot.index, fontsize=9)
axes[0].set_xlabel('교육지출 분위', fontsize=10)
axes[0].set_ylabel('거버넌스 분위', fontsize=10)
axes[0].set_title('교육투자 × 거버넌스 — 평균 학습빈곤율 히트맵\n(녹색=낮음, 적색=높음)', fontsize=11)
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        val = pivot.values[i, j]
        cnt = count_pivot.values[i, j]
        if not np.isnan(val):
            axes[0].text(j, i, f'{val:.1f}%\n(n={int(cnt)})',
                        ha='center', va='center', fontsize=8.5,
                        color='white' if val > 60 else 'black')

# 거버넌스 구간별 상관계수 변화 (임계점 탐색)
gov_vals = sorted(df['G_AVG_Governance'].unique())
gov_thresholds = np.percentile(df['G_AVG_Governance'], np.arange(10, 91, 10))
window_corrs = []
for thresh in gov_thresholds:
    sub = df[df['G_AVG_Governance'] >= thresh]
    if len(sub) >= 10:
        r, p = stats.spearmanr(sub['F2_Gov_Edu_Exp'], sub['Learning_Poverty'])
        window_corrs.append({'threshold': thresh, 'r': r, 'p': p, 'n': len(sub)})

corr_df = pd.DataFrame(window_corrs)
axes[1].plot(corr_df['threshold'], corr_df['r'], color='#3498db', linewidth=2.5, marker='o', markersize=6)
axes[1].axhline(y=0, color='gray', linewidth=1, linestyle='--', alpha=0.7)
axes[1].fill_between(corr_df['threshold'], corr_df['r'], 0,
                     where=(corr_df['r'] < 0), alpha=0.15, color=C_HIGH, label='교육지출 효과 유의 방향')
axes[1].set_xlabel('거버넌스 임계값 (WGI)\n(이 값 이상인 국가만 포함)', fontsize=10)
axes[1].set_ylabel('교육지출-학습빈곤 Spearman r', fontsize=10)
axes[1].set_title('거버넌스 수준에 따른 교육투자 효과 변화\n(임계점 탐색)', fontsize=11)

# 임계점 표시
neg_corr = corr_df[corr_df['r'] < 0]
if len(neg_corr) > 0:
    threshold_val = neg_corr.iloc[0]['threshold']
    axes[1].axvline(x=threshold_val, color='red', linewidth=2, linestyle='--',
                    label=f'임계점: WGI ≈ {threshold_val:.2f}')
    axes[1].legend(fontsize=9)
    print(f"\n  → 교육투자 효과가 음(-)으로 전환되는 WGI 임계점: {threshold_val:.3f}")

axes[1].grid(True, alpha=0.3)

# n수 표시
for _, row in corr_df.iterrows():
    axes[1].annotate(f"n={int(row['n'])}", xy=(row['threshold'], row['r']),
                     xytext=(3, 4), textcoords='offset points', fontsize=7, color='gray')

plt.suptitle('Step 4: 교육투자 효과의 거버넌스 임계점 분석', fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(IMG_DIR + 'a2_efficiency_heatmap.png', dpi=200, bbox_inches='tight')
plt.close()
print("[저장] a2_efficiency_heatmap.png")

# ── 최종 요약 ──────────────────────────────────────────────────
print("\n" + "="*60)
print("=== A2 분석 완료 요약 ===")
print(f"  전체 교육지출-학습빈곤 상관: r={r_all:.3f}, p={p_all:.4f}")
print(f"  교호작용항(β₃): {model.params['EduGov_Interaction']:+.3f} (p={model.pvalues['EduGov_Interaction']:.4f})")
print(f"  부트스트래핑 95% CI: [{ci_vals[0]:+.3f}, {ci_vals[1]:+.3f}]")
print(f"  모델 R²: {model.rsquared:.3f}")
if len(neg_corr) > 0:
    print(f"  WGI 임계점: ≈ {threshold_val:.3f}")
print("="*60)
