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

# --- Sidebar ---
champion_list = sorted(df['champion'].unique())
selected_champion = st.sidebar.selectbox("Select Champion", champion_list)
champ_df = df[df['champion']==selected_champion]

# --- Champion Icon ---
champ_icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/champion/{selected_champion}.png"
st.image(champ_icon_url, width=80)
st.subheader(selected_champion)

# --- Utility to display cards ---
def display_cards(data, img_map, is_dual=False, top_n=10, cols_per_row=5):
    for i in range(0, min(len(data), top_n), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, row in enumerate(data.iloc[i:i+cols_per_row].itertuples()):
            col = cols[j]
            if is_dual:
                img1 = img_map.get(row[1])
                img2 = img_map.get(row[2])
                if img1:
                    col.image(f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{img1}", width=40)
                if img2:
                    col.image(f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{img2}", width=40)
                col.caption(f"{row[1]} + {row[2]}\nWR:{row.win_rate}%\nPR:{row.pick_rate}%")
            else:
                img = img_map.get(row[1])
                if img:
                    if "item" in img_map:  # item
                        url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img}"
                    else:  # rune
                        url = f"http://ddragon.leagueoflegends.com/cdn/img/{img}"
                    col.image(url, width=50)
                if hasattr(row, 'rune_core'):
                    col.caption(f"{row.rune_core} + {row.rune_sub}\nWR:{row.win_rate}%\nPR:{row.pick_rate}%")
                else:
                    col.caption(f"{row[1]}\nWR:{row.win_rate}%\nPR:{row.pick_rate}%")

# --- Items ---
st.subheader("Recommended Items")
items = compute_item_stats(champ_df)
display_cards(items, item_name_to_img, is_dual=False, top_n=10, cols_per_row=5)

# --- Spells ---
st.subheader("Recommended Spell Combos")
spells = compute_spell_stats(champ_df)
display_cards(spells, spell_name_to_img, is_dual=True, top_n=10, cols_per_row=5)

# --- Runes ---
st.subheader("Recommended Runes")
runes = compute_rune_stats(champ_df)
display_cards(runes, rune_name_to_img, is_dual=False, top_n=9, cols_per_row=3)

# --- Raw Data ---
st.subheader("Raw Data")
st.dataframe(champ_df)
