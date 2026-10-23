import streamlit as st
import pandas as pd
from pathlib import Path

# ==================================================
# PAGE SETTINGS
# ==================================================

st.set_page_config(
    page_title="Lz",
    page_icon="",
    layout="wide",
)

st.title("Lz")
st.write("Search, filter, select, and download your entries.")

# ==================================================
# COLUMN NAMES
# ==================================================

# Season flag columns (0/1). Edit the labels here if you like.
SEASON_LABELS = {
    "H": "H",
    "F": "F",
    "S": "S",
    "W": "W",
}
SEASON_FLAGS = list(SEASON_LABELS.keys())

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
    *SEASON_FLAGS,
    style_col,
    shoe_type_col,
    *clothing_cols,
]

# ==================================================
# FIND AND LOAD cloth.csv
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
FILE_PATH = BASE_DIR / "cloth.csv"

st.sidebar.caption("Database: cloth.csv")

if not FILE_PATH.is_file():
    st.error("Cannot find cloth.csv.")
    st.write("Python script:", str(Path(__file__).resolve()))
    st.write("Folder being searched:", str(BASE_DIR))
    st.write("Expected CSV path:", str(FILE_PATH))

    st.write("Files found in this folder:")
    st.write(sorted(p.name for p in BASE_DIR.iterdir()))

    st.warning(
        "Place cloth.csv in the same folder as this Python script. "
        "Check the exact filename and file extension."
    )
    st.stop()


def read_text(path):
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


@st.cache_data
def load_data(path, modified_time):
    from io import StringIO

    text = read_text(path)

    # Detect the delimiter from the header line.
    header = text.splitlines()[0]
    sep = max([";", "\t", ","], key=header.count)

    df = pd.read_csv(StringIO(text), sep=sep, dtype=str)

    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.replace("\xa0", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    df = df.dropna(how="all").reset_index(drop=True)

    # Season columns -> clean 0/1 integers
    for flag in SEASON_FLAGS:
        if flag in df.columns:
            df[flag] = (
                pd.to_numeric(df[flag], errors="coerce")
                .fillna(0)
                .astype(int)
            )

    return df


try:
    data = load_data(
        str(FILE_PATH),
        FILE_PATH.stat().st_mtime,
    )
except Exception as error:
    st.error(f"Could not read cloth.csv: {error}")
    st.stop()

if data.empty:
    st.warning("The CSV contains no entries.")
    st.write("Detected columns:", data.columns.tolist())
    st.stop()

missing = [c for c in required_cols if c not in data.columns]

if missing:
    st.error("Some required columns are missing.")
    st.write("Missing columns:", missing)
    st.write("Actual CSV columns:", data.columns.tolist())
    st.stop()

data = data.copy()

# Readable season text for each entry, e.g. "H, F"
data["season"] = data[SEASON_FLAGS].apply(
    lambda row: ", ".join(
        SEASON_LABELS[flag] for flag in SEASON_FLAGS if row[flag] == 1
    ),
    axis=1,
)

# Stable row IDs for selecting entries.
data["_id"] = data.index.astype(str)

# ==================================================
# SIDEBAR FILTERS
# ==================================================

st.sidebar.header("🔎 Filter")


def get_options(column):
    values = data[column].dropna().astype(str).str.strip()
    return sorted(values[values != ""].unique().tolist())


def reset_filters():
    st.session_state["f_search"] = ""
    st.session_state["f_seasons"] = []
    st.session_state["f_styles"] = []
    st.session_state["f_shoes"] = []


search = st.sidebar.text_input(
    "Search all columns",
    placeholder="e.g. jeans, vans, elegant...",
    key="f_search",
)

seasons = st.sidebar.multiselect(
    "Season",
    options=SEASON_FLAGS,
    format_func=lambda flag: SEASON_LABELS[flag],
    key="f_seasons",
)

styles = st.sidebar.multiselect(
    "Art style",
    options=get_options(style_col),
    key="f_styles",
)

shoe_types = st.sidebar.multiselect(
    "Shoe type",
    options=get_options(shoe_type_col),
    key="f_shoes",
)

st.sidebar.button("Reset filters", on_click=reset_filters)

# ==================================================
# APPLY FILTERS
# ==================================================

filtered = data.copy()

if search.strip():
    searchable = filtered.drop(columns=["_id", "season", *SEASON_FLAGS])
    search_mask = (
        searchable.astype(str)
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

if seasons:
    # Keep entries that are marked for ANY selected season.
    # For "all selected seasons", replace .any with .all
    season_mask = (filtered[seasons] == 1).any(axis=1)
    filtered = filtered[season_mask]

if styles:
    filtered = filtered[filtered[style_col].astype(str).str.strip().isin(styles)]

if shoe_types:
    filtered = filtered[
        filtered[shoe_type_col].astype(str).str.strip().isin(shoe_types)
    ]

# ==================================================
# SELECTION STATE
# ==================================================

if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = set()

st.session_state.selected_ids.intersection_update(set(data["_id"]))

# ==================================================
# SUMMARY
# ==================================================

col1, col2, col3 = st.columns(3)

col1.metric("Total entries", len(data))
col2.metric("Matching entries", len(filtered))
col3.metric("Selected entries", len(st.session_state.selected_ids))

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


def clear_selections():
    for key in list(st.session_state.keys()):
        if key.startswith("select_"):
            del st.session_state[key]
    st.session_state.selected_ids = set()


st.subheader(f"Your entries ({len(filtered)} entries)")

if filtered.empty:
    st.info("No entries match your current filters.")

else:
    for _, item in filtered.iterrows():
        item_id = item["_id"]
        checkbox_key = f"select_{item_id}"

        if checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = (
                item_id in st.session_state.selected_ids
            )

        with st.container(border=True):
            st.subheader(f"Entry {int(item_id) + 1}")

            info1, info2, info3 = st.columns(3)

            info1.markdown("**🌦️ Season**")
            info1.write(item["season"] or "—")

            info2.markdown("**🎨 Art style**")
            info2.write(str(item[style_col]))

            info3.markdown("**👟 Shoe type**")
            info3.write(str(item[shoe_type_col]))

            st.markdown("**Items**")

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

selected = data[
    data["_id"].isin(st.session_state.selected_ids)
].drop(columns=["_id", "season"])

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
        file_name="my_selected_entries.csv",
        mime="text/csv",
    )

    st.button("Clear all selections", on_click=clear_selections)

# ==================================================
# COMPLETE DATABASE
# ==================================================

with st.expander("📋 Show complete database"):
    st.write("Loaded from:", str(FILE_PATH))

    st.dataframe(
        data.drop(columns=["_id", "season"]),
        use_container_width=True,
        hide_index=True,
    )
