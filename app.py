import streamlit as st
import pandas as pd

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

# --- Load ---
df = load_data(CSV_PATH)

# --- Sidebar ---
champion_list = sorted(df['champion'].unique())
selected_champion = st.sidebar.selectbox("Select Champion", champion_list)

champ_df = df[df['champion']==selected_champion]

# --- Champion Icon ---
champ_icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/champion/{selected_champion}.png"
st.image(champ_icon_url, width=80)

# --- Recommended Items ---
st.subheader("Recommended Items")
items = compute_item_stats(champ_df)
# 이름 → 아이템ID 매핑 (예시)
item_name_to_id = {
    "광전사의 군화":3006, "마법사의 신발":3020, "닌자의 신발":3047,
    "헤르메스의 발걸음":3111, "신속의 장화":3009, "명석함의 아이오니아 장화":3158,
    "기동력의 장화":3009
}

cols = st.columns(5)
for idx, row in items.head(10).iterrows():
    col = cols[idx%5]
    item_id = item_name_to_id.get(row['item'], None)
    if item_id:
        url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{item_id}.png"
        col.image(url, width=50)
    col.caption(f"{row['item']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Recommended Spells ---
st.subheader("Recommended Spells")
spells = compute_spell_stats(champ_df)
spell_name_to_img = {
    "Flash":"SummonerFlash.png", "Ignite":"SummonerDot.png", 
    "Heal":"SummonerHeal.png","Teleport":"SummonerTeleport.png",
    "Smite":"SummonerSmite.png","Exhaust":"SummonerExhaust.png",
    "Barrier":"SummonerBarrier.png","Cleanse":"SummonerBoost.png"
}

cols = st.columns(5)
for idx, row in spells.head(10).iterrows():
    col = cols[idx%5]
    s1 = spell_name_to_img.get(row['spell1'])
    s2 = spell_name_to_img.get(row['spell2'])
    if s1 and s2:
        col.image([f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{s1}",
                   f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{s2}"], width=40)
    col.caption(f"{row['spell1']}+{row['spell2']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Recommended Runes ---
st.subheader("Recommended Runes")
runes = compute_rune_stats(champ_df)
# 임시: 이름만 표시, 아이콘은 룬 ID 매핑 필요
cols = st.columns(3)
for idx, row in runes.head(9).iterrows():
    col = cols[idx%3]
    col.write(f"{row['rune_core']} + {row['rune_sub']}\nWR:{row['win_rate']}%\nPR:{row['pick_rate']}%")

# --- Raw Data ---
st.subheader("Raw Data")
st.dataframe(champ_df)
