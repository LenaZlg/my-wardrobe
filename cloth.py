
import streamlit as st
import pandas as pd
from pathlib import Path

# ==================================================
# PAGE SETTINGS
# ==================================================

st.set_page_config(
    page_title="My Wardrobe",
    page_icon=":)",
    layout="wide",
)

st.title(":) za faul za ibrlegn")
st.write("Search, filter, select, and download your clothing entries.")

# ==================================================
# FIND AND LOAD cloth.csv
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
FILE_PATH = BASE_DIR / "cloth.csv"

st.sidebar.caption("Wardrobe database: cloth.csv")

if not FILE_PATH.is_file():
    st.error("Cannot find cloth.csv.")
    st.write("Python script:", str(Path(__file__).resolve()))
    st.write("Folder being searched:", str(BASE_DIR))
    st.write("Expected CSV path:", str(FILE_PATH))

    st.write("Files found in this folder:")
    st.write(sorted(p.name for p in BASE_DIR.iterdir()))

    st.warning(
        "Place cloth.csv in the same folder as cloth.py. "
        "Check the exact filename and file extension."
    )
    st.stop()


@st.cache_data
def load_data(path, modified_time):
    # Your CSV uses semicolons as separators.
    df = pd.read_csv(
        path,
        sep=";",
        encoding="cp1252",
    )

    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    df = df.dropna(how="all").reset_index(drop=True)


    for season in ["H", "F", "S", "W"]:
        df[season] = pd.to_numeric(df[season], errors="coerce").fillna(0).astype(int)

    return df


try:
    clothes = load_data(
        str(FILE_PATH),
        FILE_PATH.stat().st_mtime,
    )
except Exception as error:
    st.error(f"Could not read cloth.csv: {error}")
    st.info(
        "Check that the file is a valid CSV and uses semicolons "
        "between columns. If it uses commas, change sep=';' to sep=','."
    )
    st.stop()

if clothes.empty:
    st.warning("The CSV contains no clothing entries.")
    st.write("Detected columns:", clothes.columns.tolist())
    st.stop()

# ==================================================
# COLUMN NAMES
# ==================================================

season_cols = ["H", "F", "S", "W"]
style_col = "F art style"
shoe_type_col = "F schuach art"

clothing_cols = [
    "schuach",
    "hose",
    "oberteil",
    "jacke",
    "kleid",
]

required_cols = [
    *season_cols,
    style_col,
    shoe_type_col,
    *clothing_cols,
]

missing = [
    column for column in required_cols
    if column not in clothes.columns
]

if missing:
    st.error("Some required columns are missing.")
    st.write("Missing columns:", missing)
    st.write("Actual CSV columns:", clothes.columns.tolist())
    st.stop()

# ==================================================
# SIDEBAR FILTERS
# ==================================================

st.sidebar.header("🔎 Filter wardrobe")


def get_options(column):
    values = clothes[column].dropna().astype(str).str.strip()
    return sorted(values[values != ""].unique().tolist())


search = st.sidebar.text_input(
    "Search all clothing columns",
    placeholder="e.g. jeans, summer, elegant...",
)

selected_seasons = st.sidebar.multiselect(
    "Season",
    options=season_cols,
)

styles = st.sidebar.multiselect(
    "Art style",
    options=get_options(style_col),
)

shoe_types = st.sidebar.multiselect(
    "Shoe type",
    options=get_options(shoe_type_col),
)

if st.sidebar.button("Reset filters"):
    st.session_state.clear()
    st.rerun()

# ==================================================
# APPLY FILTERS
# ==================================================

filtered = clothes.copy()

if search.strip():
    search_mask = (
        filtered.drop(columns=["_id"])
        .astype(str)
        .apply(
            lambda column: column.str.contains(
                search.strip(),
                case=False,
                regex=False,
                na=False,
            )
        )
        .any(axis=1)
    )

    filtered = filtered[search_mask]

if selected_seasons:
    filtered = filtered[
        filtered[selected_seasons].eq(1).any(axis=1)
    ]

if styles:
    filtered = filtered[
        filtered[style_col].astype(str).isin(styles)
    ]

if shoe_types:
    filtered = filtered[
        filtered[shoe_type_col].astype(str).isin(shoe_types)
    ]

# ==================================================
# SELECTION STATE
# ==================================================

if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = set()

# Keep only IDs that still exist in the database.
st.session_state.selected_ids.intersection_update(
    set(clothes["_id"])
)

# ==================================================
# SUMMARY
# ==================================================

col1, col2, col3 = st.columns(3)

col1.metric("Total entries", len(clothes))
col2.metric("Matching entries", len(filtered))
col3.metric(
    "Selected entries",
    len(st.session_state.selected_ids),
)

st.divider()



# ==================================================
# DISPLAY ENTRIES
# ==================================================

def update_selection(item_id):
    key = f"select_{item_id}"

    if st.session_state.get(key, False):
        st.session_state.selected_ids.add(item_id)
    else:
        st.session_state.selected_ids.discard(item_id)


st.subheader(f"👚 Your wardrobe ({len(filtered)} entries)")

if filtered.empty:
    st.info("No entries match your current filters.")

else:
    for _, item in filtered.iterrows():
        item_id = item["_id"]
        checkbox_key = f"select_{item_id}"

        # Initialize the checkbox before displaying it.
        if checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = (
                item_id in st.session_state.selected_ids
            )

        with st.container(border=True):
            st.subheader(f"Entry {int(item_id) + 1}")

            info1, info2, info3 = st.columns(3)

            info1.markdown("**🌦️ Seasons**")
            active_seasons = [
                season for season in season_cols
                if item[season] == 1
            ]
            info1.write(", ".join(active_seasons) if active_seasons else "—")

            info2.markdown("**🎨 Art style**")
            info2.write(str(item[style_col]))

            info3.markdown("**👟 Shoe type**")
            info3.write(str(item[shoe_type_col]))

            st.markdown("**Clothing items**")

            item_columns = st.columns(len(clothing_cols))

            for col, name in zip(item_columns, clothing_cols):
                with col:
                    value = item[name]
                    st.caption(name.title())

                    if pd.isna(value) or str(value).strip() == "":
                        st.write("—")
                    else:
                        st.write(str(value))

            st.checkbox(
                "Select this entry",
                key=checkbox_key,
                on_change=update_selection,
                args=(item_id,),
            )



# ==================================================
# SELECTED ENTRIES
# ==================================================

st.divider()
st.subheader("✅ Selected entries")

selected = clothes[
    clothes["_id"].isin(st.session_state.selected_ids)
].drop(columns=["_id"])

if selected.empty:
    st.info("Select one or more entries above.")

else:
    st.write(f"You selected {len(selected)} entries.")

    st.dataframe(
        selected,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="⬇️ Download selected entries",
        data=selected.to_csv(
            index=False,
            sep=";",
        ).encode("utf-8-sig"),
        file_name="my_selected_clothes.csv",
        mime="text/csv",
    )

    if st.button("Clear all selections"):
        st.session_state.selected_ids = set()
        st.rerun()

# ==================================================a
# COMPLETE DATABASE
# ==================================================

with st.expander("📋 Show complete clothing database"):
    st.write("Loaded from:", str(FILE_PATH))

    st.dataframe(
        clothes.drop(columns=["_id"]),
        use_container_width=True,
        hide_index=True,
    )
