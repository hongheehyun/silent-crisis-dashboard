# -*- coding: utf-8 -*-
"""
v2.0 분석 데이터 준비 스크립트 (WGI 지표 포함 최종본)
- Step 0 스캔 결과 신규 변수 N1~N5 수집
- WGI 거버넌스 지표 G1~G3 수집 (ESG DB=75 활용, 102개국 커버)
- 기존 analysis_ready.csv(v1.0, F1~F8)에 병합
- KNN Imputation 적용 후 analysis_ready_v2.csv로 저장
"""

import pandas as pd
import wbgapi as wb
import numpy as np
import os
from sklearn.impute import KNNImputer

# ── 경로 설정 ──────────────────────────────────────────────────
BASE_DIR     = os.path.join(os.path.dirname(__file__), '..')
PROCESSED    = os.path.join(BASE_DIR, 'data', 'processed')
OUT_PATH     = os.path.join(PROCESSED, 'analysis_ready_v2.csv')
V1_PATH      = os.path.join(PROCESSED, 'analysis_ready.csv')

# ── A1 분석용 신규 변수 (WDI, db=2) ──────────────────────────
new_vars = {
    'SH.DYN.MORT'       : 'N1_Under5_Mortality',
    'SP.ADO.TFRT'       : 'N2_Adolescent_Fertility',
    'EG.ELC.ACCS.ZS'    : 'N3_Electricity_Access',
    'SH.MED.PHYS.ZS'    : 'N4_Physicians_per_1000',
    'SP.M18.2024.FE.ZS' : 'N5_Child_Marriage_Female',
}

# ── A2 분석용 거버넌스 변수 (ESG DB=75, WGI 원본) ─────────────
wgi_vars = {
    'GE.EST': 'G1_Gov_Effectiveness',
    'CC.EST': 'G2_Corruption_Control',
    'RL.EST': 'G3_Rule_of_Law',
}

def collect_wdi(code, name, countries):
    """WDI(db=2)에서 개별 지표 수집"""
    try:
        wb.db = 2
        df = wb.data.DataFrame(code, economy=countries, time=range(2015, 2024), numericTimeKeys=True)
        df_filled = df.ffill(axis=1)
        latest = df_filled.iloc[:, -1].reset_index()
        latest.columns = ['Country_Code', name]
        return latest
    except Exception:
        return None

def collect_wgi(code, name, countries):
    """ESG DB(db=75)에서 WGI 지표 수집"""
    try:
        wb.db = 75
        df = wb.data.DataFrame(code, economy=countries, time=range(2015, 2024), numericTimeKeys=True)
        df_filled = df.ffill(axis=1)
        latest = df_filled.iloc[:, -1].reset_index()
        latest.columns = ['Country_Code', name]
        return latest
    except Exception:
        return None

def main():
    print("=" * 60)
    print("[Phase 1] v2.0 분석 데이터 준비 (WGI 지표 포함)")
    print("=" * 60)

    # 1. v1.0 기존 데이터 로드
    print("\n[1/5] v1.0 기존 데이터 로드...")
    v1 = pd.read_csv(V1_PATH)
    countries = v1['Country_Code'].tolist()
    print(f"  → {len(countries)}개국, {v1.shape[1]}개 컬럼")

    # 2. A1 신규 변수 수집 (WDI, db=2)
    print(f"\n[2/5] A1 신규 변수 {len(new_vars)}개 수집 (WDI)...")
    collected = []
    for code, name in new_vars.items():
        result = collect_wdi(code, name, countries)
        if result is not None:
            collected.append(result)
            non_null = result[name].notna().sum()
            print(f"  [성공] {name}: {non_null}개국")
        else:
            print(f"  [실패] {name} ({code})")

    # 3. A2 거버넌스 변수 수집 (ESG DB=75, WGI 원본)
    print(f"\n[3/5] A2 거버넌스 변수 {len(wgi_vars)}개 수집 (WGI via ESG DB)...")
    for code, name in wgi_vars.items():
        result = collect_wgi(code, name, countries)
        if result is not None:
            collected.append(result)
            non_null = result[name].notna().sum()
            print(f"  [성공] {name}: {non_null}개국")
        else:
            print(f"  [실패] {name} ({code})")

    # 4. 병합
    print("\n[4/5] 데이터 병합 중...")
    v2 = v1.copy()

    # CPIA 컬럼이 이전 버전에서 남아있다면 제거
    cpia_cols = [c for c in v2.columns if 'CPIA' in c or 'G_AVG' in c]
    if cpia_cols:
        v2 = v2.drop(columns=cpia_cols)
        print(f"  → 이전 CPIA 컬럼 제거: {cpia_cols}")

    for df in collected:
        v2 = pd.merge(v2, df, on='Country_Code', how='left')

    # 거버넌스 종합 지수 생성
    gov_cols = [c for c in ['G1_Gov_Effectiveness', 'G2_Corruption_Control', 'G3_Rule_of_Law'] if c in v2.columns]
    if gov_cols:
        v2['G_AVG_Governance'] = v2[gov_cols].mean(axis=1)
        print(f"  → G_AVG_Governance 생성 ({len(gov_cols)}개 지표 평균)")

    # 결측치 현황
    print("\n[결측치 현황]")
    check_cols = list(new_vars.values()) + list(wgi_vars.values()) + ['G_AVG_Governance']
    existing = [c for c in check_cols if c in v2.columns]
    for col in existing:
        cnt = v2[col].isnull().sum()
        pct = cnt / len(v2) * 100
        print(f"  - {col}: {cnt}개 ({pct:.1f}%)")

    # 5. KNN Imputation
    print("\n[5/5] KNN Imputation 적용 (K=5)...")
    impute_cols = [c for c in existing if v2[c].isnull().any()]
    if impute_cols:
        imputer = KNNImputer(n_neighbors=5)
        ref_cols = [c for c in v2.columns if c.startswith('F') or c.startswith('N') or c.startswith('G')]
        ref_data = v2[ref_cols].copy()
        imputed = imputer.fit_transform(ref_data)
        v2[ref_cols] = imputed

        # G_AVG 재계산
        if 'G_AVG_Governance' in v2.columns and gov_cols:
            v2['G_AVG_Governance'] = v2[gov_cols].mean(axis=1)

        print(f"  → {len(impute_cols)}개 컬럼 보정 완료")
    else:
        print("  → 결측치 없음")

    # 저장
    v2.to_csv(OUT_PATH, index=False)
    print(f"\n{'='*60}")
    print(f"[완료] analysis_ready_v2.csv 저장됨")
    print(f"  크기: {v2.shape[0]}개국 × {v2.shape[1]}개 컬럼")
    print(f"\n[컬럼 목록]")
    for col in v2.columns:
        print(f"  - {col}")
    print("=" * 60)

if __name__ == "__main__":
    main()
