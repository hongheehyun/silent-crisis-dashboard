# -*- coding: utf-8 -*-
"""
탐색적 데이터 분석 (EDA) 스크립트 (eda_analysis.py)
1. 타겟 변수 변환 전/후 분포 시각화
2. 지역/소득수준별 Boxplot & Violinplot
3. 상관관계 히트맵 생성
4. EDA 리포트 초안 자동 생성
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib
import os

def run_eda():
    print("="*60)
    print("탐색적 데이터 분석 (EDA) 파이프라인 시작")
    print("="*60)

    # 경로 설정
    BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
    IN_FILE = os.path.join(BASE_DIR, 'data', 'processed', 'model_ready.csv')
    IMG_DIR = os.path.join(BASE_DIR, 'images')
    REPORT_DIR = os.path.join(BASE_DIR, 'report')
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    print("[1] 데이터 로드 중...")
    df = pd.read_csv(IN_FILE)
    
    # seaborn 스타일 세팅
    sns.set_theme(style="whitegrid")
    # koreanize_matplotlib이 폰트 설정을 덮어쓰므로 이후에는 한글 출력 가능

    # ---------------------------------------------------------
    # 도표 1: 변환 전/후 학습빈곤율 분포 비교
    # ---------------------------------------------------------
    print("[2] 타겟 변수 분포 시각화 생성...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    sns.histplot(df['Learning_Poverty'], kde=True, ax=axes[0], color='salmon')
    axes[0].set_title('변환 전 학습빈곤율 분포 (Right-Skewed)')
    axes[0].set_xlabel('학습빈곤율 (%)')
    
    sns.histplot(df['Learning_Poverty_Log'], kde=True, ax=axes[1], color='skyblue')
    axes[1].set_title('Log1p 변환 후 학습빈곤율 분포 (Learning_Poverty_Log)')
    axes[1].set_xlabel('Log(학습빈곤율)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'eda_target_distribution.png'), dpi=150)
    plt.close()

    # ---------------------------------------------------------
    # 도표 2: 지역/소득그룹별 Boxplot & Violinplot
    # ---------------------------------------------------------
    print("[3] 맥락변수(Region, IncomeLevel)별 분포 시각화 생성...")
    
    # 2-1: Region별
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    sns.boxplot(x='Learning_Poverty', y='C1_Region', data=df, ax=axes[0], palette='Set2')
    axes[0].set_title('지역(Region)별 학습빈곤율 분포 (Box Plot)')
    
    sns.violinplot(x='Learning_Poverty', y='C1_Region', data=df, ax=axes[1], palette='Set2', inner='quartile')
    axes[1].set_title('지역(Region)별 학습빈곤율 분포 (Violin Plot)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'eda_region_distribution.png'), dpi=150)
    plt.close()
    
    # 2-2: IncomeLevel별
    fig, axes = plt.subplots(2, 1, figsize=(10, 10))
    sns.boxplot(x='Learning_Poverty', y='C2_IncomeLevel', data=df, ax=axes[0], palette='Pastel1')
    axes[0].set_title('소득그룹(Income Level)별 학습빈곤율 분포 (Box Plot)')
    
    sns.violinplot(x='Learning_Poverty', y='C2_IncomeLevel', data=df, ax=axes[1], palette='Pastel1', inner='quartile')
    axes[1].set_title('소득그룹(Income Level)별 학습빈곤율 분포 (Violin Plot)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'eda_income_distribution.png'), dpi=150)
    plt.close()

    # ---------------------------------------------------------
    # 도표 3: 상관관계 히트맵 (Correlation Heatmap)
    # ---------------------------------------------------------
    print("[4] 변수 간 상관관계 히트맵 생성...")
    cols_to_corr = ['Learning_Poverty_Log', 'Learning_Poverty'] + [c for c in df.columns if c.startswith('F')]
    corr_matrix = df[cols_to_corr].corr(method='spearman') # 스피어만 상관계수 사용 (비선형 및 이상치 강건)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1, square=True)
    plt.title('학습빈곤율 및 독립변수 간 스피어만(Spearman) 상관계수')
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'eda_correlation_heatmap.png'), dpi=150)
    plt.close()

    # ---------------------------------------------------------
    # 마크다운 리포트 생성
    # ---------------------------------------------------------
    print("[5] EDA 결과 리포트 초안 작성 중...")
    report_content = f"""# 분석 준비 모델 (Model-Ready) 탐색적 데이터 분석 (EDA) 리포트

## 1. 개요
본 리포트는 전처리(결측치 KNN 보정 및 메타데이터 결합)가 완료된 {len(df)}개국의 데이터를 바탕으로 작성되었습니다.

## 2. 주요 시각화 결과

### 2.1 종속변수 분포 및 변환 효과
학습빈곤율은 원본 데이터에서 오른쪽으로 긴 꼬리(Right-skewed)를 가지는 비대칭 분포였습니다. 모델링 성능 향상 및 선형성 확보를 위해 Log1p 변환을 적용한 결과, 분포가 정규분포에 더 가깝게 완화되었습니다.
![타겟 변수 분포](../images/eda_target_distribution.png)

### 2.2 지역 및 소득 수준별 격차
소득 수준(Income Level)이 낮을수록 학습빈곤율의 중앙값이 뚜렷하게 상승하며, 특히 사하라 이남 아프리카(Sub-Saharan Africa)와 남아시아(South Asia) 지역의 학습빈곤율이 다른 지역 대비 극명하게 높음을 확인할 수 있습니다.
![지역별 분포](../images/eda_region_distribution.png)
![소득그룹별 분포](../images/eda_income_distribution.png)

### 2.3 상관관계 분석 (Spearman Correlation)
종속변수(`Learning_Poverty_Log`)와 가장 강한 상관관계를 보이는 독립변수 그룹을 식별하기 위해 스피어만 상관계수를 도출했습니다.
![상관관계 히트맵](../images/eda_correlation_heatmap.png)
"""
    with open(os.path.join(REPORT_DIR, 'model_eda_report.md'), 'w', encoding='utf-8') as f:
        f.write(report_content)

    print("  -> 완료! 시각화 이미지는 images/ 폴더에, 리포트는 report/ 에 저장되었습니다.")
    print("="*60)

if __name__ == "__main__":
    run_eda()
