# app.py
# ------------------------------------------------------------------
# ARAM PS Dashboard + Data-Dragon 아이콘 (Streamlit 1.32+ 호환)
# ------------------------------------------------------------------
import os, ast, re, unicodedata, requests
from typing import List
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# ------------------------------------------------------------------
# Data-Dragon helpers
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def ddragon_version()->str:
    return requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5).json()[0]

@st.cache_data(show_spinner=False, ttl=86400)
def load_dd_maps(ver:str):
    champs = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json", timeout=5).json()["data"]
    champ_name2file = { cdata["name"]: cdata["id"] + ".png" for cdata in champs.values() }
    champ_alias = { re.sub(r"[ '&.:]", "", cdata["name"]).lower(): cdata["id"] + ".png" for cdata in champs.values() }

    items = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/item.json", timeout=5).json()["data"]
    item_name2id = { v["name"]: k for k, v in items.items() }

    spells = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/summoner.json", timeout=5).json()["data"]
    spell_name2key = { v["name"]: v["id"] for v in spells.values() }

    return {"champ_name2file": champ_name2file, "champ_alias": champ_alias,
            "item_name2id": item_name2id, "spell_name2key": spell_name2key}

DDRAGON_VERSION = ddragon_version()
DD = load_dd_maps(DDRAGON_VERSION)

# -----------------------
# 이름 정규화
# -----------------------
def norm_name(s):
    """이름 정규화: NFKD, 소문자, 공백/특수문자 제거"""
    if not isinstance(s,str): return ""
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[ '&.:]", "", s).lower()
    return s

# -----------------------
# Icon URL functions
# -----------------------
def champion_icon_url(name:str)->str:
    key = DD["champ_name2file"].get(name)
    if not key:
        n = re.sub(r"[ '&.:]", "", name).lower()
        key = DD["champ_alias"].get(n)
    if not key:
        key = re.sub(r"[ '&.:]", "", name)
        key = key[0].upper() + key[1:] + ".png"
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/champion/{key}"

def item_icon_url(item:str)->str:
    key = norm_name(item)
    for k,v in DD["item_name2id"].items():
        if norm_name(k) == key:
            return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/{v}.png"
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/item/1001.png"

def spell_icon_url(spell:str)->str:
    key = norm_name(spell)
    for k,v in DD["spell_name2key"].items():
        if norm_name(k) == key:
            return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/{v}.png"
    return f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/img/spell/SummonerFlash.png"

# ------------------------------------------------------------------
# CSV loader
# ------------------------------------------------------------------
CSV_CANDIDATES = [
    "aram_participants_with_full_runes_merged_plus.csv",
    "aram_participants_with_full_runes_merged.csv",
    "aram_participants_with_full_runes.csv",
    "aram_participants_clean_preprocessed.csv",
    "aram_participants_clean_no_dupe_items.csv",
    "aram_participants_with_items.csv",
]

def _discover_csv():
    for f in CSV_CANDIDATES:
        if os.path.exists(f):
            return f
    return None

def _yes(x):
    return 1 if str(x).strip().lower() in ("1","true","t","yes") else 0

def _as_list(s):
    if isinstance(s,list):
        return s
    if not isinstance(s,str) or not s.strip():
        return []
    try:
        v = ast.literal_eval(s)
        if isinstance(v,list):
            return v
    except:
        pass
    spl = "|" if "|" in s else "," if "," in s else None
    return [t.strip() for t in s.split(spl)] if spl else [s]

@st.cache_data(show_spinner=False)
def load_df(buf) -> pd.DataFrame:
    df = pd.read_csv(buf)
    df["win_clean"] = df.get("win", 0).apply(_yes)
    s1 = "spell1_name" if "spell1_name" in df else "spell1"
    s2 = "spell2_name" if "spell2_name" in df else "spell2"
    df["spell_combo"] = (df[s1].astype(str) + " + " + df[s2].astype(str)).str.strip()
    for c in [c for c in df if c.startswith("item")]:
        df[c] = df[c].fillna("").astype(str).str.strip()
    for col in ("team_champs","enemy_champs"):
        if col in df:
            df[col] = df[col].apply(_as_list)
    if "game_end_min" in df.columns:
        df["duration_min"] = pd.to_numeric(df["game_end_min"], errors="coerce").fillna(18).clip(6,40)
    else:
        df["duration_min"] = 18
    df["dpm"] = df.get("damage_total", np.nan) / df["duration_min"].replace(0,np.nan)
    for k in ("kills","deaths","assists"):
        df[k] = df.get(k,0)
    df["kda"] = (df["kills"] + df["assists"]) / df["deaths"].replace(0,np.nan)
    df["kda"] = df["kda"].fillna(df["kills"] + df["assists"])
    return df

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
st.sidebar.header(":톱니바퀴: 설정")
auto = _discover_csv()
st.sidebar.write(":돋보기: 자동 검색:", auto if auto else "없음")
up = st.sidebar.file_uploader("CSV 업로드(선택)", type="csv")
df = load_df(up) if up else load_df(auto) if auto else None
if df is None:
    st.error("CSV 파일이 없습니다.")
    st.stop()

champions = sorted(df["champion"].dropna().unique())
sel = st.sidebar.selectbox(":다트: 챔피언 선택", champions)

# ------------------------------------------------------------------
# Header & Metrics
# ------------------------------------------------------------------
dfc = df[df["champion"]==sel]
total = df["matchId"].nunique() if "matchId" in df else len(df)
games = len(dfc)
wr = round(dfc["win_clean"].mean()*100,2) if games else 0
pr = round(games/total*100,2) if total else 0
avg_k, avg_d, avg_a = [round(dfc[c].mean(),2) for c in ("kills","deaths","assists")]
avg_dpm = round(dfc["dpm"].mean(),1)

st.title(":트로피: ARAM Analytics")
mid = st.columns([2,3,2])[1]
with mid:
    st.image(champion_icon_url(sel), width=100)
    st.subheader(sel, divider=False)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("게임 수", games)
m2.metric("승률", f"{wr}%")
m3.metric("픽률", f"{pr}%")
m4.metric("평균 K/D/A", f"{avg_k}/{avg_d}/{avg_a}")
m5.metric("평균 DPM", avg_dpm)

# ------------------------------------------------------------------
# Tabs
# ------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([":막대_차트: 게임 분석",
                                  ":교차된_검: 아이템 & 스펠",
                                  ":스톱워치: 타임라인",
                                  ":클립보드: 상세 데이터"])

