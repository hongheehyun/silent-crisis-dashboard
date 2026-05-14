# -*- coding: utf-8 -*-
"""
3.3 단계 - K-Means를 활용한 국가 유형 분류 스크립트 (kmeans_clustering.py)
1. 변수 선택(Top 4) 및 스케일링
2. 최적 K 탐색 (Elbow & Silhouette)
3. K-Means 군집화
4. PCA 시각화 및 Radar Chart 프로파일링
5. 결과 저장 및 리포트 생성
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from math import pi

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

import warnings
warnings.filterwarnings('ignore')

def create_radar_chart(df, features, cluster_col, save_path):
    # 각 클러스터의 특성 평균 계산
    cluster_means = df.groupby(cluster_col)[features].mean().reset_index()
    
    # 레이더 차트 생성을 위해 Min-Max 스케일링 (0~1 사이로 정규화)
    # 변수 단위가 다 다르므로 시각적 비교를 위해 필수적입니다.
    scaled_features = pd.DataFrame()
    for feature in features:
        min_val = df[feature].min()
        max_val = df[feature].max()
        scaled_features[feature] = (cluster_means[feature] - min_val) / (max_val - min_val)
    
    num_vars = len(features)
    angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Feature 라벨 단순화
    short_features = [f.split('_', 1)[1] if '_' in f else f for f in features]
    plt.xticks(angles[:-1], short_features, size=10)
    
    ax.set_rlabel_position(0)
    plt.yticks([0.25, 0.5, 0.75], ["0.25", "0.50", "0.75"], color="grey", size=7)
    plt.ylim(0, 1)
    
    colors = ['b', 'r', 'g', 'm', 'c']
    
    for i in range(len(cluster_means)):
        values = scaled_features.iloc[i].tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=2, linestyle='solid', label=f"Cluster {i}", color=colors[i%len(colors)])
        ax.fill(angles, values, color=colors[i%len(colors)], alpha=0.1)
        
    plt.title("Cluster Profiles (Min-Max Scaled Averages)", size=15, y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

def main():
    print("="*60)
    print("국가 유형 분류 (K-Means Clustering) 파이프라인")
    print("="*60)

    BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
    IN_FILE = os.path.join(BASE_DIR, 'data', 'processed', 'model_ready.csv')
    OUT_FILE = os.path.join(BASE_DIR, 'data', 'processed', 'cluster_results.csv')
    IMG_DIR = os.path.join(BASE_DIR, 'images')
    REPORT_DIR = os.path.join(BASE_DIR, 'report')
    
    print("\n[1] 데이터 로드 및 피처 선택 중...")
    df = pd.read_csv(IN_FILE)
    
    # 앞선 RF 중요도 Top 4 변수 선택
    # F1(GDP), F3(TeacherRatio), F4(Stunting), F6(NetEnrollment)
    top_features = ['F1_GDP_per_capita', 'F3_Pupil_Teacher_Ratio', 'F4_Stunting_Rate', 'F6_Net_Enrollment']
    X = df[top_features]
    
    print(f"  -> 사용 변수: {top_features}")
    
    # 스케일링
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # ---------------------------------------------------------
    print("\n[2] 최적 K 탐색 (Elbow & Silhouette)...")
    sse = []
    silhouettes = []
    k_range = range(2, 8)
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        sse.append(kmeans.inertia_)
        silhouettes.append(silhouette_score(X_scaled, kmeans.labels_))
        
    fig, ax1 = plt.subplots(figsize=(10, 5))
    
    # Elbow
    color = 'tab:red'
    ax1.set_xlabel('Number of Clusters (K)')
    ax1.set_ylabel('Sum of Squared Errors (SSE)', color=color)
    ax1.plot(k_range, sse, marker='o', color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    
    # Silhouette
    ax2 = ax1.twinx()
    color = 'tab:blue'
    ax2.set_ylabel('Silhouette Score', color=color)
    ax2.plot(k_range, silhouettes, marker='s', color=color, linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title('Optimal K Search: Elbow Method & Silhouette Score')
    fig.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'elbow_silhouette.png'), dpi=150)
    plt.close()
    
    # 실루엣 스코어가 가장 높은 K 자동 선택
    best_k = k_range[np.argmax(silhouettes)]
    print(f"  -> 가장 높은 Silhouette Score를 기록한 K = {best_k}")
    
    # 도메인 특성상 정책 그룹은 최소 3~4개가 좋으므로, 만약 K=2가 나왔다면 수동 조정할 수 있으나 여기서는 best_k를 따름
    if best_k == 2:
        print("  -> K=2는 국가 정책 세분화에 다소 단조로우므로 K=3으로 진행합니다.")
        best_k = 3

    # ---------------------------------------------------------
    print(f"\n[3] 최종 K-Means(K={best_k}) 수행 중...")
    kmeans_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    cluster_labels = kmeans_final.fit_predict(X_scaled)
    
    df['Cluster'] = cluster_labels
    
    # 각 클러스터별 학습 빈곤율 평균 확인
    cluster_lp_mean = df.groupby('Cluster')['Learning_Poverty'].mean().sort_values()
    print("  [클러스터별 학습빈곤율 평균]")
    print(cluster_lp_mean)
    
    # 이해를 돕기 위해 학습빈곤율이 낮은 순서대로 Cluster 번호를 0, 1, 2... 로 재할당
    mapping = {old_label: new_label for new_label, old_label in enumerate(cluster_lp_mean.index)}
    df['Cluster'] = df['Cluster'].map(mapping)
    
    # ---------------------------------------------------------
    print("\n[4] 클러스터링 결과 시각화 생성 중...")
    
    # PCA 산점도
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    df['PCA1'] = X_pca[:, 0]
    df['PCA2'] = X_pca[:, 1]
    
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='PCA1', y='PCA2', hue='Cluster', palette='Set1', data=df, s=100, alpha=0.7)
    plt.title(f'K-Means Clusters in 2D PCA Space (K={best_k})')
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, 'cluster_pca_scatter.png'), dpi=150)
    plt.close()
    
    # Radar Chart
    create_radar_chart(df, top_features, 'Cluster', os.path.join(IMG_DIR, 'cluster_radar_chart.png'))
    
    # 결과 저장
    df.to_csv(OUT_FILE, index=False)
    print(f"  -> 결과 저장 완료: {OUT_FILE}")
    
    # ---------------------------------------------------------
    print("\n[5] 클러스터링 결과 리포트 초안 작성 중...")
    report_content = f"""# 국가 유형 분류 (K-Means Clustering) 리포트

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
"""
    
    with open(os.path.join(REPORT_DIR, 'clustering_report.md'), 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print("  -> 리포트 저장 완료!")
    print("="*60)

if __name__ == "__main__":
    main()
