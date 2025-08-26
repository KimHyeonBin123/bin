# app.py
# ----------------------------------------------
# ARAM PS Dashboard (Champion-centric) fully React layout
# 필요 패키지: streamlit, pandas, numpy, plotly
# ----------------------------------------------
import os, ast
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")
ICON_SIZE = 50  # 최소 아이콘 크기

# ---------- 후보 CSV ----------
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
    except Exception:
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

@st.cache_data(show_spinner=False)
def load_df(path_or_buffer) -> pd.DataFrame:
    df = pd.read_csv(path_or_buffer)
    # 승리 컬럼
    df["win_clean"] = df["win"].apply(_yes) if "win" in df.columns else 0
    # 스펠
    s1 = "spell1_name" if "spell1_name" in df.columns else ("spell1" if "spell1" in df.columns else None)
    s2 = "spell2_name" if "spell2_name" in df.columns else ("spell2" if "spell2" in df.columns else None)
    df["spell1_final"] = df[s1].astype(str) if s1 else ""
    df["spell2_final"] = df[s2].astype(str) if s2 else ""
    df["spell_combo"] = (df["spell1_final"] + " + " + df["spell2_final"]).str.strip()
    # 아이템 컬럼 정리
    for c in [c for c in df.columns if c.startswith("item")]:
        df[c] = df[c].fillna("").astype(str).str.strip()
    # 팀/상대 조합
    for col in ("team_champs","enemy_champs"):
        if col in df.columns:
            df[col] = df[col].apply(_as_list)
    # 경기 시간
    df["duration_min"] = pd.to_numeric(df["game_end_min"], errors="coerce") if "game_end_min" in df.columns else np.nan
    df["duration_min"] = df["duration_min"].fillna(18.0).clip(6.0,40.0)
    # DPM/KDA
    df["dpm"] = df["damage_total"]/df["duration_min"].replace(0,np.nan) if "damage_total" in df.columns else np.nan
    for c in ("kills","deaths","assists"):
        if c not in df.columns:
            df[c]=0
    df["kda"] = (df["kills"]+df["assists"])/df["deaths"].replace(0,np.nan)
    df["kda"] = df["kda"].fillna(df["kills"]+df["assists"])
    return df

# ---------- CSV 입력 ----------
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
champions = sorted(df["champion"].dropna().unique())
sel_champ = st.sidebar.selectbox("챔피언 선택", champions)
dfc = df[df["champion"]==sel_champ].copy()

# ---------- 기본 지표 ----------
total_matches = df["matchId"].nunique() if "matchId" in df.columns else len(df)
games = len(dfc)
winrate = round(dfc["win_clean"].mean()*100,2) if games else 0.0
pickrate = round(games/total_matches*100,2) if total_matches else 0.0
avg_k = round(dfc["kills"].mean(),2)
avg_d = round(dfc["deaths"].mean(),2)
avg_a = round(dfc["assists"].mean(),2)
avg_kda = round(dfc["kda"].mean(),2)
avg_dpm = round(dfc["dpm"].mean(),1)

st.title(f"ARAM Dashboard — {sel_champ}")
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("게임 수", games)
c2.metric("승률(%)", winrate)
c3.metric("픽률(%)", pickrate)
c4.metric("평균 K/D/A", f"{avg_k}/{avg_d}/{avg_a}")
c5.metric("평균 DPM", avg_dpm)

# ---------- 타임라인 ----------
tl_cols = ["first_blood_min","blue_first_tower_min","red_first_tower_min","game_end_min","gold_spike_min"]
if any(c in dfc.columns for c in tl_cols):
    st.subheader("타임라인 요약")
    t1,t2,t3 = st.columns(3)
    if "first_blood_min" in dfc.columns:
        t1.metric("퍼블 평균(분)", round(dfc["first_blood_min"].mean(),2))
    bt = round(dfc["blue_first_tower_min"].mean(),2) if "blue_first_tower_min" in dfc.columns else np.nan
    rt = round(dfc["red_first_tower_min"].mean(),2) if "red_first_tower_min" in dfc.columns else np.nan
    t2.metric("첫 포탑 평균(블루/레드)", f"{bt} / {rt}")
    if "game_end_min" in dfc.columns:
        t3.metric("평균 게임시간(분)", round(dfc["game_end_min"].mean(),2))
    if "gold_spike_min" in dfc.columns:
        fig = px.histogram(dfc,x="gold_spike_min",nbins=20,title="골드 스파이크 시각 분포(분)")
        st.plotly_chart(fig,use_container_width=True)

