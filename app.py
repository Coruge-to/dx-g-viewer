from pathlib import Path
from urllib.parse import quote, urlencode

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import html

BACKUP_DIR = Path(r"C:\Users\tsuru\Documents\Program\DAM\backup")

VIBRATO_TYPE_MAP = {
    0: "N", 1: "A-1", 2: "B-1", 3: "C-1", 4: "A-2", 5: "B-2", 6: "C-2",
    7: "A-3", 8: "B-3", 9: "C-3", 10: "D", 11: "E", 12: "F", 13: "G", 14: "H",
}

BONUS_SHORT_MAP = {
    "音程ボーナス": "音",
    "ビブラートボーナス": "ビ",
    "表現力ボーナス": "表",
}

# --- ヘッダーの構造定義 ---
HEADER_CONFIG = [
    {"align": "right",  "items": [("play_dt", "日付"), ("song_name", "曲名"), ("artist_name", "歌手名")]},
    {"align": "center", "items": [("total_score", "点数")]},
    {"align": "right",  "items": [("base_score", "素点"), ("bonus_score", "ボ点"), ("bonus_type_short", "ボタ")]},
    {"align": "right",  "items": [("chart_total", "チ計"), ("vibrato_longtone", "VL"), ("rhythm", "リ")]},
    {"align": "right",  "items": [("pitch", "音"), ("stability", "安"), ("expressive", "表")]},
    {"align": "right",  "items": [("emphasis", "抑"), ("kobushi_count", "こ"), ("longtone_skill", "ロ")]},
    {"align": "right",  "items": [("shakuri_count", "し"), ("fall_count", "フ"), ("vibrato_skill", "ビ")]},
    {"align": "right",  "items": [("vibrato_seconds", "ビ秒"), ("vibrato_count", "ビ回"), ("vibrato_type_code", "ビタ")]},
]

def get_latest_csv():
    files = sorted(BACKUP_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    return files[0]

def read_csv_safely(path):
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp932")

def pick_col(df, candidates, default=None):
    for c in candidates:
        if c in df.columns:
            return c
    return default

def get_query_param(name):
    try:
        value = st.query_params.get(name, "")
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name, [""])[0]

    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""

def normalize(df):
    out = pd.DataFrame(index=df.index)
    col = {
        "datetime": pick_col(df, ["演奏日時", "歌唱日時", "日時"]),
        "song": pick_col(df, ["曲名", "songName"]),
        "artist": pick_col(df, ["アーティスト", "歌手名", "artistName"]),
        "total": pick_col(df, ["総合点", "totalScore"]),
        "pitch": pick_col(df, ["音程", "radarChartPitch"]),
        "stability": pick_col(df, ["安定性", "radarChartStability"]),
        "expressive": pick_col(df, ["表現力", "radarChartExpressive"]),
        "rhythm": pick_col(df, ["リズム", "radarChartRhythm"]),
        "vl": pick_col(df, ["ビブラート/ロングトーン", "ビブラート／ロングトーン", "radarChartVibratoLongtone"]),
        "vib_count": pick_col(df, ["ビブラート回数", "vibratoCount"]),
        "vib_skill": pick_col(df, ["ビブラート上手さ", "vibratoSkill"]),
        "vib_sec": pick_col(df, ["ビブラート秒数", "vibratoTotalSecond"]),
        "vib_type": pick_col(df, ["ビブラートタイプ", "vibratoType"]),
        "kobushi": pick_col(df, ["こぶし", "kobushiCount"]),
        "shakuri": pick_col(df, ["しゃくり", "shakuriCount"]),
        "fall": pick_col(df, ["フォール", "fallCount"]),
        "emphasis": pick_col(df, ["抑揚", "emphasis"]),
        "bonus_type": pick_col(df, ["ボーナスタイプ", "bonusTypeName"]),
        "bonus_point": pick_col(df, ["ボーナスポイント", "bonusPoint"]),
        "longtone": pick_col(df, ["ロングトーンスキル", "longtoneSkill"]),
        "timing": pick_col(df, ["リズムタイミング", "timing"]),
    }

    if col["datetime"]:
        out["play_datetime"] = df[col["datetime"]].astype(str)
        out["play_dt"] = pd.to_datetime(out["play_datetime"], errors="coerce")
        out["play_date"] = out["play_dt"].dt.strftime("%y/%m/%d")
    else:
        out["play_datetime"] = ""
        out["play_dt"] = pd.NaT
        out["play_date"] = ""

    out["song_name"] = df[col["song"]].astype(str) if col["song"] else ""
    out["artist_name"] = df[col["artist"]].astype(str) if col["artist"] else ""

    numeric_fields = {
        "total_score": "total", "pitch": "pitch", "stability": "stability",
        "expressive": "expressive", "rhythm": "rhythm", "vibrato_longtone": "vl",
        "vibrato_count": "vib_count", "vibrato_skill": "vib_skill", "vibrato_seconds": "vib_sec",
        "vibrato_type_code": "vib_type", "kobushi_count": "kobushi", "shakuri_count": "shakuri",
        "fall_count": "fall", "emphasis": "emphasis", "bonus_score": "bonus_point",
        "longtone_skill": "longtone", "rhythm_timing": "timing",
    }

    for out_name, key in numeric_fields.items():
        source_col = col[key]
        if source_col:
            out[out_name] = pd.to_numeric(df[source_col], errors="coerce")
        else:
            out[out_name] = pd.NA

    out["base_score"] = out["total_score"] - out["bonus_score"]
    out["chart_total"] = out["pitch"] + out["stability"] + out["expressive"] + out["rhythm"] + out["vibrato_longtone"]
    out["bonus_type"] = df[col["bonus_type"]].astype(str) if col["bonus_type"] else ""
    out["bonus_type_short"] = out["bonus_type"].map(BONUS_SHORT_MAP).fillna(out["bonus_type"])
    out["vibrato_type_label"] = out["vibrato_type_code"].astype("Int64").map(VIBRATO_TYPE_MAP).fillna("")

    return out

