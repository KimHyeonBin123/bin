import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")
CSV_PATH = "./aram_participants_clean_preprocessed.csv"

# --- Load Data ---
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df['win_clean'] = df['win'].apply(lambda x: 1 if str(x).lower() in ('1','true','t','yes') else 0)
    item_cols = [c for c in df.columns if c.startswith('item')]
    for c in item_cols:
        df[c] = df[c].fillna('').astype(str).str.strip()
    df['spell1'] = df['spell1'].astype(str).str.strip()
    df['spell2'] = df['spell2'].astype(str).str.strip()
    df['rune_core'] = df['rune_core'].astype(str).str.strip()
    df['rune_sub'] = df['rune_sub'].astype(str).str.strip()
    return df

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

# --- 사이드바 ---
champion_list = sorted(df['champion'].unique())
selected_champion = st.sidebar.selectbox("Select Champion", champion_list)
champ_df = df[df['champion']==selected_champion]

# --- 아이템 통계 ---
def compute_item_stats(df):
    item_cols = [c for c in df.columns if c.startswith('item')]
    records = []
    for c in item_cols:
        tmp = df[['matchId','win_clean',c]].rename(columns={c:'item'})
        records.append(tmp)
    union = pd.concat(records, ignore_index=True)
    union = union[union['item']!='']
    stats = union.groupby('item').agg(total_picks=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_picks']*100).round(2)
    stats['pick_rate'] = (stats['total_picks']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

# --- Spell 통계 ---
def compute_spell_stats(df):
    stats = df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

# --- Rune 통계 ---
def compute_rune_stats(df):
    stats = df.groupby(['rune_core','rune_sub']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

# --- Helper: add icon HTML ---
def add_icon_html(name, img_dict, width=20):
    img_file = img_dict.get(name)
    if img_file:
        return f'<img src="http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img_file}" width="{width}" style="vertical-align:middle;"> {name}'
    else:
        return name

# --- 아이템 표 ---
st.subheader("Recommended Items")
items = compute_item_stats(champ_df)
items["item"] = items["item"].apply(lambda x: add_icon_html(x, item_name_to_img, width=20))
st.markdown(items.to_html(escape=False, index=False), unsafe_allow_html=True)

# --- Spell 표 ---
st.subheader("Recommended Spell Combos")
spells = compute_spell_stats(champ_df)
spells["spell1"] = spells["spell1"].apply(lambda x: add_icon_html(x, spell_name_to_img, width=15))
spells["spell2"] = spells["spell2"].apply(lambda x: add_icon_html(x, spell_name_to_img, width=15))
st.markdown(spells.to_html(escape=False, index=False), unsafe_allow_html=True)

# --- Rune 표 ---
st.subheader("Recommended Runes")
runes = compute_rune_stats(champ_df)
runes["rune_core"] = runes["rune_core"].apply(lambda x: add_icon_html(x, rune_name_to_img, width=15))
runes["rune_sub"] = runes["rune_sub"].apply(lambda x: add_icon_html(x, rune_name_to_img, width=15))
st.markdown(runes.to_html(escape=False, index=False), unsafe_allow_html=True)

# --- Raw Data ---
st.subheader("Raw Data")
st.dataframe(champ_df)
