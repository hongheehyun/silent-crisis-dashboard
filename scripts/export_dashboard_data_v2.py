"""
export_dashboard_data_v2.py
v2.0 대시보드용 JSON 데이터 생성
"""
import json, warnings
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score
warnings.filterwarnings('ignore')

# ── 데이터 로드 ─────────────────────────────────────────
df = pd.read_csv('../data/processed/analysis_ready_v2.csv')
df['log_GDP'] = np.log(df['F1_GDP_per_capita'])

# ── 기존 v1 JSON에서 iso3·region 가져오기 ────────────────
with open('../docs/dashboard_data.json', 'r') as f:
    v1 = json.load(f)
iso_map   = {c['name']: c['iso3']   for c in v1['countries']}
region_map= {c['name']: c['region'] for c in v1['countries']}

# ── log-GDP 잔차 모델 ────────────────────────────────────
X  = df[['log_GDP']].values
y  = df['Learning_Poverty'].values
m  = LinearRegression().fit(X, y)
df['LP_Predicted'] = m.predict(X)
df['Residual']     = df['Learning_Poverty'] - df['LP_Predicted']
threshold_low  = df['Residual'].quantile(0.20)
threshold_high = df['Residual'].quantile(0.80)
df['Deviance_Group'] = df['Residual'].apply(
    lambda r: 'positive' if r <= threshold_low
    else ('negative' if r >= threshold_high else 'middle')
)
r2  = m.score(X, y)
mae = float(np.mean(np.abs(df['Residual'])))

# ── 분석 변수 정의 ───────────────────────────────────────
FACTORS = {
    'N2_Adolescent_Fertility' : '10대 출산율',
    'N4_Physicians_per_1000'  : '의사 수',
    'F3_Pupil_Teacher_Ratio'  : '교사-학생 비율',
    'N5_Child_Marriage_Female': '여성 조혼율',
    'N1_Under5_Mortality'     : '유아 사망률',
    'F7_Completion_Rate'      : '초등 수료율',
    'G_AVG_Governance'        : '거버넌스 지수',
    'F2_Gov_Edu_Exp'          : '교육지출(%GDP)',
    'N3_Electricity_Access'   : '전기 보급률',
}

# ── 방법 A: 변수 잔차화 후 비교 ──────────────────────────
a1_factors = []
for col, label in FACTORS.items():
    tmp = df[['log_GDP', col, 'Deviance_Group', 'Learning_Poverty']].dropna().copy()
    if len(tmp) < 20:
        continue
    mf = LinearRegression().fit(tmp[['log_GDP']].values, tmp[col].values)
    tmp['resid_var'] = tmp[col] - mf.predict(tmp[['log_GDP']].values)
    pos = tmp[tmp['Deviance_Group'] == 'positive']['resid_var']
    oth = tmp[tmp['Deviance_Group'] != 'positive']['resid_var']
    _, p = stats.mannwhitneyu(pos, oth, alternative='two-sided')
    s = np.sqrt(((len(pos)-1)*pos.var(ddof=1) + (len(oth)-1)*oth.var(ddof=1)) / (len(pos)+len(oth)-2))
    d = float((pos.mean() - oth.mean()) / s) if s > 0 else 0
    a1_factors.append({
        'col': col, 'label': label,
        'cohens_d': round(d, 3), 'p_value': round(float(p), 4),
        'significant': bool(p < 0.05), 'tendency': bool(p < 0.10),
        'pos_mean': round(float(pos.mean()), 2),
        'oth_mean': round(float(oth.mean()), 2)
    })
a1_factors.sort(key=lambda x: abs(x['cohens_d']), reverse=True)

# ── 방법 B: GDP 분위별 내부 비교 ─────────────────────────
df['GDP_Q'] = pd.qcut(df['F1_GDP_per_capita'], 4, labels=['Q1','Q2','Q3','Q4'])
a1_quartile = []
for q in ['Q1','Q2','Q3','Q4']:
    qdf = df[df['GDP_Q'] == q]
    pos_n = (qdf['Deviance_Group'] == 'positive').sum()
    if pos_n < 3:
        continue
    for col, label in FACTORS.items():
        tmp = qdf[['Deviance_Group', col]].dropna()
        pos = tmp[tmp['Deviance_Group']=='positive'][col]
        oth = tmp[tmp['Deviance_Group']!='positive'][col]
        if len(pos) < 3 or len(oth) < 3:
            continue
        _, p = stats.mannwhitneyu(pos, oth, alternative='two-sided')
        if p < 0.10:
            s = qdf[col].dropna().std()
            d = float((pos.mean() - oth.mean()) / s) if s > 0 else 0
            a1_quartile.append({
                'quartile': q, 'label': label, 'col': col,
                'cohens_d': round(d, 3), 'p_value': round(float(p), 4),
                'significant': bool(p < 0.05),
                'pos_mean': round(float(pos.mean()), 2),
                'oth_mean': round(float(oth.mean()), 2)
            })