def score_color(score, bonus_score=None):
    if pd.isna(score): return "#FFFFFF"
    score = float(score)
    bonus = float(bonus_score) if bonus_score is not None and not pd.isna(bonus_score) else None

    if score >= 100 and bonus is not None and abs(bonus) < 0.0005:
        return "linear-gradient(135deg, #fff8ba 0%, #ffe66d 24%, #ffd034 48%, #c99700 72%, #fff0a0 100%)"
    if score >= 100: return "#FFF650"
    if score >= 99:  return "#FFFFAC"
    if score >= 98:  return "#CCFFCD"
    if score >= 95:  return "#A9FFFE"
    if score >= 90:  return "#CFCEFF"
    if score >= 85:  return "#FCBCFA"
    if score >= 80:  return "#FDCCDC"
    return "#FFFFFF"

def fmt(value, digits=None):
    if pd.isna(value): return ""
    if digits is not None: return f"{float(value):.{digits}f}"
    try:
        f = float(value)
        return str(int(f)) if f.is_integer() else str(f)
    except:
        return str(value)

def esc(value):
    return html.escape("" if pd.isna(value) else str(value))

# 引数に current_song と current_artist を追加
def make_sort_href(col_key, current_sort_col, current_sort_dir, current_date, current_song, current_artist):
    next_dir = "desc"
    if col_key == current_sort_col:
        next_dir = "asc" if current_sort_dir == "desc" else "desc"
    
    params = {"sort_col": col_key, "sort_dir": next_dir}
    
    # 現在のフィルタ状態を維持する
    if current_date:
        params["date"] = current_date
    if current_song:
        params["song"] = current_song
    if current_artist:
        params["artist"] = current_artist
        
    return "?" + urlencode(params)

