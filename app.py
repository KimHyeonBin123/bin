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
    for c in [col for col in df.columns if col.startswith('item')]:
        df[c] = df[c].fillna('').astype(str).str.strip()
    for c in ['spell1','spell2','rune_core','rune_sub']:
        df[c] = df[c].astype(str).str.strip()
    return df

# --- Compute Stats ---
def compute_item_stats(df):
    records = []
    for c in [col for col in df.columns if col.startswith('item')]:
        records.append(df[['matchId','win_clean',c]].rename(columns={c:'item'}))
    union = pd.concat(records, ignore_index=True)
    union = union[union['item']!='']
    stats = union.groupby('item').agg(total_picks=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_picks']*100).round(2)
    stats['pick_rate'] = (stats['total_picks']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

def compute_spell_stats(df):
    stats = df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

def compute_rune_stats(df):
    stats = df.groupby(['rune_core','rune_sub']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

# --- Load Data ---
df = load_data(CSV_PATH)

# --- Data Dragon Resources ---
item_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/item.json").json()
item_name_to_img = {v["name"]: v["image"]["full"] for v in item_data["data"].values()}

spell_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/summoner.json").json()
spell_name_to_img = {v["name"]: v["image"]["full"] for v in spell_data["data"].values()}

rune_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/runesReforged.json").json()
rune_name_to_img = {}
for tree in rune_data:
    rune_name_to_img[tree["name"]] = tree["icon"]
    for slot in tree["slots"]:
        for rune in slot["runes"]:
            rune_name_to_img[rune["name"]] = rune["icon"]

# --- Sidebar ---
champion_list = sorted(df['champion'].unique())
selected_champion = st.sidebar.selectbox("Select Champion", champion_list)
champ_df = df[df['champion']==selected_champion]

# --- Champion Icon ---
champ_icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/champion/{selected_champion}.png"
st.image(champ_icon_url, width=80)
st.subheader(selected_champion)

# --- Items ---
st.subheader("Recommended Items")
items = compute_item_stats(champ_df)
cols_per_row = 5
for i in range(0, min(10,len(items)), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, row in enumerate(items.iloc[i:i+cols_per_row].itertuples()):
        col = cols[j]
        img_file = item_name_to_img.get(row.item)
        if img_file:
            url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img_file}"
            col.image(url, width=45)
        col.markdown(f"<span style='font-size:12px'>{row.item}<br>WR:{row.win_rate}% PR:{row.pick_rate}%</span>", unsafe_allow_html=True)

# --- Spells ---
st.subheader("Recommended Spell Combos")
spells = compute_spell_stats(champ_df)
cols_per_row = 5
for i in range(0, min(10,len(spells)), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, row in enumerate(spells.iloc[i:i+cols_per_row].itertuples()):
        col = cols[j]
        s1 = spell_name_to_img.get(row.spell1)
        s2 = spell_name_to_img.get(row.spell2)
        if s1:
            col.image(f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{s1}", width=40)
        if s2:
            col.image(f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{s2}", width=40)
        col.markdown(f"<span style='font-size:12px'>{row.spell1} + {row.spell2}<br>WR:{row.win_rate}% PR:{row.pick_rate}%</span>", unsafe_allow_html=True)

# --- Runes ---
st.subheader("Recommended Runes")
runes = compute_rune_stats(champ_df)
cols_per_row = 3
for i in range(0, min(9,len(runes)), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, row in enumerate(runes.iloc[i:i+cols_per_row].itertuples()):
        col = cols[j]
        core_icon = rune_name_to_img.get(row.rune_core)
        sub_icon = rune_name_to_img.get(row.rune_sub)
        if core_icon:
            col.image(f"http://ddragon.leagueoflegends.com/cdn/img/{core_icon}", width=40)
        if sub_icon:
            col.image(f"http://ddragon.leagueoflegends.com/cdn/img/{sub_icon}", width=40)
        col.markdown(f"<span style='font-size:12px'>{row.rune_core} + {row.rune_sub}<br>WR:{row.win_rate}% PR:{row.pick_rate}%</span>", unsafe_allow_html=True)

# --- Raw Data ---
st.subheader("Raw Data")
st.dataframe(champ_df)
