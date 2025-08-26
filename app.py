"""
Streamlit ARAM PS Dashboard — Champion-centric with Icons
"""

import streamlit as st
import pandas as pd
from typing import List

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

CSV_PATH = "./aram_participants_clean_preprocessed.csv"

# --- Data Load ---
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if 'win' in df.columns:
        df['win_clean'] = df['win'].apply(lambda x: 1 if str(x).lower() in ('1','true','t','yes','1.0') else 0)
    else:
        df['win_clean'] = 0
    item_cols = [c for c in df.columns if c.startswith('item')]
    for c in item_cols:
        df[c] = df[c].fillna('').astype(str).str.strip()
    return df

# --- Champion stats ---
@st.cache_data
def compute_champion_stats(df: pd.DataFrame, champion: str) -> pd.DataFrame:
    df_champ = df[df['champion']==champion]
    total_matches = df['matchId'].nunique()
    total_games = len(df_champ)
    win_rate = round(df_champ['win_clean'].mean()*100,2)
    pick_rate = round(total_games/total_matches*100,2)
    return pd.DataFrame({'champion':[champion],'total_games':[total_games],'win_rate':[win_rate],'pick_rate':[pick_rate]})

# --- Item stats ---
@st.cache_data
def compute_item_stats(df: pd.DataFrame) -> pd.DataFrame:
    item_cols = [c for c in df.columns if c.startswith('item')]
    records = []
    for c in item_cols:
        tmp = df[['matchId','win_clean',c]].rename(columns={c:'item'})
        records.append(tmp)
    union = pd.concat(records, axis=0, ignore_index=True)
    union = union[union['item'].astype(str) != '']
    stats = (union.groupby('item')
             .agg(total_picks=('matchId','count'), wins=('win_clean','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins']/stats['total_picks']*100).round(2)
    total_matches = df['matchId'].nunique()
    stats['pick_rate'] = (stats['total_picks']/total_matches*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

# --- Spell stats ---
@st.cache_data
def compute_spell_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

# --- Rune stats ---
@st.cache_data
def compute_rune_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby(['rune_core','rune_sub']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

# --- Load ---
with st.spinner('Loading data...'):
    df = load_data(CSV_PATH)

# --- Sidebar ---
st.sidebar.title('ARAM PS Controls')
champion_list = sorted(df['champion'].unique().tolist())
selected_champion = st.sidebar.selectbox('Select Champion', champion_list)

# --- Champion Summary ---
st.title(f"Champion: {selected_champion}")
champ_summary = compute_champion_stats(df, selected_champion)
st.metric("Games Played", champ_summary['total_games'].values[0])
st.metric("Win Rate (%)", champ_summary['win_rate'].values[0])
st.metric("Pick Rate (%)", champ_summary['pick_rate'].values[0])

# 챔피언 아이콘
champ_icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/champion/{selected_champion}.png"
st.image(champ_icon_url, width=80)

# --- Recommended Items with Icons ---
st.subheader('Recommended Items')
items = compute_item_stats(df[df['champion']==selected_champion])
# 아이템 이름 → 아이템 ID 매핑 필요 (예: 수동 혹은 dict)
item_name_to_id = {
    "광전사의 군화":3006, "마법사의 신발":3020, "닌자의 신발":3047, 
    "헤르메스의 발걸음":3111, "신속의 장화":3009, 
    "명석함의 아이오니아 장화":3158, "기동력의 장화":3009
}
cols = st.columns(5)
for idx, row in items.head(10).iterrows():
    col = cols[idx%5]
    item_id = item_name_to_id.get(row['item'], None)
    if item_id:
        url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{item_id}.png"
        col.image(url, width=50)
    col.caption(f"{row['item']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Recommended Spells with Icons ---
st.subheader('Recommended Spell Combos')
spells = compute_spell_stats(df[df['champion']==selected_champion])
# Summoner spell ID → 이름 → 이미지 URL 예시
spell_name_to_img = {
    "Flash":"SummonerFlash.png", "Ignite":"SummonerDot.png", 
    "Heal":"SummonerHeal.png","Teleport":"SummonerTeleport.png",
    "Smite":"SummonerSmite.png","Exhaust":"SummonerExhaust.png",
    "Barrier":"SummonerBarrier.png","Cleanse":"SummonerBoost.png"
}
cols = st.columns(5)
for idx, row in spells.head(10).iterrows():
    col = cols[idx%5]
    spell1_img = spell_name_to_img.get(row['spell1'], None)
    spell2_img = spell_name_to_img.get(row['spell2'], None)
    if spell1_img and spell2_img:
        col.image([f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{spell1_img}",
                   f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{spell2_img}"], width=40)
    col.caption(f"{row['spell1']} + {row['spell2']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Recommended Rune Combos ---
st.subheader('Recommended Rune Combos')
runes = compute_rune_stats(df[df['champion']==selected_champion])
cols = st.columns(3)
for idx, row in runes.head(10).iterrows():
    col = cols[idx%3]
    # 기본 Data Dragon URL 구조: https://developer.riotgames.com/docs/lol#data-dragon
    # 임시 예시: 룬 이미지는 직접 다운로드 혹은 id 기반 매핑 필요
    col.write(f"{row['rune_core']} + {row['rune_sub']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Raw Data ---
st.subheader('Raw Data (Filtered)')
st.dataframe(df[df['champion']==selected_champion])