def render_dxg_table(df, current_sort_col, current_sort_dir, current_date, current_song, current_artist):
    rows_html = []

    headers_html = ['<th class="no-col">No.</th>']
    for col_data in HEADER_CONFIG:
        align = col_data["align"]
        items = col_data["items"]
        
        th_class = f"col-header {align}-align"
        links_html = []
        
        for col_key, label in items:
            href = make_sort_href(col_key, current_sort_col, current_sort_dir, current_date, current_song, current_artist)
            
            active_class = ""
            if col_key == current_sort_col:
                active_class = " active-desc" if current_sort_dir == "desc" else " active-asc"
            
            links_html.append(f'<a href="{href}" target="_self" class="sort-link{active_class}">{label}</a>')
        
        content = f'<div class="header-container">{"".join(links_html)}</div>'
        headers_html.append(f'<th class="{th_class}">{content}</th>')

    header_row = "\n".join(headers_html)

    header = f"""
    <table class="dxg-table">
      <colgroup>
        <col style="width: 46px;">
        <col style="width: 230px;">
        <col style="width: 78px;">
        <col style="width: 64px;">
        <col style="width: 54px;">
        <col style="width: 44px;">
        <col style="width: 44px;">
        <col style="width: 44px;">
        <col style="width: 54px;">
      </colgroup>
      <thead>
        <tr>
          {header_row}
        </tr>
      </thead>
      <tbody>
    """
    rows_html.append(header)

    for i, r in df.reset_index(drop=True).iterrows():
        no = i + 1
        bg = score_color(r["total_score"], r["bonus_score"])
        play_date = "" if pd.isna(r["play_date"]) else str(r["play_date"])
        
        # 楽曲・アーティスト名の取得
        song_val = str(r["song_name"]) if not pd.isna(r["song_name"]) else ""
        artist_val = str(r["artist_name"]) if not pd.isna(r["artist_name"]) else ""
        
        # 日付リンク用（曲フィルタはリセットして日付だけにする）
        date_params = {"date": play_date, "sort_col": current_sort_col, "sort_dir": current_sort_dir}
        date_href = f"?{urlencode(date_params)}" if play_date else "#"

        # 楽曲リンク用（日付フィルタはリセットして特定の曲の全履歴を出す）
        song_params = {"song": song_val, "artist": artist_val, "sort_col": current_sort_col, "sort_dir": current_sort_dir}
        song_href = f"?{urlencode(song_params)}" if song_val else "#"

        rows_html.append(f"""
        <tr class="record-top">
          <td>{no}</td>
          <td class="meta-cell">
            <a href="{date_href}" target="_self" class="date-text">{esc(play_date)}</a>
          </td>
          <td rowspan="3" class="score-cell" style="background:{bg};">{fmt(r["total_score"], 3)}</td>
          <td>{fmt(r["base_score"], 3)}</td>
          <td>{fmt(r["chart_total"])}</td>
          <td>{fmt(r["pitch"])}</td>
          <td>{fmt(r["emphasis"])}</td>
          <td>{fmt(r["shakuri_count"])}</td>
          <td>{fmt(r["vibrato_seconds"], 1)}</td>
        </tr>
        <tr>
          <td></td>
          <td class="meta-cell">
            <a href="{song_href}" target="_self" class="clip song">{esc(song_val)}</a>
          </td>
          <td>{fmt(r["bonus_score"], 3)}</td>
          <td>{fmt(r["vibrato_longtone"])}</td>
          <td>{fmt(r["stability"])}</td>
          <td>{fmt(r["kobushi_count"])}</td>
          <td>{fmt(r["fall_count"])}</td>
          <td>{fmt(r["vibrato_count"])}</td> 
        </tr>
        <tr class="record-bottom">
          <td></td>
          <td class="meta-cell">
            <div class="clip artist">{esc(artist_val)}</div>
          </td>
          <td>{esc(r["bonus_type_short"])}</td>
          <td>{fmt(r["rhythm"])}</td>
          <td>{fmt(r["expressive"])}</td>
          <td>{fmt(r["longtone_skill"])}</td>
          <td>{fmt(r["vibrato_skill"])}</td> 
          <td>{esc(r["vibrato_type_label"])}</td>
        </tr>
        """)

    rows_html.append("</tbody></table>")
    return "\n".join(rows_html)

st.set_page_config(page_title="DX-G Viewer", layout="wide")

