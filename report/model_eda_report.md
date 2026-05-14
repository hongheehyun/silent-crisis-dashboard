# 분석 준비 모델 (Model-Ready) 탐색적 데이터 분석 (EDA) 리포트

## 1. 개요
본 리포트는 전처리(결측치 KNN 보정 및 메타데이터 결합)가 완료된 103개국의 데이터를 바탕으로 작성되었습니다.

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
