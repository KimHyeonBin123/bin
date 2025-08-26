# -*- coding: utf-8 -*-
import os, ast
from typing import List
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# ---------- CSV 후보 ----------
CSV_CANDIDATES = [
    "aram_participants_with_full_runes_merged_plus.csv",
    "aram_participants_with_full_runes_merged.csv",
    "aram_participants_with_full_runes.csv",
    "aram_participants_clean_preprocessed.csv",
    "aram_participants_clean_no_dupe_items.csv",
    "aram_participants_with_items.csv",
]

# ---------- 유틸 ----------
def _yes(x) -> int:
    s = str(x).strip().lower()
    return 1 if s in ("1","true","t","yes") else 0

def _as_list(s):
    if isinstance(s, list):
        return s
    if not isinstance(s, str):
        return []
    s = s.strip()
    if not s:
        return []
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list):
            return v
    except:
        pass
    if "|" in s:
        return [t.strip() for t in s.split("|") if t.strip()]
    if "," in s:
        return [t.strip() for t in s.split(",") if t.strip()]
    return [s]

def _discover_csv() -> str | None:
    for name in CSV_CANDIDATES:
        if os.path.exists(name):
            return name
    return None

# ---------- 데이터 로드 ----------
@st.cache_data(show_spinner=False)
def load_df(path_or_buffer) -> pd.DataFrame:
    df = pd.read_csv(path_or_buffer)
    df["win_clean"] = df["win"].apply(_yes) if "win" in df.columns else 0
    s1 = "spell1_name" if "spell1_name" in df.columns else ("spell1" if "spell1" in df.columns else None)
    s2 = "spell2_name" if "spell2_name" in df.columns else ("spell2" if "spell2" in df.columns else None)
    df["spell1_final"] = df[s1].astype(str) if s1 else ""
    df["spell2_final"] = df[s2].astype(str) if s2 else ""
    df["spell_combo"]  = (df["spell1_final"] + " + " + df["spell2_final"]).str.strip()
    for c in [c for c in df.columns if c.startswith("item")]:
        df[c] = df[c].fillna("").astype(str).str.strip()
    for col in ("team_champs", "enemy_champs"):
        if col in df.columns:
            df[col] = df[col].apply(_as_list)
    df["duration_min"] = pd.to_numeric(df["game_end_min"], errors="coerce") if "game_end_min" in df.columns else np.nan
    df["duration_min"] = df["duration_min"].fillna(18.0).clip(lower=6.0, upper=40.0)
    df["dpm"] = df["damage_total"] / df["duration_min"].replace(0, np.nan) if "damage_total" in df.columns else np.nan
    for c in ("kills","deaths","assists"):
        if c not in df.columns:
            df[c] = 0
    df["kda"] = (df["kills"] + df["assists"]) / df["deaths"].replace(0, np.nan)
    df["kda"] = df["kda"].fillna(df["kills"] + df["assists"])
    return df

# ---------- 파일 입력 ----------
st.sidebar.title("데이터")
auto_path = _discover_csv()
st.sidebar.write("자동 검색:", auto_path if auto_path else "없음")
uploaded = st.sidebar.file_uploader("CSV 업로드(선택)", type=["csv"])
if uploaded is not None:
    df = load_df(uploaded)
elif auto_path is not None:
    df = load_df(auto_path)
else:
    st.error("CSV를 찾을 수 없습니다.")
    st.stop()

# ---------- 챔피언 선택 ----------
st.sidebar.markdown("---")
champions = sorted(df["champion"].dropna().unique().tolist())
if not champions:
    st.error("champion 컬럼이 비어있습니다.")
    st.stop()
sel_champ = st.sidebar.selectbox("챔피언 선택", champions)
dfc = df[df["champion"] == sel_champ].copy()

# ---------- LoL Data Dragon Resources ----------
item_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/item.json").json()
item_name_to_img = {v["name"]: v["image"]["full"] for k,v in item_data["data"].items()}

spell_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/summoner.json").json()
spell_name_to_img = {v["name"]: v["image"]["full"] for k,v in spell_data["data"].items()}

rune_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/runesReforged.json").json()
rune_name_to_img = {}
for tree in rune_data:
    rune_name_to_img[tree["name"]] = tree["icon"]
    for slot in tree["slots"]:
        for rune in slot["runes"]:
            rune_name_to_img[rune["name"]] = rune["icon"]