DXG_CSS = """
<style>
.dxg-table {
  border-collapse: collapse;
  table-layout: fixed;
  width: auto;
  font-family: Arial, "Yu Gothic", sans-serif;
  font-size: 14px;
}

.dxg-table th,
.dxg-table td {
  border: 1px solid #bdbdbd;
  padding: 5px 7px;
  text-align: right;
  vertical-align: middle;
  white-space: nowrap;
  overflow: hidden;
}

.dxg-table th {
  background: #f8f8f8;
  font-weight: bold;
  color: #222;
  padding: 0;
  height: 1px;
}

.dxg-table th.no-col {
  padding: 5px 7px;
  vertical-align: middle;
}

.header-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sort-link {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 2px 7px;
  color: #222 !important; 
  text-decoration: none !important; 
  box-sizing: border-box;
  line-height: 1.3;
  border-radius: 0 !important; 
}

.right-align .sort-link {
  justify-content: flex-end;
}

.center-align .sort-link {
  justify-content: center;
  font-size: 16px;
}

.sort-link:hover {
  background: rgba(0,0,0,0.05);
}

.sort-link.active-desc {
  background: #b00000 !important;
  color: white !important;
}
.sort-link.active-asc {
  background: #0044b0 !important;
  color: white !important;
}

.dxg-table .score-cell {
  font-size: 20px;
  text-align: center;
  font-weight: 500;
  color: #222;
  box-shadow: inset 0 0 8px rgba(255,255,255,0.45);
}

.dxg-table .meta-cell {
  text-align: left;
  max-width: 230px;
  overflow: hidden;
}

.dxg-table .clip {
  display: block;
  width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.dxg-table .date-text {
  text-align: right;
  color: #1666aa;
  text-decoration: underline;
}

.dxg-table .date-text:visited {
  color: #1666aa;
}

/* 曲名リンクの装飾設定 */
.dxg-table a.song {
  color: #1670a8;
  text-align: left;
  text-decoration: underline;
}

.dxg-table .artist {
  color: #333;
  text-align: left;
  text-decoration: none;
}

.dxg-table .record-top td {
  border-top: 3px solid #666;
}

.dxg-table .record-bottom td {
  border-bottom: 3px solid #666;
}

.wrapper {
  max-height: 900px;
  overflow-y: auto;
  overflow-x: auto;
  padding-bottom: 20px;
}

.clear-filter-btn {
  display: inline-block;
  padding: 6px 12px;
  margin-bottom: 15px;
  background-color: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 4px;
  color: #333;
  text-decoration: none;
  font-weight: bold;
}
.clear-filter-btn:hover {
  background-color: #e2e6ea;
}
</style>
"""

st.title("精密集計DX-G 風ビューア")

csv_path = get_latest_csv()

if csv_path is None:
    st.error(f"CSVが見つかりません: {BACKUP_DIR}")
    st.stop()

st.caption(f"読み込みCSV: {csv_path}")

raw = read_csv_safely(csv_path)
df = normalize(raw)

# URLパラメータの取得に追加
selected_date = get_query_param("date")
selected_song = get_query_param("song")
selected_artist = get_query_param("artist")

sort_col = get_query_param("sort_col") or "total_score"
sort_dir = get_query_param("sort_dir") or "desc"

# 適用中のフィルタの表示処理
active_filters = []
if selected_date:
    active_filters.append(f"日付: {selected_date}")
if selected_song and selected_artist:
    active_filters.append(f"楽曲: {selected_song} ({selected_artist})")

if active_filters:
    st.info(f"フィルタ適用中: {' ｜ '.join(active_filters)}")
    st.markdown('<a href="?" target="_self" class="clear-filter-btn">❌ フィルタを解除して全件表示に戻る</a>', unsafe_allow_html=True)

keyword = st.text_input("曲名・歌手名検索", "")

view = df.copy()

# フィルタ実行
if selected_date:
    view = view[view["play_date"] == selected_date]

if selected_song and selected_artist:
    view = view[(view["song_name"] == selected_song) & (view["artist_name"] == selected_artist)]

if keyword:
    mask = (
        view["song_name"].astype(str).str.contains(keyword, case=False, na=False)
        | view["artist_name"].astype(str).str.contains(keyword, case=False, na=False)
    )
    view = view[mask]

# --- ここで並び替えの対応関係を制御 ---
if sort_col in view.columns:
    if sort_col in ["song_name", "artist_name", "vibrato_type_code"]:
        is_ascending = (sort_dir == "desc")
    else:
        is_ascending = (sort_dir == "asc")

    view = view.sort_values(sort_col, ascending=is_ascending)

st.write(f"表示件数: {len(view)} 件")

# render_dxg_table に current_song と current_artist も渡す
html_string = DXG_CSS + '<div class="wrapper">' + render_dxg_table(view, sort_col, sort_dir, selected_date, selected_song, selected_artist) + "</div>"

clean_html = "\n".join([line.strip() for line in html_string.split("\n")])

st.markdown(clean_html, unsafe_allow_html=True)