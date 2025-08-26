# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

# 샘플 데이터 (URL은 실제 아이콘 이미지 주소로 교체하세요)
data = {
    "champion": ["Ahri", "Yasuo", "Lux"],
    "spell1": [
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerFlash.png",
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerHeal.png",
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerDot.png"
    ],
    "spell2": [
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerHeal.png",
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerFlash.png",
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerBarrier.png"
    ],
    "item1": [
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/6655.png",
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/3031.png",
        "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/3285.png"
    ],
}

df = pd.DataFrame(data)

st.title("칼바람 챔피언 추천 빌드")
st.subheader("Recommended Items & Spells")

# Grid 설정
gb = GridOptionsBuilder.from_dataframe(df)

# 챔피언 이름은 텍스트 그대로
gb.configure_column("champion", header_name="Champion")

# 스펠/아이템은 이미지로 렌더링
for col in ["spell1", "spell2", "item1"]:
    gb.configure_column(
        col,
        header_name=col.capitalize(),
        cellRenderer='''
        function(params) {
            if (params.value) {
                return `<img src="${params.value}" width="30" height="30"/>`
            }
            return "";
        }
        '''
    )

grid_options = gb.build()

# AgGrid 출력
AgGrid(
    df,
    gridOptions=grid_options,
    allow_unsafe_jscode=True,  # JS 코드 허용해야 이미지 렌더링됨
    height=300,
    fit_columns_on_grid_load=True,
)
