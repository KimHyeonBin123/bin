# app.py (안정화 버전)
import streamlit as st
import pandas as pd
import requests
from typing import Dict, Any, Optional

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")
CSV_PATH = "./aram_participants_clean_preprocessed.csv"

# ---------- 안전한 요청 도우미 ----------
def fetch_json(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "streamlit-ddragon/1.0"})
        r.raise_for_status()
        # 일부 CDN이 text/plain으로 줄 수 있으니 content-type만 믿지 않고 시도
        return r.json()
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def get_dd_version() -> str:
    data = fetch_json("https://ddragon.leagueoflegends.com/api/versions.json")
    if isinstance(data, list) and data:
        return data
    # 폴백: 최근에 많이 쓰인 버전 예시 (최신이 아닐 수 있음) - 최초 실패 시에도 앱이 켜지도록
    return "14.10.1"

@st.cache_data(show_spinner=False)
def load_dd_maps(version: str, lang_order: list[str] = ["ko_KR","en_US"]) -> Dict[str, Any]:
    # 언어 우선순위에 따라 champion/item/summoner를 로드, 실패 시 다음 언어로 폴백
    champions = items = spells = None
    used_lang = None
    for lang in lang_order:
        base = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{lang}"
        champions_try = fetch_json(f"{base}/champion.json")
        items_try = fetch_json(f"{base}/item.json")
        spells_try = fetch_json(f"{base}/summoner.json")
        if champions_try and items_try and spells_try:
            champions = champions_try["data"]
            items = items_try["data"]
            spells = spells_try["data"]
            used_lang = lang
            break
    if champions is None or items is None or spells is None:
        # 언어/버전 모두 실패 시 마지막 안전망: en_US + 고정 버전
        fallback_version = "14.10.1"
        base = f"https://ddragon.leagueoflegends.com/cdn/{fallback_version}/data/en_US"
        champions = fetch_json(f"{base}/champion.json")["data"]
        items = fetch_json(f"{base}/item.json")["data"]
        spells = fetch_json(f"{base}/summoner.json")["data"]
        used_lang = "en_US"

    # 룬은 고정 경로 사용 (버전 세그먼트 없음)
    runes = fetch_json("https://ddragon.leagueoflegends.com/cdn/data/en_US/runesReforged.json") or []
    # 맵 구성
    champ_key_to_name = {v["key"]: k for k, v in champions.items()}
    spell_id_to_file = {v["key"]: v["id"] for v in spells.values()}
    rune_id_to_img, style_id_to_img = {}, {}
    for style in runes:
        style_id_to_img[style["id"]] = style.get("icon")
        for slot in style.get("slots", []):
            for perk in slot.get("runes", []):
                rune_id_to_img[perk["id"]] = perk["icon"]
    return {
        "champions": champions,
        "items": items,
        "spells": spells,
        "champ_key_to_name": champ_key_to_name,
        "spell_id_to_file": spell_id_to_file,
        "rune_id_to_img": rune_id_to_img,
        "style_id_to_img": style_id_to_img,
        "used_lang": used_lang or "en_US",
        "version": version,
    }

# ---------- 아이콘 URL ----------
def dd_champion_icon(version: str, champ_name: str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_name}.png"

