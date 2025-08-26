import os
import ast
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from typing import List

# Riot DDragon 이미지 URL
def get_icon_url(icon_type: str, name: str) -> str:
    base_url = "https://ddragon.leagueoflegends.com/cdn/13.19.1/img/"
    if icon_type == "champion":
        return f"{base_url}champion/{name}.png"
    elif icon_type == "item":
        return f"{base_url}item/{name}.png"
    elif icon_type == "spell":
        return f"{base_url}spell/{name}.png"
    elif icon_type == "rune":
        return f"https://ddragon.canisback.com/img/perk-images/Styles/{name}.png"
    return ""

# 데이터 로드 및 전처리
@st.cache_data(show_spinner=False)
def load_df(path_or_buffer) -> pd.DataFrame:
    df = pd.read_csv(path_or_buffer)
    # 데이터 전처리 코드 생략...
    return df

# CSV 파일 자동 탐색
def _discover_csv() -> str | None:
    for name in CSV_CANDIDATES:
        if os.path.exists(name):
            return name
    return None

# 필터링된 데이터프레임 생성
def filter_champion_data(df: pd.DataFrame, champion: str) -> pd.DataFrame:
    return df[df["champion"] == champion].copy()

# 아이템 통계 계산
def item_stats(sub: pd.DataFrame) -> pd.DataFrame:
    item_cols = [c for c in sub.columns if c.startswith("item")]
    rec = []
    for c in item_cols:
        rec.append(sub[["matchId", "win_clean", c]].rename(columns={c: "item"}))
    u = pd.concat(rec, ignore_index=True)
    u = u[u["item"].astype(str) != ""]
    g = (u.groupby("item")
         .agg(total_picks=("matchId", "count"), wins=("win_clean", "sum"))
         .reset_index())
    g["win_rate"] = (g["wins"] / g["total_picks"] * 100).round(2)
    g = g.sort_values(["total_picks", "win_rate"], ascending=[False, False])
    return g

# 룬 조합 통계 계산
def rune_stats(dfc: pd.DataFrame) -> pd.DataFrame:
    if "rune_core" in dfc.columns and "rune_sub" in dfc.columns:
        rn = (dfc.groupby(["rune_core", "rune_sub"])
              .agg(games=("matchId", "count"), wins=("win_clean", "sum"))
              .reset_index())
        rn["win_rate"] = (rn["wins"] / rn["games"] * 100).round(2)
        rn = rn.sort_values(["games", "win_rate"], ascending=[False, False]).head(10)
        return rn
    return pd.DataFrame()

# 챔피언 선택
champions = sorted(df["champion"].dropna().unique().tolist())
sel_champ = st.sidebar.selectbox("챔피언 선택", champions)

# 데이터 로드
auto_path = _discover_csv()
if auto_path is not None:
    df = load_df(auto_path)
else:
    st.error("CSV 파일을 찾을 수 없습니다.")
    st.stop()

# 챔피언 데이터 필터링
dfc = filter_champion_data(df, sel_champ)

# 아이템 통계
st.subheader("아이템 통계")
st.dataframe(item_stats(dfc).head(10), use_container_width=True)

# 룬 조합 통계
st.subheader("룬 조합 통계")
rune_df = rune_stats(dfc)
if not rune_df.empty:
    for _, r in rune_df.iterrows():
        col1, col2, col3 = st.columns([1, 1, 4])
        col1.image(get_icon_url("rune", r["rune_core"]), width=32)
        col2.image(get_icon_url("rune", r["rune_sub"]), width=32)
        col3.caption(f"{r['rune_core']} / {r['rune_sub']} — {r['games']} games / {r['win_rate']}% win rate")
else:
    st.info("룬 정보가 부족합니다.")

# 원본 데이터 표시
st.subheader("원본 데이터 (필터 적용)")
show_cols = [c for c in dfc.columns if c not in ("team_champs", "enemy_champs")]
st.dataframe(dfc[show_cols], use_container_width=True)
