# -*- coding: utf-8 -*-
"""
3.2 단계 - Random Forest 모델 훈련 및 1차 스크리닝 스크립트 (train_rf_model.py)
1. VIF(다중공선성) 검증 및 내생성 변수 제거
2. Random Forest Regressor 5-Fold Cross Validation
3. 1차 Feature Importance 추출 및 시각화
4. 학습된 모델 객체 저장
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import joblib

from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_squared_error, r2_score

# 한글 폰트 관련 경고 무시 및 기본 설정 (koreanize_matplotlib이 있다면 자동 적용됨)
import warnings
warnings.filterwarnings('ignore')

def calculate_vif(X):
    X_const = add_constant(X)
    vif_data = pd.DataFrame()
    vif_data["Feature"] = X_const.columns
    vif_data["VIF"] = [variance_inflation_factor(X_const.values, i) for i in range(X_const.shape[1])]
    vif_data = vif_data[vif_data['Feature'] != 'const'] # 상수항은 제외하고 리턴
    return vif_data.sort_values("VIF", ascending=False).reset_index(drop=True)

def main():
    print("="*60)
    print("Random Forest 모델 학습 및 1차 중요도 분석 파이프라인")
    print("="*60)

    # 경로 설정
    BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
    IN_FILE = os.path.join(BASE_DIR, 'data', 'processed', 'model_ready.csv')
    IMG_DIR = os.path.join(BASE_DIR, 'images')
    MODEL_DIR = os.path.join(BASE_DIR, 'data', 'processed')
    
    # 데이터 로드
    print("\n[1] 데이터 로드 중...")
    df = pd.read_csv(IN_FILE)
    
    # 독립변수 및 종속변수 정의
    feature_cols = [c for c in df.columns if c.startswith('F')]
    X = df[feature_cols]
    y = df['Learning_Poverty_Log'] # 로그 변환된 학습빈곤율 타겟
    
    # VIF 계산 및 내생성 변수 제거
    print("\n[2] VIF 다중공선성 검증 중...")
    vif_df = calculate_vif(X)
    print("  [초기 VIF 결과]")
    print(vif_df)
    
    # VIF 임계치 설정 (통상 10, 보수적으로 5 이상이면 매우 높음)
    # EDA 분석에서 예상한 대로, 결측치를 채운 F6(순등록률)과 F7(수료율)의 VIF가 극단적으로 높게 나올 수 있습니다.
    # 안전한 모델링을 위해 VIF가 30 이상인 극단적 변수는 내생성 변수로 간주하고 제거합니다.
    VIF_THRESHOLD = 30
    features_to_drop = vif_df[vif_df['VIF'] > VIF_THRESHOLD]['Feature'].tolist()
    
    if features_to_drop:
        print(f"\n  ⚠️ VIF {VIF_THRESHOLD} 초과로 인해 제거되는 내생성 의심 변수: {features_to_drop}")
        X_selected = X.drop(columns=features_to_drop)
    else:
        print("\n  -> 제거할 만큼 극단적인 다중공선성을 가진 변수가 없습니다.")
        X_selected = X.copy()
        
    print(f"  -> 최종 선택된 피처 수: {len(X_selected.columns)}개")

    # VIF 시각화 저장
    plt.figure(figsize=(10, 6))
    sns.barplot(x='VIF', y='Feature', data=vif_df, palette='viridis')
    plt.axvline(x=10, color='r', linestyle='--', label='VIF=10 (경고 선)')
    plt.axvline(x=VIF_THRESHOLD, color='darkred', linestyle='-', label=f'VIF={VIF_THRESHOLD} (제거 선)')
    plt.title('독립변수 분산팽창지수 (Variance Inflation Factor)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'vif_analysis.png'), dpi=150)
    plt.close()

    # Random Forest 교차 검증 (5-Fold CV)
    print("\n[3] Random Forest 모델 5-Fold 교차 검증 중...")
    rf_model = RandomForestRegressor(n_estimators=200, random_state=42, max_depth=7, min_samples_leaf=3)
    
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_r2 = cross_val_score(rf_model, X_selected, y, cv=kf, scoring='r2')
    cv_neg_mse = cross_val_score(rf_model, X_selected, y, cv=kf, scoring='neg_mean_squared_error')
    cv_rmse = np.sqrt(-cv_neg_mse)
    
    print(f"  -> 교차검증 R² 스코어: {cv_r2.mean():.4f} (±{cv_r2.std():.4f})")
    print(f"  -> 교차검증 RMSE: {cv_rmse.mean():.4f} (±{cv_rmse.std():.4f})")
    
    # 전체 데이터로 훈련 및 중요도 추출
    print("\n[4] 전체 데이터 모델 학습 및 Feature Importance 추출 중...")
    rf_model.fit(X_selected, y)
    
    importances = rf_model.feature_importances_
    imp_df = pd.DataFrame({'Feature': X_selected.columns, 'Importance': importances})
    imp_df = imp_df.sort_values('Importance', ascending=False)
    
    print("  [Random Forest 1차 중요도]")
    print(imp_df)
    
    # 중요도 시각화
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Importance', y='Feature', data=imp_df, palette='magma')
    plt.title('Random Forest Feature Importance (Gini/MSE 기반)')
    plt.xlabel('상대적 중요도')
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'rf_feature_importance.png'), dpi=150)
    plt.close()
    
    # 모델 저장 (다음 단계 SHAP 분석을 위함)
    print("\n[5] 학습된 모델 저장 중...")
    model_data = {
        'model': rf_model,
        'features': X_selected.columns.tolist()
    }
    joblib.dump(model_data, os.path.join(MODEL_DIR, 'rf_model.pkl'))
    print("  -> rf_model.pkl 저장 완료")
    print("="*60)

if __name__ == "__main__":
    main()
