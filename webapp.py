import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import dotenv

# ----------------------------------------------------
# 0. 기본 설정 및 환경변수 로드
# ----------------------------------------------------
dotenv.load_dotenv()
#인증키 = os.getenv("subway_key")
인증키 = st.secrets["subway_key"]

# 페이지 기본 설정
st.set_page_config(
    page_title="서울시 지하철 승하차 인원 분석",
    page_icon="🚇",
    layout="wide"
)

# 한글 폰트 설정 (기존 스크립트 로직 반영)
import sys
if sys.platform == "win32":
    plt.rc("font", family="Malgun Gothic")
else:
    plt.rc("font", family="AppleGothic")

plt.rc("axes", unicode_minus=False)

# ----------------------------------------------------
# 메인 UI 레이아웃
# ----------------------------------------------------
st.subheader("🚇 서울시 지하철 호선별 역별 승하차 인원 분석")
st.markdown("OpenAPI를 활용하여 특정 날짜의 지하철 승하차 승객수를 분석합니다.")

# 사이드바: 달력 컨트롤 입력
st.sidebar.subheader("조회 조건 설정")
selected_date = st.sidebar.date_input(
    "조회할 사용일자를 선택하세요",
    value=pd.to_datetime("2026-08-20")
)

# API 요청용 YYYYMMDD 포맷 변환
use_ymd = selected_date.strftime("%Y%m%d")

# ----------------------------------------------------
# 1~4. OpenAPI 데이터 수집 및 검증
# ----------------------------------------------------
if st.sidebar.button("데이터 조회하기", type="primary"):
    url = f"http://openapi.seoul.go.kr:8088/{인증키}/json/CardSubwayStatsNew/1/1000/{use_ymd}"

    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        st.error(f"데이터 요청 중 네트워크 에러가 발생했습니다: {e}")
        st.stop()

    # 데이터 검증
    if "CardSubwayStatsNew" not in data or data["CardSubwayStatsNew"]["RESULT"]["CODE"] != "INFO-000":
        err_msg = data.get("RESULT", {}).get("MESSAGE", "데이터가 없거나 호출 실패했습니다.")
        st.error(f"데이터를 가져올 수 없습니다. (에러 메시지: {err_msg})")
        st.stop()

    # 데이터프레임 생성
    rows = data["CardSubwayStatsNew"]["row"]
    df = pd.DataFrame(rows)

    # 숫자로 변환
    df["GTON_TNOPE"] = pd.to_numeric(df["GTON_TNOPE"])
    df["GTOFF_TNOPE"] = pd.to_numeric(df["GTOFF_TNOPE"])

    # 5. '총승객수' 열 추가 ( 승차총승객수 + 하차총승객수 )
    df["총승객수"] = df["GTON_TNOPE"] + df["GTOFF_TNOPE"]

    # ----------------------------------------------------
    # 6 & 7. 요약 통계 및 상위 3개 역 표시
    # ----------------------------------------------------
    st.subheader(f"📊 {selected_date.strftime('%Y년 %m월 %d일')}")

    col1, col2 = st.columns([1,2])

    with col1:
        st.markdown("**■ 데이터 기본 통계 정보**")
        st.metric("전체 행 개수", f"{len(df):,} 개")
        st.metric("총승객수 최대", f"{df['총승객수'].max():,} 명")
        st.metric("총승객수 최소", f"{df['총승객수'].min():,} 명")
        st.metric("총승객수 평균", f"{df['총승객수'].mean():,.2f} 명")

    with col2:
        st.markdown("**■ 역명(SBWY_STNS_NM)별 총승객수 합계 상위 3개 역**")
        top3_stations = (
            df.groupby("SBWY_STNS_NM")["총승객수"]
            .sum()
            .reset_index()
            .sort_values(by="총승객수", ascending=False)
            .head(3)
        )
        for idx, row in top3_stations.iterrows():
            st.info(f"🏆 **{row['SBWY_STNS_NM']}**: {row['총승객수']:,} 명")

    st.divider()

    # ----------------------------------------------------
    # 8. 총승객수 분포 히스토그램 (구간 50)
    # ----------------------------------------------------
    st.subheader("📈 총승객수 분포 히스토그램 (구간 50)")
    
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.hist(df["총승객수"], bins=50, color="skyblue", edgecolor="black")
    ax1.set_title(f"총승객수 분포 히스토그램 ({use_ymd})", fontsize=14)
    ax1.set_xlabel("총승객수", fontsize=12)
    ax1.set_ylabel("빈도수 (역 개수)", fontsize=12)
    ax1.grid(axis="y", linestyle="--", alpha=0.7)
    st.pyplot(fig1)

    st.divider()

    # ----------------------------------------------------
    # 9. 총승객수 10만명 이상 데이터 -> 막대 그래프
    # ----------------------------------------------------
    st.subheader("📊 총승객수 10만명 이상 역별 현황")

    df_100k = df[df["총승객수"] >= 100000].sort_values(
        by="총승객수", ascending=False
    )

    if df_100k.empty:
        st.warning("총승객수가 10만명 이상인 데이터가 없습니다.")
    else:
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        sns.barplot(
            data=df_100k,
            x="SBWY_STNS_NM",
            y="총승객수",
            hue="SBWY_ROUT_LN_NM",
            dodge=False,
            ax=ax2
        )

        ax2.set_title(f"총승객수 10만명 이상 역별 총승객수 현황 ({use_ymd})", fontsize=14)
        ax2.set_xlabel("역명 (SBWY_STNS_NM)", fontsize=12)
        ax2.set_ylabel("총승객수", fontsize=12)
        ax2.tick_params(axis='x', rotation=45)
        ax2.legend(
            title="호선명(SBWY_ROUT_LN_NM)",
            bbox_to_anchor=(1.05, 1),
            loc="upper left"
        )
        ax2.grid(axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()
        st.pyplot(fig2)

    # 원본 데이터 확인 (옵션)
    with st.expander("원본 데이터 보기"):
        st.dataframe(df)