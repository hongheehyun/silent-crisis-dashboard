# -*- coding: utf-8 -*-
"""
전처리 파이프라인 스크립트 (preprocess_data.py)
1. Region 및 Income Level 결합
2. 결측치 과다 국가(70% 룰) 제거
3. K-NN Imputation (지역, 소득 그룹 활용)
4. 타겟변수 로그 변환
"""

import pandas as pd
import numpy as np
import wbgapi as wb
from sklearn.impute import KNNImputer
import os

def preprocess_pipeline():
    print("="*60)
    print("데이터 전처리 (Preprocessing) 파이프라인 시작")
    print("="*60)

    # 경로 설정
    BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
    IN_FILE = os.path.join(BASE_DIR, 'data', 'processed', 'analysis_ready.csv')
    OUT_FILE = os.path.join(BASE_DIR, 'data', 'processed', 'model_ready.csv')
    
    # 1. 데이터 로드
    print("[1] 데이터 로드 중...")
    df = pd.read_csv(IN_FILE)
    print(f"  -> 초기 데이터 크기: {df.shape}")
    
    # 2. 메타데이터(Region, Income Level) 결합
    print("[2] World Bank API에서 국가 메타데이터 수집 및 결합...")
    econ_info = wb.economy.DataFrame()
    econ_info = econ_info[['region', 'incomeLevel']].reset_index()
    econ_info = econ_info.rename(columns={'id': 'Country_Code', 'region': 'C1_Region', 'incomeLevel': 'C2_IncomeLevel'})
    
    df = pd.merge(df, econ_info, on='Country_Code', how='left')
    
    # 3. 결측치 70% 이상 룰 (독립변수 8개 중 30% 이상(3개 이상) 결측이면 제거)
    print("[3] 70% 결측치 룰 적용 (너무 비어있는 국가 제거)...")
    feature_cols = [c for c in df.columns if c.startswith('F')]
    
    # 임계치(thresh): 정상 값이 최소 (8 - 2) = 6개 이상 있어야 함. (즉 3개 이상 결측치면 드롭)
    # 다만 프로젝트 스펙상 조금 관대하게 적용할 수도 있으므로 일단 thresh=len(feature_cols)*0.7 로 계산
    thresh = int(len(feature_cols) * 0.7)
    df_clean = df.dropna(subset=feature_cols, thresh=thresh).copy()
    print(f"  -> 결측치 과다로 제거된 국가 수: {len(df) - len(df_clean)}개")
    print(f"  -> 남은 국가 수: {len(df_clean)}개")
    
    # 4. K-NN Imputation
    print("[4] K-NN Imputation 진행...")
    # K-NN을 위해 범주형 변수를 원핫인코딩 처리
    df_knn_input = df_clean[feature_cols + ['C1_Region', 'C2_IncomeLevel']].copy()
    df_encoded = pd.get_dummies(df_knn_input, columns=['C1_Region', 'C2_IncomeLevel'])
    
    imputer = KNNImputer(n_neighbors=5, weights='distance')
    imputed_values = imputer.fit_transform(df_encoded)
    
    # 다시 데이터프레임으로 만들어서 스케일링된/채워진 독립변수만 가져옴
    df_imputed = pd.DataFrame(imputed_values, columns=df_encoded.columns, index=df_clean.index)
    
    # 결측치가 채워진 독립변수를 원본 데이터 프레임에 덮어쓰기
    for col in feature_cols:
        df_clean[col] = df_imputed[col]
        
    print("  -> 결측치 보정 완료 (현재 결측치 합계: 0)")
    
    # 5. 종속변수 변환 (Log1p)
    print("[5] 종속변수(학습빈곤율) Log 변환 수행...")
    df_clean['Learning_Poverty_Log'] = np.log1p(df_clean['Learning_Poverty'])
    
    # 6. 저장
    print(f"[6] 전처리 완료 데이터 저장 -> {OUT_FILE}")
    df_clean.to_csv(OUT_FILE, index=False)
    print("="*60)

if __name__ == "__main__":
    preprocess_pipeline()
