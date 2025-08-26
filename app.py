import os, ast, requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

# ---------- DDragon 리소스 로드 ----------
PATCH = "14.16.1"
# 아이템
item_json = requests.get(
    f"http://ddragon.leagueoflegends.com/cdn/{PATCH}/data/ko_KR/item.json"
).json()
item_name_to_img = {v["name"]: f"http://ddragon.leagueoflegends.com/cdn/{PATCH}/img/item/{v['image']['full']}"
                    for k,v in item_json["data"].items()}

# 스펠
spell_json = requests.get(
    f"http://ddragon.leagueoflegends.com/cdn/{PATCH}/data/ko_KR/summoner.json"
).json()
spell_name_to_img = {v["name"]: f"http://ddragon.leagueoflegends.com/cdn/{PATCH}/img/spell/{v['image']['full']}"
                     for k,v in spell_json["data"].items()}

# 룬
rune_json = requests.get(
    f"http://ddragon.leagueoflegends.com/cdn/{PATCH}/data/ko_KR/runesReforged.json"
).json()
rune_name_to_img = {}
for tree in rune_json:
    rune_name_to_img[tree["name"]] = f"http://ddragon.leagueoflegends.com/cdn/img/{tree['icon']}"
    for slot in tree["slots"]:
        for rune in slot["runes"]:
            rune_name_to_img[rune["name"]] = f"http://ddragon.leagueoflegends.com/cdn/img/{rune['icon']}"

# ---------- 아이콘 helper ----------
def add_icon_html(name: str, mapping: dict, width=20) -> str:
    if not name or str(name).lower() in ("nan","none"):
        return ""
    url = mapping.get(name)
    if url:
        return f'<img src="{url}" width="{width}"/> {name}'
    return name

def aggrid_table(df: pd.DataFrame, html_cols: list):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
    for col in html_cols:
        gb.configure_column(col, cellRenderer="html")
    grid = gb.build()
    AgGrid(df, gridOptions=grid,
           allow_unsafe_jscode=True,
           fit_columns_on_grid_load=True,
           height=300)

# ---------- 예시: 아이템 성과 ----------
st.subheader("아이템 성과 (Top 20)")
def item_stats(sub: pd.DataFrame) -> pd.DataFrame:
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
    return g

items = item_stats(dfc).head(20)
items["아이템"] = items["item"].apply(lambda x: add_icon_html(x, item_name_to_img))
aggrid_table(items[["아이템","total_picks","wins","win_rate"]], ["아이템"])

# ---------- 예시: 스펠 조합 ----------
st.subheader("스펠 조합 (Top 10)")
sp = (dfc.groupby(["spell1_final","spell2_final"])
      .agg(games=("matchId","count"), wins=("win_clean","sum"))
      .reset_index())
sp["win_rate"] = (sp["wins"]/sp["games"]*100).round(2)
sp = sp.sort_values(["games","win_rate"], ascending=[False,False]).head(10)

sp["Spell1"] = sp["spell1_final"].apply(lambda x: add_icon_html(x, spell_name_to_img))
sp["Spell2"] = sp["spell2_final"].apply(lambda x: add_icon_html(x, spell_name_to_img))
aggrid_table(sp[["Spell1","Spell2","games","wins","win_rate"]], ["Spell1","Spell2"])

# ---------- 예시: 룬 조합 ----------
st.subheader("룬 조합 (Top 10)")
rn = (dfc.groupby(["rune_core","rune_sub"])
      .agg(games=("matchId","count"), wins=("win_clean","sum"))
      .reset_index())
rn["win_rate"] = (rn["wins"]/rn["games"]*100).round(2)
rn = rn.sort_values(["games","win_rate"], ascending=[False,False]).head(10)

rn["메인룬"] = rn["rune_core"].apply(lambda x: add_icon_html(x, rune_name_to_img))
rn["보조룬"] = rn["rune_sub"].apply(lambda x: add_icon_html(x, rune_name_to_img))
aggrid_table(rn[["메인룬","보조룬","games","wins","win_rate"]], ["메인룬","보조룬"])
