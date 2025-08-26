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

df = load_data(CSV_PATH)
champion_list = sorted(df['champion'].unique())
selected_champion = st.sidebar.selectbox('Select Champion', champion_list)
champ_df = df[df['champion']==selected_champion]

# --- Load DDragon Resources ---
item_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/item.json").json()
item_img = {v["name"]: v["image"]["full"] for v in item_data["data"].values()}

spell_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/summoner.json").json()
spell_img = {v["name"]: v["image"]["full"] for v in spell_data["data"].values()}

rune_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.17.1/data/ko_KR/runesReforged.json").json()
rune_img = {}
for tree in rune_data:
    rune_img[tree["name"]] = tree["icon"]
    for slot in tree["slots"]:
        for rune in slot["runes"]:
            rune_img[rune["name"]] = rune["icon"]

# --- Champion Summary ---
st.title(f"Champion: {selected_champion}")
champ_stats = champ_df['win_clean'].agg(['count','mean'])
st.metric("Games Played", champ_stats['count'])
st.metric("Win Rate (%)", round(champ_stats['mean']*100,2))
st.metric("Pick Rate (%)", round(len(champ_df)/df['matchId'].nunique()*100,2))

# --- Recommended Items (small icons) ---
st.subheader("Recommended Items")
item_cols = [c for c in champ_df.columns if c.startswith('item')]
item_records = []
for c in item_cols:
    tmp = champ_df[[c,'win_clean']].rename(columns={c:'item'})
    item_records.append(tmp)
items_union = pd.concat(item_records, axis=0)
items_union = items_union[items_union['item']!='']
items_stats = items_union.groupby('item').agg(total=('item','count'), wins=('win_clean','sum')).reset_index()
items_stats['win_rate'] = (items_stats['wins']/items_stats['total']*100).round(1)

# HTML 테이블로 아이콘 + 글자 표시
items_html = "<table><tr>"
for idx, row in items_stats.head(20).iterrows():
    icon = item_img.get(row['item'], "")
    if icon:
        items_html += f"<td style='text-align:center;padding:4px'>"
        items_html += f"<img src='http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{icon}' width='30'><br>"
        items_html += f"<span style='font-size:10px'>{row['item']}<br>WR:{row['win_rate']}%</span></td>"
items_html += "</tr></table>"
st.markdown(items_html, unsafe_allow_html=True)

# --- Recommended Spells ---
st.subheader("Recommended Spell Combos")
spells_stats = champ_df.groupby(['spell1','spell2']).agg(total=('matchId','count'), wins=('win_clean','sum')).reset_index()
spells_stats['win_rate'] = (spells_stats['wins']/spells_stats['total']*100).round(1)

spells_html = "<table><tr>"
for idx, row in spells_stats.head(10).iterrows():
    s1_icon = spell_img.get(row['spell1'], "")
    s2_icon = spell_img.get(row['spell2'], "")
    spells_html += "<td style='text-align:center;padding:4px'>"
    if s1_icon:
        spells_html += f"<img src='http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{s1_icon}' width='25'>"
    if s2_icon:
        spells_html += f"<img src='http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{s2_icon}' width='25'><br>"
    spells_html += f"<span style='font-size:10px'>{row['spell1']}+{row['spell2']}<br>WR:{row['win_rate']}%</span></td>"
spells_html += "</tr></table>"
st.markdown(spells_html, unsafe_allow_html=True)

# --- Recommended Runes ---
st.subheader("Recommended Runes")
runes_stats = champ_df.groupby(['rune_core','rune_sub']).agg(total=('matchId','count'), wins=('win_clean','sum')).reset_index()
runes_stats['win_rate'] = (runes_stats['wins']/runes_stats['total']*100).round(1)

runes_html = "<table><tr>"
for idx, row in runes_stats.head(10).iterrows():
    core_icon = rune_img.get(row['rune_core'], "")
    sub_icon = rune_img.get(row['rune_sub'], "")
    runes_html += "<td style='text-align:center;padding:4px'>"
    if core_icon:
        runes_html += f"<img src='http://ddragon.leagueoflegends.com/cdn/img/{core_icon}' width='25'>"
    if sub_icon:
        runes_html += f"<img src='http://ddragon.leagueoflegends.com/cdn/img/{sub_icon}' width='25'><br>"
    runes_html += f"<span style='font-size:10px'>{row['rune_core']}+{row['rune_sub']}<br>WR:{row['win_rate']}%</span></td>"
runes_html += "</tr></table>"
st.markdown(runes_html, unsafe_allow_html=True)

# --- Raw Data ---
st.subheader("Raw Data (Filtered)")
st.dataframe(champ_df)
