# -*- coding: utf-8 -*-
import pandas as pd
import os

# 데이터 로딩
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
df = pd.read_csv(os.path.join(DATA_DIR, 'WB_LPGD.csv'))

# 학습빈곤율 (Total) 데이터만 추출
lp_total = df[(df['INDICATOR'] == 'WB_LPGD_SE_LPV_PRIM') & (df['SEX_LABEL'] == 'Total')]

# 국가별 최신 데이터 연도 추출
latest_years = lp_total.groupby('REF_AREA_LABEL')['TIME_PERIOD'].max()

print("="*50)
print("국가별 최신 데이터(Latest Available Year) 연도 분포")
print("="*50)

print(f"\n[1] 대상 국가 수: {len(latest_years)}개국")

# 최신 연도 분포
year_dist = latest_years.value_counts().sort_index()
print(f"\n[2] 각 국가의 '가장 최근 조사 연도' 분포:")
for year, count in year_dist.items():
    print(f"  - {year}년이 가장 최신인 국가: {count}개국")

# 2010년 이전이 최신인 국가들 확인
old_countries = latest_years[latest_years < 2010].sort_values()
print(f"\n[3] 2010년 이전 데이터가 가장 최신인 국가 ({len(old_countries)}개국):")
for country, year in old_countries.items():
    print(f"  - {country}: {year}년")