def dd_item_icon(version: str, item_id: int | str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png"

def dd_spell_icon(version: str, spell_file: str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{spell_file}.png"

def dd_rune_icon(perk_path: str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/img/{perk_path}"

# ---------- 데이터 로드/집계 ----------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if 'win' in df.columns:
        df['win_clean'] = df['win'].apply(lambda x: 1 if str(x).lower() in ('1','true','t','yes') else 0)
    else:
        df['win_clean'] = 0
    item_cols = [c for c in df.columns if c.startswith('item')]
    for c in item_cols:
        df[c] = df[c].fillna('').astype(str).str.strip()
    return df

@st.cache_data
def compute_champion_stats(df: pd.DataFrame, champion: str) -> pd.DataFrame:
    df_champ = df[df['champion']==champion].copy()
    total_matches = df['matchId'].nunique()
    total_games = len(df_champ)
    win_rate = round(df_champ['win_clean'].mean()*100,2) if total_games else 0.0
    pick_rate = round(total_games/total_matches*100,2) if total_matches else 0.0
    return pd.DataFrame({'champion':[champion],'total_games':[total_games],'win_rate':[win_rate],'pick_rate':[pick_rate]})

@st.cache_data
def compute_item_stats(df: pd.DataFrame) -> pd.DataFrame:
    item_cols = [c for c in df.columns if c.startswith('item')]
    recs = []
    for c in item_cols:
        recs.append(df[['matchId','win_clean',c]].rename(columns={c:'item'}))
    union = pd.concat(recs, ignore_index=True)
    union = union[union['item'].astype(str)!='']
    stats = (union.groupby('item')
             .agg(total_picks=('matchId','count'), wins=('win_clean','sum'))
             .reset_index())
    stats['win_rate'] = (stats['wins']/stats['total_picks']*100).round(2)
    total_matches = df['matchId'].nunique()
    stats['pick_rate'] = (stats['total_picks']/total_matches*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

@st.cache_data
def compute_spell_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby(['spell1','spell2']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

@st.cache_data
def compute_rune_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby(['rune_core','rune_sub']).agg(total_games=('matchId','count'), wins=('win_clean','sum')).reset_index()
    stats['win_rate'] = (stats['wins']/stats['total_games']*100).round(2)
    stats['pick_rate'] = (stats['total_games']/df['matchId'].nunique()*100).round(2)
    return stats.sort_values('win_rate', ascending=False)

# ---------- 앱 ----------
with st.spinner("데이터 불러오는 중..."):
    df = load_data(CSV_PATH)

version = get_dd_version()
maps = load_dd_maps(version, lang_order=["ko_KR","en_US"])

st.sidebar.title('ARAM PS Controls')
champion_list = sorted(df['champion'].dropna().unique().tolist())
selected_champion = st.sidebar.selectbox('챔피언 선택', champion_list)

st.title(f"Champion: {selected_champion}")
st.caption(f"DataDragon version: {maps['version']} | lang: {maps['used_lang']}")

# 챔피언 아이콘 (CSV가 canonical name을 가진다고 가정)
st.image(dd_champion_icon(maps['version'], selected_champion), width=80)

summary = compute_champion_stats(df, selected_champion)
c1, c2, c3 = st.columns(3)
c1.metric("Games Played", int(summary['total_games'].values))
c2.metric("Win Rate (%)", float(summary['win_rate'].values))
c3.metric("Pick Rate (%)", float(summary['pick_rate'].values))

# 아이템
st.subheader('Recommended Items')
items = compute_item_stats(df[df['champion']==selected_champion]).head(20).copy()
def to_item_icon(val: str):
    try:
        return dd_item_icon(maps['version'], int(str(val)))
    except:
        return None
items["icon"] = items["item"].apply(to_item_icon)
st.dataframe(
    items[["icon","item","total_picks","wins","win_rate","pick_rate"]],
    use_container_width=True,
    column_config={"icon": st.column_config.ImageColumn("아이콘", width="small")}
)

# 스펠
st.subheader('Recommended Spell Combos')
spells = compute_spell_stats(df[df['champion']==selected_champion]).head(10).copy()
def to_spell_file(v: str):
    s = str(v)
    if s.isdigit() and s in maps["spell_id_to_file"]:
        return maps["spell_id_to_file"][s]
    return s if s.startswith("Summoner") else f"Summoner{s}"
spells["spell1_icon"] = spells["spell1"].apply(lambda s: dd_spell_icon(maps['version'], to_spell_file(s)))
spells["spell2_icon"] = spells["spell2"].apply(lambda s: dd_spell_icon(maps['version'], to_spell_file(s)))
st.dataframe(
    spells[["spell1_icon","spell2_icon","total_games","wins","win_rate","pick_rate"]],
    use_container_width=True,
    column_config={
        "spell1_icon": st.column_config.ImageColumn("스펠1", width="small"),
        "spell2_icon": st.column_config.ImageColumn("스펠2", width="small"),
    }
)

# 룬
st.subheader('Recommended Rune Combos')
runes = compute_rune_stats(df[df['champion']==selected_champion]).head(10).copy()
def to_rune_icon(val):
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
    }
)

st.subheader('Raw Data (Filtered)')
st.dataframe(df[df['champion']==selected_champion], use_container_width=True)
