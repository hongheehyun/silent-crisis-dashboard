# -*- coding: utf-8 -*-
"""
WB_LPGD 데이터셋 EDA - 1단계: 데이터 탐색 및 기술통계
"""
import pandas as pd
import numpy as np
import json
import glob
import os
import warnings
warnings.filterwarnings('ignore')

# === 데이터 로딩 ===
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
IMG_DIR = os.path.join(os.path.dirname(__file__), '..', 'images')
os.makedirs(IMG_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(DATA_DIR, 'WB_LPGD.csv'))

# === JSON 메타데이터에서 지표 설명 추출 ===
indicator_info = {}
for f in sorted(glob.glob(os.path.join(DATA_DIR, 'WB_LPGD_*.json'))):
    data = json.load(open(f, encoding='utf-8'))
    sd = data.get('series_description', {})
    code = 'WB_LPGD_' + os.path.basename(f).replace('WB_LPGD_','').replace('.json','')
    indicator_info[code] = {
        'name': sd.get('name', 'N/A'),
        'definition': sd.get('definition_long', sd.get('definition_short', 'N/A')),
        'unit': sd.get('measurement_unit', 'N/A'),
    }

print("="*70)
print("WB_LPGD (Learning Poverty Global Database) 탐색적 데이터 분석")
print("="*70)

# 1. 기본 미리보기
print("\n[1] 데이터 미리보기 (상위 5행)")
print(df.head().to_string())
print("\n[1-2] 데이터 미리보기 (하위 5행)")
print(df.tail().to_string())

# 2. 기본 정보
print("\n[2] 데이터 기본 정보")
print(f"  행 수: {len(df):,}")
print(f"  열 수: {len(df.columns)}")
print(f"  컬럼 목록: {list(df.columns)}")
print("\n  데이터 타입:")
for col in df.columns:
    print(f"    {col}: {df[col].dtype} (결측: {df[col].isna().sum()})")

# 3. 중복 확인
dup = df.duplicated().sum()
print(f"\n[3] 중복 레코드 수: {dup}")

# 4. 지표 설명 (JSON 기반)
print("\n[4] 지표별 설명 (JSON 메타데이터)")
for code, info in indicator_info.items():
    print(f"\n  [{code}]")
    print(f"    이름: {info['name']}")
    print(f"    정의: {info['definition'][:200]}")
    print(f"    단위: {info['unit']}")

# 5. 주요 범주형 변수 분포
print("\n[5] 주요 범주형 변수 분포")
cat_cols = ['INDICATOR', 'REF_AREA_LABEL', 'SEX_LABEL', 'AGE_LABEL', 'URBANISATION_LABEL',
            'UNIT_MEASURE_LABEL', 'COMP_BREAKDOWN_1_LABEL']
for col in cat_cols:
    if col in df.columns:
        vc = df[col].value_counts()
        print(f"\n  {col} (고유값: {df[col].nunique()})")
        for v, c in vc.head(10).items():
            print(f"    {v}: {c:,}")

# 6. 수치형 변수 기술통계
print("\n[6] 수치형 변수 기술통계")
num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
print(df[num_cols].describe().to_string())

# 7. 지표별 OBS_VALUE 기술통계
print("\n[7] 지표별 OBS_VALUE 기술통계")
for ind in df['INDICATOR'].unique():
    sub = df[df['INDICATOR'] == ind]['OBS_VALUE'].dropna()
    if len(sub) > 0:
        ind_name = indicator_info.get(ind, {}).get('name', ind)
        print(f"\n  {ind} ({ind_name})")
        print(f"    건수={len(sub):,}, 평균={sub.mean():.2f}, 중앙값={sub.median():.2f}, "
              f"표준편차={sub.std():.2f}, 최솟값={sub.min():.2f}, 최댓값={sub.max():.2f}")

print("\n✅ 1단계 탐색 완료")