# ── A2: OLS 교호작용 회귀 ────────────────────────────────
import statsmodels.formula.api as smf
reg = df[['Learning_Poverty','F2_Gov_Edu_Exp','G_AVG_Governance','F1_GDP_per_capita']].dropna().copy()
for c in ['F2_Gov_Edu_Exp','G_AVG_Governance','F1_GDP_per_capita']:
    reg[c+'_z'] = (reg[c]-reg[c].mean())/reg[c].std()
reg['EduGov_Interaction'] = reg['F2_Gov_Edu_Exp_z'] * reg['G_AVG_Governance_z']
model_a2 = smf.ols('Learning_Poverty ~ F2_Gov_Edu_Exp_z + G_AVG_Governance_z + EduGov_Interaction + F1_GDP_per_capita_z', data=reg).fit()

# 부트스트래핑 (B=500)
np.random.seed(42)
boot_gov = []
for _ in range(500):
    samp = reg.sample(len(reg), replace=True)
    bm = smf.ols('Learning_Poverty ~ F2_Gov_Edu_Exp_z + G_AVG_Governance_z + EduGov_Interaction + F1_GDP_per_capita_z', data=samp).fit()
    boot_gov.append(bm.params['G_AVG_Governance_z'])
boot_ci = [round(float(np.percentile(boot_gov, 2.5)), 2), round(float(np.percentile(boot_gov, 97.5)), 2)]

a2_coefficients = []
coef_info = [
    ('F2_Gov_Edu_Exp_z',        '교육지출 β₁',           '교육지출 단독 효과 (GDP 통제)'),
    ('G_AVG_Governance_z',      '거버넌스 β₂',            '거버넌스 독립 효과 (GDP 통제)'),
    ('EduGov_Interaction',      '교육지출×거버넌스 β₃',   '교호작용 효과'),
    ('F1_GDP_per_capita_z',     'GDP 통제 β₄',           'GDP 통제 변수'),
]
for param, label, desc in coef_info:
    a2_coefficients.append({
        'param': param, 'label': label, 'description': desc,
        'beta': round(float(model_a2.params[param]), 3),
        'p_value': round(float(model_a2.pvalues[param]), 4),
        'ci_lower': round(float(model_a2.conf_int().loc[param, 0]), 2),
        'ci_upper': round(float(model_a2.conf_int().loc[param, 1]), 2),
        'significant': bool(model_a2.pvalues[param] < 0.05)
    })

# ── 국가 데이터 ──────────────────────────────────────────
countries = []
for _, row in df.iterrows():
    name = row['Country_Name']
    # 숫자형 필드 null 처리
    def safe(val):
        if pd.isna(val): return None
        return round(float(val), 3)

    countries.append({
        'iso3'           : iso_map.get(name, ''),
        'name'           : name,
        'region'         : region_map.get(name, '기타'),
        'lp'             : safe(row['Learning_Poverty']),
        'gdp'            : safe(row['F1_GDP_per_capita']),
        'log_gdp'        : safe(row['log_GDP']),
        'lp_predicted'   : safe(row['LP_Predicted']),
        'residual'       : safe(row['Residual']),
        'deviance_group' : row['Deviance_Group'],
        'governance'     : safe(row['G_AVG_Governance']),
        'physicians'     : safe(row['N4_Physicians_per_1000']),
        'teen_birth'     : safe(row['N2_Adolescent_Fertility']),
        'child_marriage' : safe(row['N5_Child_Marriage_Female']),
        'pupil_teacher'  : safe(row['F3_Pupil_Teacher_Ratio']),
        'under5_mort'    : safe(row['N1_Under5_Mortality']),
        'electricity'    : safe(row['N3_Electricity_Access']),
        'edu_exp'        : safe(row['F2_Gov_Edu_Exp']),
        'completion'     : safe(row['F7_Completion_Rate']),
    })

# ── TOP 5 이탈자 ─────────────────────────────────────────
top5 = df[df['Deviance_Group']=='positive'].nsmallest(5, 'Residual')[
    ['Country_Name','Learning_Poverty','LP_Predicted','Residual']
].copy()
top_deviants = []
for rank, (_, r) in enumerate(top5.iterrows(), 1):
    top_deviants.append({
        'rank': rank,
        'country': r['Country_Name'],
        'lp': round(float(r['Learning_Poverty']), 1),
        'predicted': round(float(r['LP_Predicted']), 1),
        'residual': round(float(r['Residual']), 1)
    })