# ---------- 이미지 URL 함수 ----------
def champ_icon(name): return f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/{name}.png"
def item_icon(name): return f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/item/{name}.png"
def spell_icon(name): return f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/spell/{name}.png"
def rune_icon(name): return f"https://raw.community.rune.url/{name}.png"  # 실제 URL 수정 필요

# ---------- 챔피언 아이콘 ----------
st.subheader("선택 챔피언")
st.image(champ_icon(sel_champ), width=ICON_SIZE, caption=sel_champ)

# ---------- 코어 아이템 ----------
st.subheader("코어 아이템")
for col in ["first_core_item_name","second_core_item_name"]:
    if col in dfc.columns:
        items = dfc[col].dropna().unique()
        cols = st.columns(len(items))
        for i,it in enumerate(items):
            cols[i].image(item_icon(it),width=ICON_SIZE,caption=it)

# ---------- 아이템 성과 ----------
st.subheader("아이템 성과(상위 10)")
def item_stats(sub):
    item_cols = [c for c in sub.columns if c.startswith("item")]
    rec=[]
    for c in item_cols:
        rec.append(sub[["matchId","win_clean",c]].rename(columns={c:"item"}))
    u = pd.concat(rec,ignore_index=True)
    u = u[u["item"]!=""]
    g = u.groupby("item").agg(total_picks=("matchId","count"),wins=("win_clean","sum")).reset_index()
    g["win_rate"] = (g["wins"]/g["total_picks"]*100).round(2)
    return g.sort_values(["total_picks","win_rate"],ascending=[False,False])
top_items=item_stats(dfc).head(10)
cols=st.columns(len(top_items))
for i,row in enumerate(top_items.itertuples()):
    cols[i].image(item_icon(row.item),width=ICON_SIZE,caption=f"{row.item}\n픽:{row.total_picks} 승:{row.win_rate}%")

# ---------- 스펠 조합 ----------
st.subheader("스펠 조합 (상위 5)")
if "spell_combo" in dfc.columns:
    sp = dfc.groupby("spell_combo").agg(games=("matchId","count"),wins=("win_clean","sum")).reset_index()
    sp["win_rate"] = (sp["wins"]/sp["games"]*100).round(2)
    sp = sp.sort_values(["games","win_rate"],ascending=[False,False]).head(5)
    for _, row in sp.iterrows():
        spells=row.spell_combo.split(" + ")
        cols=st.columns(len(spells))
        for i,spn in enumerate(spells):
            cols[i].image(spell_icon(spn),width=ICON_SIZE,caption=spn)

# ---------- 룬 조합 ----------
st.subheader("룬 조합 (상위 5)")
if "rune_core" in dfc.columns and "rune_sub" in dfc.columns:
    rn = dfc.groupby(["rune_core","rune_sub"]).agg(games=("matchId","count"),wins=("win_clean","sum")).reset_index()
    rn["win_rate"] = (rn["wins"]/rn["games"]*100).round(2)
    rn = rn.sort_values(["games","win_rate"],ascending=[False,False]).head(5)
    for _, row in rn.iterrows():
        runes=[row.rune_core,row.rune_sub]
        cols=st.columns(len(runes))
        for i,rn_name in enumerate(runes):
            cols[i].image(rune_icon(rn_name),width=ICON_SIZE,caption=rn_name)

# ---------- 원본 데이터 ----------
st.subheader("원본 데이터 (필터 적용)")
show_cols=[c for c in dfc.columns if c not in ("team_champs","enemy_champs")]
st.dataframe(dfc[show_cols],use_container_width=True)
st.markdown("---")
st.caption("CSV 자동탐색 + 업로드 지원 · 누락 컬럼은 자동 건너뜀")
