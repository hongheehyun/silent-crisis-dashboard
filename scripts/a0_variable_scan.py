import pandas as pd
import wbgapi as wb
import os
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

def scan_new_variables():
    print("="*60)
    print("[Step 0] 테마 기반 새로운 지표 스캔 (WDI API)")
    print("="*60)

    BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
    DATA_PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
    IMG_DIR = os.path.join(BASE_DIR, 'images')
    os.makedirs(IMG_DIR, exist_ok=True)
    
    # 1. 기존 데이터 로드
    try:
        base_data = pd.read_csv(os.path.join(DATA_PROCESSED_DIR, 'analysis_ready.csv'))
        target_countries = base_data['Country_Code'].tolist()
        print(f"기존 분석 국가 수: {len(target_countries)}개")
    except Exception as e:
        print(f"기존 데이터를 불러오는 데 실패했습니다: {e}")
        return

    # 2. 스캔할 테마별 지표 정의 (사용자 요청 지표 전체 반영 + 대체 지표)
    theme_indicators = {
        # 거버넌스 (GE.EST 계열은 WDI 기본 DB에 없을 수 있으므로 CPIA 대체 지표도 포함)
        'GE.EST': 'Gov_Effectiveness',
        'CC.EST': 'Corruption_Control',
        'RL.EST': 'Rule_of_Law',
        'IQ.CPA.PUBS.XQ': 'CPIA_Public_Sector', # 행정 역량 (대체)
        'IQ.CPA.TRAN.XQ': 'CPIA_Transparency',  # 투명성/부패통제 (대체)
        
        # 사회보호
        'SP.ADO.TFRT': 'Adolescent_Fertility',
        'SL.TLF.0714.ZS': 'Child_Employment',
        'per_allsp.cov_pop_tot': 'Social_Protection_Cov',
        
        # 보건/영양
        'SH.DYN.MORT': 'Under5_Mortality',
        'SH.IMM.MEAS': 'Measles_Immunization',
        'SH.MED.PHYS.ZS': 'Physicians_per_1000',
        
        # 인프라/디지털
        'EG.ELC.ACCS.ZS': 'Electricity_Access',
        'IT.CEL.SETS.P2': 'Mobile_Subscriptions',
        'IS.ROD.PAVE.ZS': 'Paved_Roads',
        
        # 젠더/사회
        'SL.TLF.CACT.FE.ZS': 'Female_Labor_Part',
        'SP.M18.2024.FE.ZS': 'Child_Marriage_Female',
        'SG.GEN.PARL.ZS': 'Female_Parliamentarians'
    }

    print("\nAPI 수집 시작 (개별 지표별 안전 수집)...")
    collected_dfs = []
    
    for code, name in theme_indicators.items():
        try:
            # 개별 지표 호출
            df = wb.data.DataFrame(code, economy=target_countries, time=range(2015, 2024), numericTimeKeys=True)
            if df is not None and not df.empty:
                # 2015~2023 ffill 후 마지막 값 취합
                df_filled = df.ffill(axis=1)
                latest_values = df_filled.iloc[:, -1].reset_index()
                latest_values.columns = ['Country_Code', name]
                collected_dfs.append(latest_values)
                print(f" [성공] {name} ({code}) 수집 완료")
            else:
                print(f" [실패] {name} ({code}) - 데이터 없음")
        except Exception as e:
            print(f" [오류] {name} ({code}) - 수집 불가 API 에러")

    if not collected_dfs:
        print("수집된 데이터가 없습니다.")
        return

    # 3. 데이터 병합
    merged = base_data[['Country_Code', 'Learning_Poverty']].copy()
    merged['Learning_Poverty_Log'] = np.log1p(merged['Learning_Poverty'])
    
    for df in collected_dfs:
        merged = pd.merge(merged, df, on='Country_Code', how='left')
    
    # 4. 상관계수 계산
    # 수집 성공한 변수만 필터링
    scan_vars = [col for col in merged.columns if col not in ['Country_Code', 'Learning_Poverty', 'Learning_Poverty_Log']]
    corr_data = merged[['Learning_Poverty'] + scan_vars]
    
    spearman_corr = corr_data.corr(method='spearman')[['Learning_Poverty']].drop(['Learning_Poverty'])

    print("\n=== [결과] 학습 빈곤율과의 상관관계 (Spearman) ===")
    sorted_spearman = spearman_corr['Learning_Poverty'].abs().sort_values(ascending=False)
    for var in sorted_spearman.index:
        val = spearman_corr.loc[var, 'Learning_Poverty']
        print(f" - {var}: {val:.3f}")

    # 5. 시각화 (상관관계 히트맵)
    plt.figure(figsize=(12, 10))
    full_corr = corr_data.corr(method='spearman')
    
    # Target(Learning_Poverty)을 맨 앞에 두기
    cols = ['Learning_Poverty'] + scan_vars
    full_corr = full_corr.loc[cols, cols]
    
    mask = np.triu(np.ones_like(full_corr, dtype=bool))
    sns.heatmap(full_corr, mask=mask, annot=True, fmt=".2f", cmap='coolwarm', vmin=-1, vmax=1, center=0, square=True, linewidths=.5)
    plt.title('Spearman Correlation: Learning Poverty vs New Theme Indicators')
    plt.tight_layout()
    
    heatmap_path = os.path.join(IMG_DIR, 'a0_new_vars_correlation.png')
    plt.savefig(heatmap_path, dpi=300)
    print(f"\n히트맵 이미지 저장 완료: {heatmap_path}")
    print("="*60)

if __name__ == "__main__":
    scan_new_variables()
