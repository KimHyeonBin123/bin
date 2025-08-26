"""
Streamlit ARAM PS Dashboard — Champion-centric (AgGrid)
File: streamlit_aram_ps_app_champion_aggrid.py
"""

import streamlit as st
import pandas as pd
import requests
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")
CSV_PATH = "./aram_participants_clean_preprocessed.csv"

# --- 데이터 로드 ---
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # win 컬럼 정리
    if 'win' in df.columns:
        df['win_clean'] = df['win'].apply(lambda x: 1 if str(x).lower() in ('1','true','t','yes') else 0)
    else:
        df['win_clean'] = 0
    item_cols = [c for c in df.columns if c.startswith('item')]
    for c in item_cols:
        df[c] = df[c].fillna('').astype(str).str.strip()
    df['spell1'] = df['spell1'].astype(str).str.strip()
    df['spell2'] = df['spell2'].astype(str).str.strip()
    df['rune_core'] = df['rune_core'].astype(str).str.strip()
    df['rune_sub'] = df['rune_sub'].astype(str).str.strip()
    return df

# --- Stats 계산 ---
def compute_champion_stats(df, champion):
    df_champ = df[df['champion']==champion]
    total_matches = df['matchId'].nunique()
    total_games = len(df_champ)
    win_rate = round(df_champ['win_clean'].mean()*100,2)
    pick_rate = round(total_games/total_matches*100,2)
    return pd.DataFrame({'champion':[champion],
                         'total_games':[total_games],
                         'win_rate':[win_rate],
                         'pick_rate':[pick_rate]})

def compute_item_stats(df):
    item_cols = [c for c in df.columns if c.startswith('item')]
    records = []
    for c in item_cols:
        tmp = df[['matchId','win_clean',c]].rename(columns={c:'item'})
        records.append(tmp)
    union = pd.concat(records, axis=0, ignore_index=True)
    union = union[union['item'] != '']
    stats = union.groupby('item').agg(total_picks=('matchId','count'),
                                      wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_picks']*100).round(2)
    total_matches = df['matchId'].nunique()
    stats['pick_rate'] = (stats['total_picks']/total_matches*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

def compute_spell_stats(df):
    stats = df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'),
                                                wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

def compute_rune_stats(df):
    stats = df.groupby(['rune_core','rune_sub']).agg(total_games=('matchId','count'),
                                                     wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

# --- Load Data ---
with st.spinner('Loading data...'):
    df = load_data(CSV_PATH)

# --- Data Dragon Resources ---
# 아이템
item_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/item.json").json()
item_name_to_img = {v["name"]: v["image"]["full"] for k,v in item_data["data"].items()}

# 스펠
spell_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/summoner.json").json()
spell_name_to_img = {v["name"]: v["image"]["full"] for k,v in spell_data["data"].items()}

# 룬
rune_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/runesReforged.json").json()
rune_name_to_img = {}
for tree in rune_data:
    rune_name_to_img[tree["name"]] = tree["icon"]
    for slot in tree["slots"]:
        for rune in slot["runes"]:
            rune_name_to_img[rune["name"]] = rune["icon"]

# --- Sidebar ---
champion_list = sorted(df['champion'].unique().tolist())
selected_champion = st.sidebar.selectbox('Select Champion', champion_list)
champ_df = df[df['champion']==selected_champion]

# --- Champion Summary ---
st.title(f"Champion: {selected_champion}")
champ_summary = compute_champion_stats(df, selected_champion)
st.metric("Games Played", champ_summary['total_games'].values[0])
st.metric("Win Rate (%)", champ_summary['win_rate'].values[0])
st.metric("Pick Rate (%)", champ_summary['pick_rate'].values[0])

# --- Helper to add icon ---
def add_icon_html(name, img_dict, width=20):
    img_file = img_dict.get(name)
    if img_file:
        url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img_file}" if 'item' in img_file else f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/{img_file}"
        return f'<img src="{url}" width="{width}"/> {name}'
    return name

# --- Recommended Items ---
st.subheader('Recommended Items')
items = compute_item_stats(champ_df)
items['item'] = items['item'].apply(lambda x: add_icon_html(x, item_name_to_img, width=20))

gb = GridOptionsBuilder.from_dataframe(items)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
gb.configure_column("item", cellRenderer='html')
gridOptions = gb.build()
AgGrid(items, gridOptions=gridOptions, enable_enterprise_modules=False, fit_columns_on_grid_load=True)

# --- Recommended Spells ---
st.subheader('Recommended Spell Combos')
spells = compute_spell_stats(champ_df)
spells['spell1'] = spells['spell1'].apply(lambda x: add_icon_html(x, spell_name_to_img, width=20))
spells['spell2'] = spells['spell2'].apply(lambda x: add_icon_html(x, spell_name_to_img, width=20))

gb = GridOptionsBuilder.from_dataframe(spells)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
gb.configure_column("spell1", cellRenderer='html')
gb.configure_column("spell2", cellRenderer='html')
gridOptions = gb.build()
AgGrid(spells, gridOptions=gridOptions, enable_enterprise_modules=False, fit_columns_on_grid_load=True)

# --- Recommended Runes ---
st.subheader('Recommended Rune Combos')
runes = compute_rune_stats(champ_df)
runes['rune_core'] = runes['rune_core'].apply(lambda x: add_icon_html(x, rune_name_to_img, width=20))
runes['rune_sub'] = runes['rune_sub'].apply(lambda x: add_icon_html(x, rune_name_to_img, width=20))

gb = GridOptionsBuilder.from_dataframe(runes)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
gb.configure_column("rune_core", cellRenderer='html')
gb.configure_column("rune_sub", cellRenderer='html')
gridOptions = gb.build()
AgGrid(runes, gridOptions=gridOptions, enable_enterprise_modules=False, fit_columns_on_grid_load=True)

# --- Raw Data ---
st.subheader('Raw Data (Filtered)')
st.dataframe(champ_df)
