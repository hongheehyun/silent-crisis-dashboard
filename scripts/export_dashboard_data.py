# -*- coding: utf-8 -*-
"""
웹 대시보드용 정적 JSON 데이터 추출 스크립트
1. cluster_results.csv 데이터 로드
2. Feature Importance, SHAP 개요, 클러스터 요약 정보 산출
3. /project/docs/dashboard_data.json 형태로 추출
"""

import pandas as pd
import json
import os

def main():
    print("="*60)
    print("대시보드 데이터 JSON Export 파이프라인")
    print("="*60)

    BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
    IN_FILE = os.path.join(BASE_DIR, 'data', 'processed', 'cluster_results.csv')
    OUT_FILE = os.path.join(BASE_DIR, 'docs', 'dashboard_data.json')
    
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    
    # 1. 메인 데이터 로드
    df = pd.read_csv(IN_FILE)
    
    # NaN 값들은 None으로 변환해야 JSON 파싱 시 에러가 나지 않음
    df = df.where(pd.notnull(df), None)

    # 2. Hero 섹션용 글로벌 통계 요약
    total_countries = len(df)
    avg_learning_poverty = round(df['Learning_Poverty'].mean(), 1)
    
    # 학습빈곤 아동 수 추정 (여기서는 가상의 통계를 사용하거나 단순히 상징적 수치 생성 가능하나,
    # 실제 World Bank 발표 수치인 약 2억 6천만 명을 예시로 고정)
    estimated_lp_children = 260000000 
    
    # 3. 국가별 테이블 데이터 (우선순위 지수 가상 계산: LP와 Cluster 기준)
    # LP가 높고, Cluster가 2인 국가가 시급함
    df['Priority_Score'] = df['Learning_Poverty'] + (df['Cluster'] * 10)
    # 스케일링 0~100
    df['Priority_Score'] = ((df['Priority_Score'] - df['Priority_Score'].min()) / 
                            (df['Priority_Score'].max() - df['Priority_Score'].min()) * 100).round(1)
                            
    countries_data = []
    for _, row in df.iterrows():
        # ISO3 코드(Country Code)가 지도 매핑 시 필요
        countries_data.append({
            "iso3": row['Country_Code'],
            "name": row['Country_Name'],
            "region": row['C1_Region'],
            "income": row['C2_IncomeLevel'],
            "learning_poverty": round(row['Learning_Poverty'], 1) if row['Learning_Poverty'] is not None else None,
            "cluster": int(row['Cluster']),
            "priority_score": row['Priority_Score'],
            "features": {
                "gdp": round(row['F1_GDP_per_capita'], 0) if row.get('F1_GDP_per_capita') else 0,
                "pupil_teacher_ratio": round(row['F3_Pupil_Teacher_Ratio'], 1) if row.get('F3_Pupil_Teacher_Ratio') else 0,
                "stunting": round(row['F4_Stunting_Rate'], 1) if row.get('F4_Stunting_Rate') else 0,
                "net_enrollment": round(row['F6_Net_Enrollment'], 1) if row.get('F6_Net_Enrollment') else 0,
            }
        })
    
    # 4. 차트 데이터 (클러스터 평균, 변수 중요도)
    cluster_means = df.groupby('Cluster')[['F1_GDP_per_capita', 'F3_Pupil_Teacher_Ratio', 'F4_Stunting_Rate', 'F6_Net_Enrollment', 'Learning_Poverty']].mean().reset_index()
    
    clusters_info = []
    for _, row in cluster_means.iterrows():
        clusters_info.append({
            "cluster_id": int(row['Cluster']),
            "avg_learning_poverty": round(row['Learning_Poverty'], 1),
            "features": {
                "gdp": round(row['F1_GDP_per_capita'], 0),
                "pupil_teacher": round(row['F3_Pupil_Teacher_Ratio'], 1),
                "stunting": round(row['F4_Stunting_Rate'], 1),
                "enrollment": round(row['F6_Net_Enrollment'], 1)
            }
        })
        
    # RF Feature Importance (하드코딩 혹은 이전 단계 결과 요약)
    rf_importance = [
        {"feature": "1인당 GDP", "importance": 0.48, "shap_direction": "negative"},
        {"feature": "교사 1인당 학생 수", "importance": 0.20, "shap_direction": "positive"},
        {"feature": "아동 발육부진율", "importance": 0.13, "shap_direction": "positive"},
        {"feature": "순등록률", "importance": 0.05, "shap_direction": "negative"},
        {"feature": "인터넷 사용률", "importance": 0.04, "shap_direction": "negative"}
    ]

    # 최종 JSON 구조 조립
    dashboard_data = {
        "summary": {
            "total_countries": total_countries,
            "avg_learning_poverty": avg_learning_poverty,
            "estimated_lp_children": estimated_lp_children
        },
        "rf_importance": rf_importance,
        "clusters": clusters_info,
        "countries": sorted(countries_data, key=lambda x: x['priority_score'], reverse=True)
    }
    
    # 5. JSON 저장
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        
    print(f"[Export 완료] 대시보드 데이터가 생성되었습니다: {OUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    main()