# ── 요약 통계 ─────────────────────────────────────────────
out = {
    'summary': {
        'total_countries': int(len(df)),
        'avg_lp'         : round(float(df['Learning_Poverty'].mean()), 1),
        'max_lp'         : round(float(df['Learning_Poverty'].max()), 1),
        'min_lp'         : round(float(df['Learning_Poverty'].min()), 1),
        'max_country'    : str(df.loc[df['Learning_Poverty'].idxmax(), 'Country_Name']),
        'min_country'    : str(df.loc[df['Learning_Poverty'].idxmin(), 'Country_Name']),
        'n_positive_dev' : int((df['Deviance_Group']=='positive').sum()),
        'model_r2'       : round(float(r2), 3),
        'model_mae'      : round(float(mae), 2),
    },
    'countries'     : countries,
    'top_deviants'  : top_deviants,
    'a1_factors'    : a1_factors,
    'a1_quartile'   : a1_quartile,
    'a2': {
        'coefficients'  : a2_coefficients,
        'r2'            : round(float(model_a2.rsquared), 3),
        'boot_gov_ci'   : boot_ci,
        'edu_corr_lp'   : round(float(stats.spearmanr(
            df['F2_Gov_Edu_Exp'].dropna(),
            df.loc[df['F2_Gov_Edu_Exp'].notna(), 'Learning_Poverty']
        )[0]), 3),
    },
    'policy_recommendations': [
        {
            'id': 1, 'icon': '👩‍🎓',
            'title': 'Gender Gap 해소',
            'subtitle': '가장 강력한 독립 성공요인',
            'headline': '여아가 학교에 남아있게 하는 것이\n교과서를 나눠주는 것보다 중요하다',
            'evidence': '10대 출산율 Cohen\'s d = -0.92 (p=0.0001)',
            'actions': ['조혼 방지 법제화 지원', '여아 장학금 + 성교육 연계', '여아 중등교육 이수율을 ODA 성과지표 의무화']
        },
        {
            'id': 2, 'icon': '🏥',
            'title': '보건 역량 + 교사 수급',
            'subtitle': '예산보다 인력이 핵심',
            'headline': '의사 수와 교사 수는\n교육 예산보다 학습 빈곤을 더 직접적으로 줄인다',
            'evidence': '의사 수 d=+0.78 (p=0.005), 교사-학생 비율 d=-0.68 (p=0.007)',
            'actions': ['교육 지원에 아동 보건 인프라 연계 조건 포함', '교사 급여·처우 개선에 ODA 집중', '교사-학생 비율 목표: 1:20 이하']
        },
        {
            'id': 3, 'icon': '🏛️',
            'title': 'Governance 강화 선행',
            'subtitle': '교육 원조의 선행 조건',
            'headline': '교육 예산 증액은 단독으로 효과 없다\n거버넌스가 뒷받침될 때만 작동한다',
            'evidence': '거버넌스 β = -16.6 (p<0.001), 교육지출 β = +0.08 (p=0.97)',
            'actions': ['ODA 배분 시 WGI 점수 조건 연계', '교육 지원 패키지에 행정 역량 강화 필수 포함', '예산 집행 감독 체계 구축 우선 투자']
        },
        {
            'id': 4, 'icon': '🌍',
            'title': '성공 모델 벤치마킹',
            'subtitle': '같은 가난, 다른 교실',
            'headline': '스리랑카·베트남은 GDP 대비\n30%p 이상 낮은 학습 빈곤을 달성했다',
            'evidence': 'TOP 5 긍정적 이탈자 평균 -29%p (log-GDP 기준)',
            'actions': ['스리랑카·베트남을 교육 효율성 모범국으로 지정', '베냉: 최빈국 벤치마크 (Q1 최고 이탈자)', '성공요인(젠더·보건·교사) 집중 이전 전략']
        }
    ]
}

with open('../docs/dashboard_data_v2.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=str)

print(f"✅ dashboard_data_v2.json 생성 완료")
print(f"   국가 수: {len(countries)}")
print(f"   A1 성공요인: {len(a1_factors)}개")
print(f"   A1 분위별: {len(a1_quartile)}개 레코드")
print(f"   A2 계수: {len(a2_coefficients)}개")
print(f"   요약 통계: {out['summary']}")
