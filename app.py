import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")
CSV_PATH = "./aram_participants_clean_preprocessed.csv"

# --- 데이터 로드 ---
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
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

# --- 통계 계산 ---
def compute_item_stats(df):
    item_cols = [c for c in df.columns if c.startswith('item')]
    records = []
    for c in item_cols:
        tmp = df[['matchId','win_clean',c]].rename(columns={c:'item'})
        records.append(tmp)
    union = pd.concat(records, ignore_index=True)
    union = union[union['item']!='']
    stats = union.groupby('item').agg(total_picks=('matchId','count'),
                                     wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_picks']*100).round(2)
    stats['pick_rate'] = (stats['total_picks']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

def compute_spell_stats(df):
    stats = df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'),
                                                 wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

def compute_rune_stats(df):
    stats = df.groupby(['rune_core','rune_sub']).agg(total_games=('matchId','count'),
                                                      wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

# --- 데이터 로드 ---
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

# --- 사이드바 ---
st.sidebar.title('ARAM PS Controls')
champion_list = sorted(df['champion'].unique())
selected_champion = st.sidebar.selectbox("Select Champion", champion_list)
champ_df = df[df['champion']==selected_champion]

st.title(f"Champion: {selected_champion}")
st.metric("Games Played", len(champ_df))
st.metric("Win Rate (%)", round(champ_df['win_clean'].mean()*100,2))
st.metric("Pick Rate (%)", round(len(champ_df)/df['matchId'].nunique()*100,2))

# --- Plotly Table Helper ---
def plot_table_with_icons(df_stats, name_col, img_dict, top_n=10):
    df_stats = df_stats.head(top_n).copy()
    imgs = []
    names = []
    wrs = []
    prs = []
    for _, row in df_stats.iterrows():
        name = row[name_col]
        img_file = img_dict.get(name, None)
        if img_file:
            img_tag = f'<img src="http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img_file}" width="25px">'
        else:
            img_tag = ''
        imgs.append(img_tag)
        names.append(name)
        wrs.append(f"{row['win_rate']}%")
        prs.append(f"{row['pick_rate']}%")
    fig = go.Figure(data=[go.Table(
        header=dict(values=["아이콘","이름","Win Rate","Pick Rate"],
                    fill_color='lightblue', align='center'),
        cells=dict(values=[imgs,names,wrs,prs],
                   fill_color='lavender', align='center'),
    )])
    st.plotly_chart(fig, use_container_width=True)

# --- 아이템 ---
st.subheader("Recommended Items")
items = compute_item_stats(champ_df)
plot_table_with_icons(items, "item", item_name_to_img, top_n=10)

# --- 스펠 ---
st.subheader("Recommended Spells")
spells = compute_spell_stats(champ_df)
# spell은 img url 다름
spell_img_dict = {k:f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{v}" for k,v in spell_name_to_img.items()}
plot_table_with_icons(spells, "spell1", spell_img_dict, top_n=10)  # spell1 기준

# --- 룬 ---
st.subheader("Recommended Runes")
runes = compute_rune_stats(champ_df)
rune_img_dict = {k:f"http://ddragon.leagueoflegends.com/cdn/img/{v}" for k,v in rune_name_to_img.items()}
plot_table_with_icons(runes, "rune_core", rune_img_dict, top_n=10)
