# app.py
import streamlit as st
import pandas as pd
import requests
from typing import Dict, Any

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")

CSV_PATH = "./aram_participants_clean_preprocessed.csv"

# ---------- Data Dragon 버전/매핑 ----------
@st.cache_data(show_spinner=False)
def get_dd_version() -> str:
    # Data Dragon 최신 버전 (가장 앞 인덱스가 최신)
    ver = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10).json()
    return ver

@st.cache_data(show_spinner=False)
def load_dd_maps(version: str, lang: str = "ko_KR") -> Dict[str, Any]:
    base = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{lang}"
    champions = requests.get(f"{base}/champion.json", timeout=10).json()["data"]  # name->data
    items = requests.get(f"{base}/item.json", timeout=10).json()["data"]          # id(str)->data
    spells = requests.get(f"{base}/summoner.json", timeout=10).json()["data"]     # key->data
    runes = requests.get("https://ddragon.leagueoflegends.com/cdn/data/en_US/runesReforged.json", timeout=10).json()

    # 챔피언: numeric key("266") -> canonical name("Aatrox") 매핑
    champ_key_to_name = {v["key"]: k for k, v in champions.items()}
    # 주문: numeric id 문자열 -> 이미지 파일명(id, 예: "SummonerFlash")
    spell_id_to_file = {v["key"]: v["id"] for v in spells.values()}

    # 룬: perk/style id -> perk-images 경로
    rune_id_to_img = {}
    style_id_to_img = {}
    for style in runes:
        style_id_to_img[style["id"]] = style.get("icon")  # ex: perk-images/Styles/Domination/Domination.png
        for slot in style.get("slots", []):
            for perk in slot.get("runes", []):
                rune_id_to_img[perk["id"]] = perk["icon"]  # ex: perk-images/Styles/Domination/Electrocute/Electrocute.png

    return {
        "champions": champions,
        "items": items,
        "spells": spells,
        "champ_key_to_name": champ_key_to_name,
        "spell_id_to_file": spell_id_to_file,
        "rune_id_to_img": rune_id_to_img,
        "style_id_to_img": style_id_to_img,
    }

# ---------- 아이콘 URL 빌더 ----------
def dd_champion_icon(version: str, champ_name: str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_name}.png"

