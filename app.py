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

# --- 챔피언 선택 ---
champion_list = sorted(df['champion'].unique())
selected_champion = st.sidebar.selectbox("Select Champion", champion_list)
champ_df = df[df['champion']==selected_champion]

st.title(f"Champion: {selected_champion}")

# --- 추천 아이템 ---
st.subheader("Recommended Items")
item_cols = [c for c in champ_df.columns if c.startswith('item')]
records = []
for c in item_cols:
    tmp = champ_df[['matchId','win_clean',c]].rename(columns={c:'item'})
    records.append(tmp)
union = pd.concat(records, ignore_index=True)
union = union[union['item']!='']
stats = union.groupby('item').agg(total_picks=('matchId','count'), wins=('win_clean','sum')).reset_index()
stats['win_rate'] = (stats['wins']/stats['total_picks']*100).round(2)
stats['pick_rate'] = (stats['total_picks']/champ_df['matchId'].nunique()*100).round(2)
stats = stats.sort_values('win_rate', ascending=False).head(10)

# HTML 테이블 생성
html_items = '<table style="border-collapse: collapse;">'
html_items += '<tr>'
for _, row in stats.iterrows():
    img_url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{item_name_to_img.get(row["item"], "")}"
    html_items += f'<td style="text-align:center; padding:4px;">'
    html_items += f'<img src="{img_url}" width="25px"><br>'
    html_items += f'{row["item"]}<br>WR:{row["win_rate"]}%<br>PR:{row["pick_rate"]}%'
    html_items += '</td>'
html_items += '</tr></table>'
st.markdown(html_items, unsafe_allow_html=True)

# --- 추천 스펠 ---
st.subheader("Recommended Spell Combos")
spells = champ_df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
spells['win_rate'] = (spells['wins']/spells['total_games']*100).round(2)
spells['pick_rate'] = (spells['total_games']/champ_df['matchId'].nunique()*100).round(2)
spells = spells.sort_values('win_rate', ascending=False).head(10)

html_spells = '<table style="border-collapse: collapse;">'
html_spells += '<tr>'
for _, row in spells.iterrows():
    s1_url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{spell_name_to_img.get(row['spell1'], '')}"
    s2_url = f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{spell_name_to_img.get(row['spell2'], '')}"
    html_spells += f'<td style="text-align:center; padding:4px;">'
    html_spells += f'<img src="{s1_url}" width="20px"> + <img src="{s2_url}" width="20px"><br>'
    html_spells += f'{row["spell1"]} + {row["spell2"]}<br>WR:{row["win_rate"]}%<br>PR:{row["pick_rate"]}%'
    html_spells += '</td>'
html_spells += '</tr></table>'
st.markdown(html_spells, unsafe_allow_html=True)

# --- 추천 룬 ---
st.subheader("Recommended Runes")
runes = champ_df.groupby(['rune_core','rune_sub']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
runes['win_rate'] = (runes['wins']/runes['total_games']*100).round(2)
runes['pick_rate'] = (runes['total_games']/champ_df['matchId'].nunique()*100).round(2)
runes = runes.sort_values('win_rate', ascending=False).head(10)

html_runes = '<table style="border-collapse: collapse;">'
html_runes += '<tr>'
for _, row in runes.iterrows():
    core_url = f"http://ddragon.leagueoflegends.com/cdn/img/{rune_name_to_img.get(row['rune_core'], '')}"
    sub_url = f"http://ddragon.leagueoflegends.com/cdn/img/{rune_name_to_img.get(row['rune_sub'], '')}"
    html_runes += f'<td style="text-align:center; padding:4px;">'
    html_runes += f'<img src="{core_url}" width="25px"> + <img src="{sub_url}" width="20px"><br>'
    html_runes += f'{row["rune_core"]} + {row["rune_sub"]}<br>WR:{row["win_rate"]}%<br>PR:{row["pick_rate"]}%'
    html_runes += '</td>'
html_runes += '</tr></table>'
st.markdown(html_runes, unsafe_allow_html=True)
