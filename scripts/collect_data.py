# -*- coding: utf-8 -*-
"""
학습빈곤 데이터 및 World Bank 지표 병합 스크립트 (수정본)
1. 종속변수: WB_LPGD.csv (2015년 이후 최신 데이터 1건/국가)
2. 독립변수: wbgapi를 통해 스펙(F1~F8) 데이터 자동 수집 (2015~2023 기준 최신값 수동 병합)
"""

import pandas as pd
import wbgapi as wb
import os

def collect_and_merge_data():
    print("="*60)
    print("데이터 수집 및 병합 파이프라인 시작 (2015 컷오프 적용)")
    print("="*60)

    BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
    DATA_RAW = os.path.join(BASE_DIR, 'data', 'WB_LPGD.csv')
    DATA_PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
    os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
    
    # ------------------------------------------------------------------
    # 1. 종속변수 (y) 추출 및 전처리
    # ------------------------------------------------------------------
    print("\n[1] 종속변수(y) 전처리 중... (WB_LPGD.csv)")
    df_raw = pd.read_csv(DATA_RAW)
    
    lp = df_raw[(df_raw['INDICATOR'] == 'WB_LPGD_SE_LPV_PRIM') & 
                (df_raw['SEX_LABEL'] == 'Total')].copy()
    
    lp_2015 = lp[lp['TIME_PERIOD'] >= 2015].copy()
    lp_latest = lp_2015.sort_values('TIME_PERIOD').groupby('REF_AREA').last().reset_index()
    
    y_data = lp_latest[['REF_AREA', 'REF_AREA_LABEL', 'TIME_PERIOD', 'OBS_VALUE']].copy()
    y_data.columns = ['Country_Code', 'Country_Name', 'LP_Year', 'Learning_Poverty']
    
    print(f"  -> 2015년 이후 데이터 보유 국가: {len(y_data)}개국 추출 완료")
    
    # ------------------------------------------------------------------
    # 2. 독립변수 (X) 수집 (wbgapi 활용)
    # ------------------------------------------------------------------
    print("\n[2] 독립변수(X) 수집 중... (World Bank API - wbgapi)")
    
    indicators = {
        'NY.GDP.PCAP.PP.KD': 'F1_GDP_per_capita',
        'SE.XPD.TOTL.GD.ZS': 'F2_Gov_Edu_Exp',
        'SE.PRM.ENRL.TC.ZS': 'F3_Pupil_Teacher_Ratio',
        'SH.STA.STNT.ZS': 'F4_Stunting_Rate',
        'IT.NET.USER.ZS': 'F5_Internet_Usage',
        'SE.PRM.NENR': 'F6_Net_Enrollment',
        'SE.PRM.CMPT.ZS': 'F7_Completion_Rate',
        'SE.ENR.PRIM.FM.ZS': 'F8_Gender_Parity_Index'
    }
    
    target_countries = y_data['Country_Code'].tolist()
    
    # mrv=1 버그 회피: 2015~2023 전체를 가져와서 pandas 레벨에서 ffill 후 2023값 사용
    print(f"  -> API 통신 중... (지표 8개, 국가 {len(target_countries)}개)")
    try:
        # economy 행, series/time 열 구조가 아님. time이 컬럼으로 오게 됨.
        df_wdi = wb.data.DataFrame(
            list(indicators.keys()), 
            economy=target_countries, 
            time=range(2015, 2024), 
            numericTimeKeys=True
        )
        
        # 구조 변환: 인덱스는 (economy, series), 컬럼은 2015~2023
        # 각 지표(series)별로 2015~2023의 결측치를 ffill(앞으로 채우기) 한 뒤, 가장 끝열(2023년) 값을 취함
        df_wdi_filled = df_wdi.ffill(axis=1) # 2015부터 2023방향으로 앞의 값을 채움
        latest_values = df_wdi_filled.iloc[:, -1] # 가장 마지막 열(2023년) 추출
        
        # 데이터프레임으로 변환 (economy, series -> columns)
        x_data = latest_values.unstack('series').reset_index()
        x_data = x_data.rename(columns={'economy': 'Country_Code'})
        x_data = x_data.rename(columns=indicators)
        print("  -> API 수집 완료!")
    except Exception as e:
        print(f"  [오류] API 호출 실패: {e}")
        return

    # ------------------------------------------------------------------
    # 3. 데이터 병합 (Merge)
    # ------------------------------------------------------------------
    print("\n[3] 데이터 병합 및 정리 중...")
    merged_data = pd.merge(y_data, x_data, on='Country_Code', how='left')
    
    print("\n  [병합 결과 데이터 결측치 현황]")
    print(merged_data.isnull().sum())
    
    # ------------------------------------------------------------------
    # 4. 저장
    # ------------------------------------------------------------------
    out_path = os.path.join(DATA_PROCESSED_DIR, 'analysis_ready.csv')
    merged_data.to_csv(out_path, index=False)
    
    print(f"\n[4] 완료! 최종 데이터셋 저장 위치:\n  -> {out_path}")
    print("="*60)

if __name__ == "__main__":
    collect_and_merge_data()