with tab1:
    if "first_blood_min" in dfc and dfc["first_blood_min"].notna().any():
        st.metric("퍼블 평균 분", round(dfc["first_blood_min"].mean(),2))
    if "game_end_min" in dfc:
        st.metric("평균 게임 시간", round(dfc["game_end_min"].mean(),2))

with tab2:
    left, right = st.columns(2)
    with left:
        st.subheader(":방패: 아이템 성과")
        item_cols = [c for c in dfc if c.startswith("item")]
        rec = pd.concat([dfc[["matchId","win_clean",c]].rename(columns={c:"item"}) for c in item_cols])
        g = (rec[rec["item"]!=""]
             .groupby("item")
             .agg(total=("matchId","count"), wins=("win_clean","sum"))
             .assign(win_rate=lambda d:(d.wins/d.total*100).round(2))
             .sort_values(["total","win_rate"], ascending=[False,False])
             .head(10)
             .reset_index())
        for _,r in g.iterrows():
            block = st.container()
            c_icon, c_name, c_pick, c_wr = block.columns([1,4,2,2])
            with c_icon: st.image(item_icon_url(str(r.item)), width=32)
            with c_name: c_name.write(str(r.item))
            with c_pick: c_pick.write(f"{int(r.total)} 게임")
            with c_wr:   c_wr.write(f"{r.win_rate}%")
            st.divider()
    with right:
        st.subheader(":반짝임: 스펠 조합")
        sp = (dfc.groupby("spell_combo")
              .agg(games=("matchId","count"), wins=("win_clean","sum"))
              .assign(win_rate=lambda d:(d.wins/d.games*100).round(2))
              .sort_values(["games","win_rate"], ascending=[False,False])
              .head(8)
              .reset_index())
        for _, r in sp.iterrows():
            s1, s2 = [s.strip() for s in str(r.spell_combo).split("+")]
            block = st.container()
            col_i, col_n, col_v = block.columns([2,3,2])
            with col_i:
                st.image(spell_icon_url(s1), width=28)
                st.image(spell_icon_url(s2), width=28)
            with col_n: col_n.write(str(r.spell_combo))
            with col_v: col_v.write(f"{r.win_rate}%\n{int(r.games)}G")
            st.divider()

with tab3:
    if "first_core_item_min" in dfc and dfc["first_core_item_min"].notna().any():
        st.metric("1코어 평균 분", round(dfc["first_core_item_min"].mean(),2))
        fig = px.histogram(dfc, x="first_core_item_min", nbins=24, title="1코어 시점")
        fig.update_layout(plot_bgcolor="#1E2328", paper_bgcolor="#1E2328", font_color="#F0E6D2")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.dataframe(dfc.drop(columns=["team_champs","enemy_champs"], errors="ignore"),
                 use_container_width=True)

st.caption(f"Data-Dragon v{DDRAGON_VERSION} · {len(champions)}챔프 · {total}경기")
