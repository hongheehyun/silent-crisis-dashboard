# -*- coding: utf-8 -*-
import pandas as pd
import os

# 데이터 로딩
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
df = pd.read_csv(os.path.join(DATA_DIR, 'WB_LPGD.csv'))

# 학습빈곤율 데이터만 추출
lp_df = df[df['INDICATOR'] == 'WB_LPGD_SE_LPV_PRIM'].copy()

print("="*50)
print("학습빈곤율(SE_LPV_PRIM) 결측 및 분포 분석")
print("="*50)

print(f"\n[1] 전체 건수: {len(lp_df)}건")

# 성별 라벨 분할 확인
sex_counts = lp_df['SEX_LABEL'].value_counts()
print(f"\n[2] 성별(SEX_LABEL)별 건수:")
for k, v in sex_counts.items():
    print(f"  - {k}: {v}건")

# Total 성별 데이터만 분리해서 국가수 확인
lp_total = lp_df[lp_df['SEX_LABEL'] == 'Total']
countries_with_data = lp_total['REF_AREA_LABEL'].nunique()
print(f"\n[3] Total(통합) 데이터 기준 국가 수: {countries_with_data}개국")

# 국가별 관측 연도 개수 분포
obs_per_country = lp_total.groupby('REF_AREA_LABEL').size()
print(f"\n[4] 국가별 데이터 보고 횟수 (Total 기준, 요약):")
print(f"  - 최소 보고 횟수: {obs_per_country.min()}회")
print(f"  - 최대 보고 횟수: {obs_per_country.max()}회")
print(f"  - 평균 보고 횟수: {obs_per_country.mean():.1f}회")

print("\n  [국가별 보고 횟수 분포]")
vc = obs_per_country.value_counts().sort_index()
for k, v in vc.items():
    print(f"    - {k}회 보고한 국가: {v}개국")

# 연도별 데이터 개수 확인
year_counts = lp_total['TIME_PERIOD'].value_counts().sort_index()
print(f"\n[5] 연도별 데이터 수집 건수 (Total 기준):")
for year, count in year_counts.items():
    print(f"  - {year}년: {count}건")