# ---------- HTML 아이콘 함수 ----------
def add_icon_html(name, img_dict, width=25):
    img_file = img_dict.get(name)
    if img_file:
        url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img_file}" if 'item' in img_file else f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/{img_file}"
        return f'<img src="{url}" width="{width}"/> {name}'
    return name

# ---------- ARAM 대시보드 ----------
st.title(f"ARAM Dashboard — {sel_champ}")
c1, c2, c3, c4, c5 = st.columns(5)
games = len(dfc)
total_matches = df["matchId"].nunique() if "matchId" in df.columns else len(df["matchId"])
winrate = round(dfc["win_clean"].mean()*100, 2) if games else 0.0
pickrate = round(games/total_matches*100, 2) if total_matches else 0.0
c1.metric("게임 수", games)
c2.metric("승률(%)", winrate)
c3.metric("픽률(%)", pickrate)
c4.metric("평균 K/D/A", f"{round(dfc['kills'].mean(),2)}/{round(dfc['deaths'].mean(),2)}/{round(dfc['assists'].mean(),2)}")
c5.metric("평균 DPM", round(dfc["dpm"].mean(),1))

# ---------- 아이템 성과 (AgGrid + 아이콘) ----------
st.subheader("아이템 성과(슬롯 무시, 전체 합산)")

def item_stats(sub: pd.DataFrame) -> pd.DataFrame:
    item_cols = [c for c in sub.columns if c.startswith("item")]
    rec = [sub[["matchId","win_clean",c]].rename(columns={c:"item"}) for c in item_cols]
    u = pd.concat(rec, ignore_index=True)
    u = u[u["item"].astype(str)!=""]
    g = (u.groupby("item")
         .agg(total_picks=("matchId","count"), wins=("win_clean","sum"))
         .reset_index())
    g["win_rate"] = (g["wins"]/g["total_picks"]*100).round(2)
    g = g.sort_values(["total_picks","win_rate"], ascending=[False,False])
    return g

items = item_stats(dfc)
items['item'] = items['item'].apply(lambda x: add_icon_html(x, item_name_to_img, width=25))

gb = GridOptionsBuilder.from_dataframe(items)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
gb.configure_column("item", cellRenderer='html')
gridOptions = gb.build()
AgGrid(items, gridOptions=gridOptions, enable_enterprise_modules=False, fit_columns_on_grid_load=True)

# ---------- 스펠/룬 섹션 (아이콘 적용) ----------
c1, c2 = st.columns(2)

with c1:
    st.subheader("스펠 조합")
    if "spell_combo" in dfc.columns and dfc["spell_combo"].str.strip().any():
        sp = (dfc.groupby("spell_combo")
              .agg(games=("matchId","count"), wins=("win_clean","sum"))
              .reset_index())
        sp["win_rate"] = (sp["wins"]/sp["games"]*100).round(2)
        sp = sp.sort_values(["games","win_rate"], ascending=[False,False])
        # 아이콘 적용
        sp['spell_combo'] = sp['spell_combo'].apply(lambda x: ' + '.join([add_icon_html(s, spell_name_to_img, 20) for s in x.split('+')]))
        gb = GridOptionsBuilder.from_dataframe(sp)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True)
        gb.configure_column("spell_combo", cellRenderer='html')
        AgGrid(sp, gridOptions=gb.build(), enable_enterprise_modules=False, fit_columns_on_grid_load=True)

with c2:
    st.subheader("룬 조합(메인/보조)")
    if ("rune_core" in dfc.columns) and ("rune_sub" in dfc.columns):
        rn = (dfc.groupby(["rune_core","rune_sub"])
              .agg(games=("matchId","count"), wins=("win_clean","sum"))
              .reset_index())
        rn["win_rate"] = (rn["wins"]/rn["games"]*100).round(2)
        rn = rn.sort_values(["games","win_rate"], ascending=[False,False])
        rn['rune_core'] = rn['rune_core'].apply(lambda x: add_icon_html(x, rune_name_to_img, 20))
        rn['rune_sub'] = rn['rune_sub'].apply(lambda x: add_icon_html(x, rune_name_to_img, 20))
        gb = GridOptionsBuilder.from_dataframe(rn)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True)
        gb.configure_column("rune_core", cellRenderer='html')
        gb.configure_column("rune_sub", cellRenderer='html')
        AgGrid(rn, gridOptions=gb.build(), enable_enterprise_modules=False, fit_columns_on_grid_load=True)
