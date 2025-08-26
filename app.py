# app.py (최종본)
import streamlit as st
import pandas as pd
import requests
from typing import Dict, Any, Optional

st.set_page_config(page_title="ARAM PS Dashboard", layout="wide")
CSV_PATH = "./aram_participants_clean_preprocessed.csv"

# ---------------- 안전한 요청/버전 ----------------
def fetch_json(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "streamlit-ddragon/1.0"})
        r.raise_for_status()
        return r.json()
    except Exception:
        return None  # JSONDecodeError/HTTP 오류 대비

@st.cache_data(show_spinner=False)
def get_dd_version() -> str:
    data = fetch_json("https://ddragon.leagueoflegends.com/api/versions.json")
    if isinstance(data, list) and data:
        return data  # 최신 버전
    return "14.10.1"   # 폴백 버전

# ---------------- Data Dragon 매핑 로드 ----------------
@st.cache_data(show_spinner=False)
def load_dd_maps(version: str, lang_order: list[str] = ["ko_KR","en_US"]) -> Dict[str, Any]:
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
        # 최후 폴백
        fallback_version = "14.10.1"
        base = f"https://ddragon.leagueoflegends.com/cdn/{fallback_version}/data/en_US"
        champions = fetch_json(f"{base}/champion.json")["data"]
        items = fetch_json(f"{base}/item.json")["data"]
        spells = fetch_json(f"{base}/summoner.json")["data"]
        used_lang = "en_US"

    # 룬: 고정 경로(버전 세그먼트 없음)
    runes = fetch_json("https://ddragon.leagueoflegends.com/cdn/data/en_US/runesReforged.json") or []

    # 매핑 사전
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

# ---------------- 아이콘 URL/검증 ----------------
def _is_http(s: str) -> bool:
    return isinstance(s, str) and s.startswith("http")

def _safe(url: str | None) -> str:
    return url if _is_http(url or "") else ""  # ImageColumn은 빈 문자열이면 미표시

def dd_champion_icon(version: str, champ_name: str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_name}.png"

def dd_item_icon(version: str, item_id: int | str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png"

def dd_spell_icon(version: str, spell_file: str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{spell_file}.png"

def dd_rune_icon(perk_path: str) -> str:
    return f"https://ddragon.leagueoflegends.com/cdn/img/{perk_path}"

def champ_canonical(name_or_key: str, maps: Dict[str,Any]) -> str:
    s = str(name_or_key).strip()
    if s.isdigit() and s in maps["champ_key_to_name"]:
        return maps["champ_key_to_name"][s]
    return s

# ---------------- 데이터 로드/집계 ----------------
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

# ---------------- 앱 UI ----------------
with st.spinner("데이터 불러오는 중..."):
    df = load_data(CSV_PATH)

version = get_dd_version()
maps = load_dd_maps(version, lang_order=["ko_KR","en_US"])

# 사이드바: 캐시 초기화 및 챔피언 선택
with st.sidebar:
    st.title('ARAM PS Controls')
    champion_list = sorted(df['champion'].dropna().unique().tolist())
    selected_champion = st.selectbox('챔피언 선택', champion_list)
    if st.button("아이콘 캐시 초기화"):
        st.cache_data.clear()
        st.experimental_rerun()

# 헤더
canon = champ_canonical(selected_champion, maps)
st.title(f"Champion: {canon}")
st.image(_safe(dd_champion_icon(maps['version'], canon)), width=80)

# 요약 메트릭
summary = compute_champion_stats(df, selected_champion)
c1, c2, c3 = st.columns(3)
c1.metric("Games Played", int(summary['total_games'].values))
c2.metric("Win Rate (%)", float(summary['win_rate'].values))
c3.metric("Pick Rate (%)", float(summary['pick_rate'].values))

# ---------------- 아이템 섹션 ----------------
st.subheader('Recommended Items')
items = compute_item_stats(df[df['champion']==selected_champion]).head(20).copy()

def to_item_icon(val) -> str:
    s = str(val).strip()
    if s.isdigit():
        return _safe(dd_item_icon(maps['version'], int(s)))
    return ""

items["icon"] = items["item"].apply(to_item_icon).astype(str)
for c in ["item","total_picks","wins","win_rate","pick_rate"]:
    if c in items.columns:
        items[c] = items[c].astype(str).replace("nan","")

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

# ---------------- 스펠 섹션 ----------------
st.subheader('Recommended Spell Combos')
spells = compute_spell_stats(df[df['champion']==selected_champion]).head(10).copy()

def to_spell_idfile(v) -> str:
    s = str(v).strip()
    if s.isdigit() and s in maps["spell_id_to_file"]:
        return maps["spell_id_to_file"][s]  # 예: SummonerFlash
    return s if s.startswith("Summoner") else f"Summoner{s}"

spells["spell1_icon"] = spells["spell1"].apply(lambda s: _safe(dd_spell_icon(maps['version'], to_spell_idfile(s)))).astype(str)
spells["spell2_icon"] = spells["spell2"].apply(lambda s: _safe(dd_spell_icon(maps['version'], to_spell_idfile(s)))).astype(str)
for c in ["total_games","wins","win_rate","pick_rate"]:
    if c in spells.columns:
        spells[c] = spells[c].astype(str).replace("nan","")

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

# ---------------- 룬 섹션 ----------------
st.subheader('Recommended Rune Combos')
runes = compute_rune_stats(df[df['champion']==selected_champion]).head(10).copy()

def to_rune_url(v) -> str:
    s = str(v).strip()
    if s.isdigit():
        k = int(s)
        if k in maps["rune_id_to_img"]:
            return _safe(dd_rune_icon(maps["rune_id_to_img"][k]))
        if k in maps["style_id_to_img"]:
            return _safe(dd_rune_icon(maps["style_id_to_img"][k]))
        return ""
    if s.startswith("perk-images/"):
        return _safe(dd_rune_icon(s))
    return ""

runes["core_icon"] = runes["rune_core"].apply(to_rune_url).astype(str)
runes["sub_icon"] = runes["rune_sub"].apply(to_rune_url).astype(str)
for c in ["total_games","wins","win_rate","pick_rate"]:
    if c in runes.columns:
        runes[c] = runes[c].astype(str).replace("nan","")

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

# ---------------- 원본 데이터 ----------------
st.subheader('Raw Data (Filtered)')
st.dataframe(df[df['champion']==selected_champion], use_container_width=True)

st.markdown('---')
st.write('앱: 로컬 CSV 기반, 특정 챔피언 선택 시 승률·픽률과 추천 아이템/스펠/룬을 아이콘과 함께 표시')
