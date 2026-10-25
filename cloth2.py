from pathlib import Path
import pandas as pd
import streamlit as st





# ==================================================
# PAGE SETTINGS
# ==================================================

st.set_page_config(
    page_title="clothsloth",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

#st.title("Lz")
#st.write("Search, filter, select, and download your entries.")

# ==================================================
# CUSTOM DESIGN
# ==================================================

st.markdown("""
<style>
/* Main background */
.stApp {
    background-color: #F7F6F2;
    color: #292D28;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #EAEDE5;
    border-right: 1px solid #D8DED2;
}

/* Main content spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Entry cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF;
    border: 1px solid #E5E7E0;
    border-radius: 16px;
    padding: 8px;
    box-shadow: 0 2px 8px rgba(40, 50, 40, 0.04);
    transition: border-color 0.2s, box-shadow 0.2s;
}

/* Hover effect */
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #A4B59B;
    box-shadow: 0 5px 16px rgba(40, 50, 40, 0.09);
}

/* Headings */
h1, h2, h3 {
    color: #354638 !important;
    letter-spacing: -0.5px;
}

/* Small text */
[data-testid="stCaptionContainer"] {
    color: #788174;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button {
    background-color: #526B52;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    transition: background-color 0.2s;
}

/* Button hover */
.stButton > button:hover,
.stDownloadButton > button:hover {
    background-color: #3D543E;
    color: white;
    border: none;
}

/* Expandable details */
[data-testid="stExpander"] {
    background-color: #F4F6F0;
    border: 1px solid #E0E5DA;
    border-radius: 10px;
}

/* Text input fields */
[data-testid="stTextInput"] input {
    border-radius: 10px;
}

/* Multiselect fields */
[data-testid="stMultiSelect"] [data-baseweb="select"] {
    border-radius: 10px;
}

/* Checkboxes */
[data-testid="stCheckbox"] {
    padding-top: 4px;
}

</style>
""", unsafe_allow_html=True)

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
          pd.to_numeric(df[flag], errors="coerce").fillna(0).astype(int)
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
# SIDEBAR FILTERS & SETTINGS
# ==================================================

st.sidebar.header("🔎 Filter & Ansicht")


def get_options(column):
  values = data[column].dropna().astype(str).str.strip()
  return sorted(values[values != ""].unique().tolist())


def reset_filters():
  st.session_state["f_search"] = ""
  st.session_state["f_seasons"] = []
  st.session_state["f_styles"] = []
  st.session_state["f_shoes"] = []


# Layout-Einstellung direkt in der Sidebar
cards_per_row = st.sidebar.slider(
    "Karten pro Reihe", min_value=1, max_value=6, value=3
)

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

#col1, col2, col3 = st.columns(3)

#col1.metric("Total entries", len(data))
#col2.metric("Matching entries", len(filtered))
#col3.metric("Selected entries", len(st.session_state.selected_ids))

#st.divider()


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


if filtered.empty:
    st.info("No entries match your current filters.")

else:
    rows = [
        filtered.iloc[i : i + cards_per_row]
        for i in range(0, len(filtered), cards_per_row)
    ]

    for row_items in rows:
        columns = st.columns(cards_per_row, gap="small")

        for column, (_, item) in zip(columns, row_items.iterrows()):
            item_id = item["_id"]
            checkbox_key = f"select_{item_id}"

            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = (
                    item_id in st.session_state.selected_ids
                )

            with column:
                with st.container(border=True, gap="small"):
                    st.markdown(f"**#{int(item_id) + 1}**")

                    st.caption(
                        f"{item['season'] or '—'} · "
                        f"{item[style_col] or '—'} · "
                        f"{item[shoe_type_col] or '—'}"
                    )

                    with st.expander("Details"):
                        for name in clothing_cols:
                            value = item[name]

                            if pd.isna(value) or not str(value).strip():
                                continue

                            st.markdown(
                                f"**{name.title()}:** {value}"
                            )

                    st.checkbox(
                        "Select",
                        key=checkbox_key,
                        on_change=update_selection,
                        args=(item_id,),
                    )



# ==================================================
# SELECTED ENTRIES
# ==================================================

#st.divider()
#st.subheader("✅ Selected entries")

selected = data[data["_id"].isin(st.session_state.selected_ids)].drop(
    columns=["_id", "season"]
)

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
