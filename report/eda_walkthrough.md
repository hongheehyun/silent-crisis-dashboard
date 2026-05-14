# 데이터 전처리 및 EDA 결과 보고

`project_spec.md`의 §2.3과 §3.1에 명시된 지침에 따라 전처리 파이프라인과 탐색적 데이터 분석(EDA)을 모두 성공적으로 완료했습니다.

## 1. 데이터 전처리 완료 내역
`scripts/preprocess_data.py`를 실행하여 다음 작업을 완료하고 `data/processed/model_ready.csv`를 생성했습니다.

- **맥락 변수 결합**: World Bank API를 통해 분석 대상 105개국의 지역(Region) 및 소득그룹(Income Level) 정보를 가져와 병합했습니다.
- **70% 결측치 룰 적용**: 독립변수의 누락이 70% 이상인 2개국을 제외하여 **총 103개국**을 최종 대상 정예 데이터로 확보했습니다.
- **K-NN Imputation**: 결측치가 일부 있던 피처들(`F4_Stunting_Rate` 등)에 대해, 지역과 소득 수준이 유사한 이웃 국가(K=5)의 값을 참조해 결측치를 100% 보정했습니다.
- **종속변수 변환**: `Learning_Poverty` 컬럼에 Log1p 변환을 적용한 `Learning_Poverty_Log` 파생 변수를 성공적으로 생성했습니다.

## 2. 탐색적 데이터 분석 (EDA) 시각화 결과
`scripts/eda_analysis.py`를 통해 전처리된 모델 학습용 데이터를 시각화했습니다.

### 종속변수 분포 (Log 변환 효과)
오른쪽으로 치우쳐(Right-skewed) 있던 학습빈곤율 데이터가 로그 변환 이후 선형성 가정을 충족하기 쉬운 정규분포에 더 가까운 형태로 다듬어졌습니다.
![종속변수 분포도](../images/eda_target_distribution.png)

### 지역 및 소득 수준별 격차 (Boxplot & Violinplot)
사하라 이남 아프리카(Sub-Saharan Africa) 지역과 저소득 국가(Low income)에서 학습빈곤율이 극심하게 높게 형성되어 있음을 명확히 확인할 수 있습니다.
![지역별 분포](../images/eda_region_distribution.png)
![소득수준별 분포](../images/eda_income_distribution.png)

### 상관관계 히트맵 (Spearman)
스피어만 상관계수 분석 결과, 예상대로 아동 발육부진율(`F4_Stunting_Rate`)은 학습빈곤율과 강한 양의 상관관계(약 0.72)를 보였으며, 인터넷 사용률(`F5_Internet_Usage`)과 1인당 GDP(`F1`)는 강한 음의 상관관계(-0.83, -0.76)를 보였습니다. 
*주의사항에서 언급했던 수료율(`F7`), 순등록률(`F6`)도 매우 강한 음의 상관관계를 보이므로, 추후 머신러닝 단계에서 VIF 및 변수 중요도 분석을 면밀히 해야 함을 재확인했습니다.*
![상관관계 히트맵](../images/eda_correlation_heatmap.png)

---
> [!NOTE]
> EDA 상세 서술 리포트는 `model_eda_report.md` 파일에 저장되어 있습니다. 이제 데이터가 완벽하게 준비되었으므로, **§3.2 Random Forest를 활용한 위험 요인 식별(모델링)** 단계로 넘어갈 준비가 되었습니다!
