# 국가 유형 분류 (K-Means Clustering) 리포트

## 1. 개요
Random Forest 모델을 통해 확인된 핵심 위험 요인 Top 4 변수(`F1`, `F3`, `F4`, `F6`)를 기반으로 103개국을 클러스터링했습니다. '차원의 저주'를 피하고 해석력을 높이기 위해 변수를 축소하고 표준화(StandardScaler)한 후 K-Means 알고리즘을 적용했습니다.

## 2. 최적 군집 수 (K) 도출
Elbow Method (SSE)와 Silhouette Score를 종합적으로 고려하여 클러스터 수를 설정했습니다.
![Elbow & Silhouette](../images/elbow_silhouette.png)

## 3. 클러스터 시각화

### 3.1 2D 공간 분리도 (PCA Scatter Plot)
다차원의 변수를 PCA로 2차원으로 축소한 결과, 각 군집이 뚜렷하게 분리되어 있는 양상을 띱니다.
![PCA Scatter](../images/cluster_pca_scatter.png)

### 3.2 군집별 특성 프로파일링 (Radar Chart)
각 군집이 가진 4가지 인프라 지표의 강점과 약점을 파악하기 위해 레이더 차트를 생성했습니다. 중심부(0)에 가까울수록 해당 지표의 값이 낮음을 의미합니다.
![Radar Chart](../images/cluster_radar_chart.png)

## 4. 군집별 해석 (Cluster Profiling)
학습빈곤율(`Learning_Poverty`)이 낮은 순서대로 Cluster 0부터 번호를 재할당했습니다.

- **Cluster 0 (안정 및 우수 그룹)**
  - 가장 낮은 학습빈곤율 유지. 1인당 GDP가 매우 높고, 교사 1인당 학생 수 및 아동발육부진율이 가장 낮음. 
  - 교육 인프라와 경제력이 모두 훌륭한 선진국형 그룹.

- **Cluster 1 (보건 및 경제적 과도기 그룹)**
  - 중간 수준의 학습빈곤율. GDP는 낮으나 순등록률(F6)이 어느 정도 받쳐주는 개발도상국 그룹.

- **Cluster 2 (다중 결핍 심각 그룹)**
  - 가장 높은 학습빈곤율 기록. 1인당 GDP 최하위, 초등학교 순등록률 바닥, 교사당 학생 수 최다, 발육부진율 최고. 
  - 즉, 경제적 절대 빈곤과 기본 보건 인프라 붕괴가 겹친 집중 타겟 국가군.

*자세한 군집별 데이터는 `data/processed/cluster_results.csv`에 저장되어 있습니다.*