def dd_item_icon(version: str, item_id: int | str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png"

def dd_spell_icon(version: str, spell_file: str) -> str:
    # spell_file는 보통 "SummonerFlash" 같은 id를 사용 (확실하고 안정적)
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{spell_file}.png"

def dd_rune_icon(perk_path: str) -> str:
    # 룬은 버전 세그먼트가 없는 공식 경로 사용
    return f"https://ddragon.leagueoflegends.com/cdn/img/{perk_path}"

# ---------- 데이터 로드 ----------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # win 정리
    if 'win' in df.columns:
        df['win_clean'] = df['win'].apply(lambda x: 1 if str(x).lower() in ('1','true','t','yes') else 0)
    else:
        df['win_clean'] = 0
    # item 열 정리
    item_cols = [c for c in df.columns if c.startswith('item')]
    for c in item_cols:
        df[c] = df[c].fillna('').astype(str).str.strip()
    return df

@st.cache_data
def compute_champion_stats(df: pd.DataFrame, champion: str) -> pd.DataFrame:
    df_champ = df[df['champion'] == champion].copy()
    total_matches = df['matchId'].nunique()
    total_games = len(df_champ)
    win_rate = round(df_champ['win_clean'].mean() * 100, 2) if total_games > 0 else 0.0
    pick_rate = round(total_games / total_matches * 100, 2) if total_matches > 0 else 0.0
    return pd.DataFrame({
        'champion': [champion],
        'total_games': [total_games],
        'win_rate': [win_rate],
        'pick_rate': [pick_rate],
    })

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

@st.cache_data
def compute_spell_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

@st.cache_data
def compute_rune_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby(['rune_core','rune_sub']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    stats = stats.sort_values('win_rate', ascending=False)
    return stats

# ---------- 앱 ----------
with st.spinner("데이터 불러오는 중..."):
    df = load_data(CSV_PATH)

version = get_dd_version()
maps = load_dd_maps(version, lang="ko_KR")

st.sidebar.title('ARAM PS Controls')
champion_list = sorted(df['champion'].dropna().unique().tolist())
selected_champion = st.sidebar.selectbox('챔피언 선택', champion_list)

# 상단: 챔피언 이름 + 아이콘
st.title(f"Champion: {selected_champion}")
# 선택한 champion이 Data Dragon 파일명 규칙과 일치한다고 가정.
# 만약 CSV가 numeric key를 사용한다면 maps['champ_key_to_name']로 변환 필요.
st.image(dd_champion_icon(version, selected_champion), width=80)

champ_summary = compute_champion_stats(df, selected_champion)
col1, col2, col3 = st.columns(3)
col1.metric("Games Played", int(champ_summary['total_games'].values))
col2.metric("Win Rate (%)", float(champ_summary['win_rate'].values))
col3.metric("Pick Rate (%)", float(champ_summary['pick_rate'].values))

# 추천 아이템
st.subheader('Recommended Items')
items = compute_item_stats(df[df['champion']==selected_champion]).head(20).copy()

def to_item_icon(val: str):
    # CSV의 item 컬럼이 숫자 ID면 그대로 사용
    try:
        iid = int(str(val))
        return dd_item_icon(version, iid)
    except:
        return None

items["icon"] = items["item"].apply(to_item_icon)
st.dataframe(
    items[["icon","item","total_picks","wins","win_rate","pick_rate"]],
    use_container_width=True,
    column_config={
        "icon": st.column_config.ImageColumn("아이콘", width="small"),
        "item": "아이템 ID",
        "total_picks": "픽 수",
        "wins": "승리",
        "win_rate": "승률(%)",
        "pick_rate": "픽률(%)",
    }
)

# 추천 스펠
st.subheader('Recommended Spell Combos')
spells = compute_spell_stats(df[df['champion']==selected_champion]).head(10).copy()

def to_spell_file(name_or_id: str):
    # CSV에 "Flash" 같은 표기면 summoner.json의 id("SummonerFlash")가 더 안전
    # 값이 숫자 id인 경우 maps['spell_id_to_file'] 사용
    s = str(name_or_id)
    if s.isdigit() and s in maps["spell_id_to_file"]:
        return maps["spell_id_to_file"][s]
    # 이미 SummonerFlash 형태면 그대로
    return s if s.startswith("Summoner") else f"Summoner{s}"

spells["spell1_icon"] = spells["spell1"].apply(lambda s: dd_spell_icon(version, to_spell_file(s)))
spells["spell2_icon"] = spells["spell2"].apply(lambda s: dd_spell_icon(version, to_spell_file(s)))

st.dataframe(
    spells[["spell1_icon","spell2_icon","total_games","wins","win_rate","pick_rate"]],
    use_container_width=True,
    column_config={
        "spell1_icon": st.column_config.ImageColumn("스펠1", width="small"),
        "spell2_icon": st.column_config.ImageColumn("스펠2", width="small"),
        "total_games": "게임수",
        "wins": "승리",
        "win_rate": "승률(%)",
        "pick_rate": "픽률(%)",
    }
)

# 추천 룬
st.subheader('Recommended Rune Combos')
runes = compute_rune_stats(df[df['champion']==selected_champion]).head(10).copy()

def to_rune_icon(val):
    # val이 perk/style id(숫자)면 매핑, 이미 perk-images 경로면 그대로
    s = str(val)
    if s.isdigit():
        k = int(s)
        if k in maps["rune_id_to_img"]:
            return dd_rune_icon(maps["rune_id_to_img"][k])
        if k in maps["style_id_to_img"]:
            return dd_rune_icon(maps["style_id_to_img"][k])
    if s.startswith("perk-images/"):
        return dd_rune_icon(s)
    return None

runes["core_icon"] = runes["rune_core"].apply(to_rune_icon)
runes["sub_icon"] = runes["rune_sub"].apply(to_rune_icon)

st.dataframe(
    runes[["core_icon","sub_icon","total_games","wins","win_rate","pick_rate"]],
    use_container_width=True,
    column_config={
        "core_icon": st.column_config.ImageColumn("핵심 룬", width="small"),
        "sub_icon": st.column_config.ImageColumn("보조 룬", width="small"),
        "total_games": "게임수",
        "wins": "승리",
        "win_rate": "승률(%)",
        "pick_rate": "픽률(%)",
    }
)

# 원본 데이터(필터)
st.subheader('Raw Data (Filtered)')
st.dataframe(df[df['champion']==selected_champion], use_container_width=True)

st.markdown('---')
st.write('앱: 로컬 CSV 기반, 특정 챔피언 선택 시 승률, 픽률, 추천 아이템/스펠/룬 + 아이콘 표시')
