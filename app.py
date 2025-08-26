import os, ast
from typing import List
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import requests

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# ----------------- Data Dragon 아이콘 -----------------
@st.cache_data(show_spinner=False)
def get_ddragon_item_data():
    url = "http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/item.json"
    return requests.get(url).json()

@st.cache_data(show_spinner=False)
def get_ddragon_spell_data():
    url = "http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/summoner.json"
    return requests.get(url).json()

@st.cache_data(show_spinner=False)
def get_ddragon_rune_data():
    url = "http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/runesReforged.json"
    return requests.get(url).json()

item_data = get_ddragon_item_data()
spell_data = get_ddragon_spell_data()
rune_data = get_ddragon_rune_data()

# 아이콘 매핑
item_name_to_img = {v["name"]: v["image"]["full"] for k,v in item_data["data"].items()}
spell_name_to_img = {v["name"]: v["image"]["full"] for k,v in spell_data["data"].items()}

rune_name_to_img = {}
for tree in rune_data:
    rune_name_to_img[tree["name"]] = tree["icon"]
    for slot in tree["slots"]:
        for rune in slot["runes"]:
            rune_name_to_img[rune["name"]] = rune["icon"]

# 아이콘 HTML 생성
def add_icon_html(name, img_dict, width=20):
    img_file = img_dict.get(name)
    if img_file:
        # 아이템/스펠/룬 구분
        if img_file.endswith(".png"):
            if 'item' in img_file:
                url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img_file}"
            elif 'Summoner' in img_file or 'Summoner' in name:
                url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{img_file}"
            else:
                url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/{img_file}"
            return f'<img src="{url}" width="{width}"/> {name}'
        else:
            url = f"http://ddragon.leagueoflegends.com/cdn/img/{img_file}"
            return f'<img src="{url}" width="{width}"/> {name}'
    return name

# ----------------- CSV 로드/전처리 (기존 코드 유지) -----------------
# ... [기존 load_df, _as_list, _discover_csv 등 함수 그대로 유지] ...

# ----------------- 아이템 성과 출력 (아이콘 포함) -----------------
def item_stats_with_icon(sub: pd.DataFrame):
    item_cols = [c for c in sub.columns if c.startswith("item")]
    rec = []
    for c in item_cols:
        rec.append(sub[["matchId","win_clean",c]].rename(columns={c:"item"}))
    u = pd.concat(rec, ignore_index=True)
    u = u[u["item"].astype(str)!=""]
    g = (u.groupby("item")
         .agg(total_picks=("matchId","count"), wins=("win_clean","sum"))
         .reset_index())
    g["win_rate"] = (g["wins"]/g["total_picks"]*100).round(2)
    g = g.sort_values(["total_picks","win_rate"], ascending=[False,False])
    # HTML 컬럼 추가
    g["item_icon"] = g["item"].apply(lambda x: add_icon_html(x, item_name_to_img))
    return g

# 예시 출력
st.subheader("아이템 성과 (Top 20)")
df_items = item_stats_with_icon(dfc).head(20)
for _, row in df_items.iterrows():
    st.markdown(row["item_icon"] + f" — 픽: {row['total_picks']}, 승률: {row['win_rate']}%", unsafe_allow_html=True)
