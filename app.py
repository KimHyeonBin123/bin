# --- Helper: 아이콘 URL 생성 ---
def get_icon_url(name, img_dict, category="item"):
    img_file = img_dict.get(name)
    if not img_file:
        return None
    if category == "item":
        return f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/item/{img_file}"
    elif category == "spell":
        return f"http://ddragon.leagueoflegends.com/cdn/13.17.1/img/spell/{img_file}"
    elif category == "rune":
        return f"http://ddragon.leagueoflegends.com/cdn/img/{img_file}"
    return None

# --- Recommended Items ---
st.subheader('Recommended Items')
items = compute_item_stats(champ_df)
items['item_icon'] = items['item'].apply(lambda x: get_icon_url(x, item_name_to_img, "item"))

gb = GridOptionsBuilder.from_dataframe(items)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
gb.configure_column(
    "item_icon",
    header_name="Item",
    cellRenderer="""
    function(params) {
        if (params.value) {
            return `<img src="${params.value}" style="width:20px;height:20px;vertical-align:middle;margin-right:4px;">`;
        }
        return '';
    }
    """,
    width=100
)
gridOptions = gb.build()
AgGrid(items, gridOptions=gridOptions, enable_enterprise_modules=False, fit_columns_on_grid_load=True)

# --- Recommended Spells ---
st.subheader('Recommended Spell Combos')
spells = compute_spell_stats(champ_df)
spells['spell1_icon'] = spells['spell1'].apply(lambda x: get_icon_url(x, spell_name_to_img, "spell"))
spells['spell2_icon'] = spells['spell2'].apply(lambda x: get_icon_url(x, spell_name_to_img, "spell"))

gb = GridOptionsBuilder.from_dataframe(spells)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
for col in ["spell1_icon","spell2_icon"]:
    gb.configure_column(
        col,
        cellRenderer="""
        function(params) {
            if (params.value) {
                return `<img src="${params.value}" style="width:20px;height:20px;vertical-align:middle;margin-right:4px;">`;
            }
            return '';
        }
        """,
        width=100
    )
gridOptions = gb.build()
AgGrid(spells, gridOptions=gridOptions, enable_enterprise_modules=False, fit_columns_on_grid_load=True)

# --- Recommended Runes ---
st.subheader('Recommended Rune Combos')
runes = compute_rune_stats(champ_df)
runes['rune_core_icon'] = runes['rune_core'].apply(lambda x: get_icon_url(x, rune_name_to_img, "rune"))
runes['rune_sub_icon'] = runes['rune_sub'].apply(lambda x: get_icon_url(x, rune_name_to_img, "rune"))

gb = GridOptionsBuilder.from_dataframe(runes)
gb.configure_default_column(filterable=True, sortable=True, resizable=True)
for col in ["rune_core_icon","rune_sub_icon"]:
    gb.configure_column(
        col,
        cellRenderer="""
        function(params) {
            if (params.value) {
                return `<img src="${params.value}" style="width:20px;height:20px;vertical-align:middle;margin-right:4px;">`;
            }
            return '';
        }
        """,
        width=100
    )
gridOptions = gb.build()
AgGrid(runes, gridOptions=gridOptions, enable_enterprise_modules=False, fit_columns_on_grid_load=True)
