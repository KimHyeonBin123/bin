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

# --- Compute Stats ---
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
    main_id = tree["id"]
    main_icon = tree["icon"]
    rune_name_to_img[tree["name"]] = main_icon
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
cols = st.columns(5)
for idx, row in items.head(10).iterrows():
    col = cols[idx%5]
    img_file = item_name_to_img.get(row['item'])
    if img_file:
        url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img_file}"
        col.image(url, width=50)
    col.caption(f"{row['item']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Spells ---
st.subheader("Recommended Spell Combos")
spells = compute_spell_stats(champ_df)
cols = st.columns(5)
for idx, row in spells.head(10).iterrows():
    col = cols[idx%5]
    s1 = spell_name_to_img.get(row['spell1'])
    s2 = spell_name_to_img.get(row['spell2'])
    if s1:
        col.image(f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{s1}", width=40)
    if s2:
        col.image(f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{s2}", width=40)
    col.caption(f"{row['spell1']} + {row['spell2']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Runes ---
st.subheader("Recommended Runes")
runes = compute_rune_stats(champ_df)
cols = st.columns(3)
for idx, row in runes.head(9).iterrows():
    col = cols[idx%3]
    core_icon = rune_name_to_img.get(row['rune_core'])
    sub_icon = rune_name_to_img.get(row['rune_sub'])
    if core_icon:
        col.image(f"http://ddragon.leagueoflegends.com/cdn/img/{core_icon}", width=50)
    if sub_icon:
        col.image(f"http://ddragon.leagueoflegends.com/cdn/img/{sub_icon}", width=50)
    col.caption(f"{row['rune_core']} + {row['rune_sub']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Raw Data ---
st.subheader("Raw Data")
st.dataframe(champ_df)
