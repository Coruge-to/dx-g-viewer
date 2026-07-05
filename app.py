from pathlib import Path
from urllib.parse import quote, urlencode

import pandas as pd
import streamlit as st
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

# --- スマホ用（SP）ヘッダー構造 ---
HEADER_CONFIG_SP = [
    {"align": "right",  "items": [("play_dt", "日付"), ("song_name", "曲名"), ("artist_name", "歌手名")]},
    {"align": "center", "items": [("total_score", "点数")]},
    {"align": "right",  "items": [("base_score", "素点"), ("bonus_score", "ボ点"), ("bonus_type_short", "ボタ")]},
    {"align": "right",  "items": [("chart_total", "チ計"), ("vibrato_longtone", "VL"), ("rhythm", "リ")]},
    {"align": "right",  "items": [("pitch", "音"), ("stability", "安"), ("expressive", "表")]},
    {"align": "right",  "items": [("emphasis", "抑"), ("kobushi_count", "こ"), ("longtone_skill", "ロ")]},
    {"align": "right",  "items": [("shakuri_count", "し"), ("fall_count", "フ"), ("vibrato_skill", "ビ")]},
    {"align": "right",  "items": [("vibrato_seconds", "ビ秒"), ("vibrato_count", "ビ回"), ("vibrato_type_code", "ビタ")]},
]

# --- PC用ヘッダー構造（一列表示） ---
HEADER_CONFIG_PC = [
    ("play_dt", "日付"), ("song_name", "曲名 / 歌手名"), ("total_score", "点数"),
    ("base_score", "素点"), ("bonus_score", "ボ点"), ("bonus_type_short", "ボタ"),
    ("chart_total", "チ計"), ("pitch", "音"), ("stability", "安"), ("expressive", "表"),
    ("rhythm", "リ"), ("vibrato_longtone", "VL"), ("emphasis", "抑"),
    ("shakuri_count", "し"), ("kobushi_count", "こ"), ("fall_count", "フ"),
    ("longtone_skill", "ロ"), ("vibrato_skill", "ビ"), ("vibrato_seconds", "ビ秒"),
    ("vibrato_count", "ビ回"), ("vibrato_type_code", "ビタ")
]

def get_latest_csv():
    files = sorted(BACKUP_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files: return None
    return files[0]

def read_csv_safely(path):
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp932")

def pick_col(df, candidates, default=None):
    for c in candidates:
        if c in df.columns: return c
    return default

def get_query_param(name):
    try:
        value = st.query_params.get(name, "")
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name, [""])[0]
    if isinstance(value, list): return value[0] if value else ""
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
        if source_col: out[out_name] = pd.to_numeric(df[source_col], errors="coerce")
        else: out[out_name] = pd.NA

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

def make_sort_href(col_key, current_sort_col, current_sort_dir, current_date, current_song, current_artist, current_mode, current_search):
    next_dir = "desc"
    if col_key == current_sort_col:
        next_dir = "asc" if current_sort_dir == "desc" else "desc"
    
    params = {"sort_col": col_key, "sort_dir": next_dir, "mode": current_mode}
    if current_date: params["date"] = current_date
    if current_song: params["song"] = current_song
    if current_artist: params["artist"] = current_artist
    if current_search: params["search"] = current_search
    return "?" + urlencode(params)

# --- 検索バー iframe 生成（JavaScriptによる親画面URL更新機能付き） ---
def get_search_iframe_srcdoc(keyword):
    srcdoc = f"""
    <!DOCTYPE html>
    <html><head><style>
      body {{ margin: 0; padding: 0; background: transparent; font-family: sans-serif; }}
      form {{ margin: 0; display: flex; }}
      input {{
        width: 100%; height: 32px; padding: 6px 12px; border: 1px solid #ccc;
        border-radius: 4px; color: #333; font-size: 14px; outline: none; box-sizing: border-box;
      }}
      input:focus {{ border-color: #1666aa; box-shadow: 0 0 4px rgba(22,102,170,0.3); }}
      input::placeholder {{ color: #aaa; }}
    </style>
    <script>
      function submitSearch(e, form) {{
        e.preventDefault();
        var val = form.search.value;
        var topUrl = new URL(window.top.location.href);
        if (val) {{
          topUrl.searchParams.set('search', val);
        }} else {{
          topUrl.searchParams.delete('search');
        }}
        window.top.location.href = topUrl.toString();
      }}
    </script>
    </head>
    <body>
      <form onsubmit='submitSearch(event, this)'>
        <input type='text' name='search' value='{html.escape(keyword)}' placeholder='🔍 曲名 or 歌手名'>
      </form>
    </body></html>
    """
    return html.escape(srcdoc)

def render_sp_table(df, sort_col, sort_dir, date, song, artist, mode, search):
    rows_html = []
    headers_html = ['<th class="no-col">No.</th>']
    for col_data in HEADER_CONFIG_SP:
        align = col_data["align"]
        items = col_data["items"]
        links_html = []
        for col_key, label in items:
            href = make_sort_href(col_key, sort_col, sort_dir, date, song, artist, mode, search)
            active_class = (" active-desc" if sort_dir == "desc" else " active-asc") if col_key == sort_col else ""
            links_html.append(f'<a href="{href}" target="_self" class="sort-link{active_class}">{label}</a>')
        headers_html.append(f'<th class="col-header {align}-align"><div class="header-container">{"".join(links_html)}</div></th>')

    rows_html.append(f'<table class="dxg-table sp-table"><thead><tr>{"".join(headers_html)}</tr></thead><tbody>')

    for i, r in df.reset_index(drop=True).iterrows():
        bg = score_color(r["total_score"], r["bonus_score"])
        d_val = "" if pd.isna(r["play_date"]) else str(r["play_date"])
        s_val = str(r["song_name"]) if not pd.isna(r["song_name"]) else ""
        a_val = str(r["artist_name"]) if not pd.isna(r["artist_name"]) else ""
        
        date_href = f"?{urlencode({'date': d_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': mode, 'search': search})}" if d_val else "#"
        song_href = f"?{urlencode({'song': s_val, 'artist': a_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': mode, 'search': search})}" if s_val else "#"

        rows_html.append(f"""
        <tr class="record-top">
          <td>{i+1}</td>
          <td class="meta-cell"><a href="{date_href}" target="_self" class="date-text">{esc(d_val)}</a></td>
          <td rowspan="3" class="score-cell" style="background:{bg};">{fmt(r["total_score"], 3)}</td>
          <td>{fmt(r["base_score"], 3)}</td><td>{fmt(r["chart_total"])}</td><td>{fmt(r["pitch"])}</td><td>{fmt(r["emphasis"])}</td><td>{fmt(r["shakuri_count"])}</td><td>{fmt(r["vibrato_seconds"], 1)}</td>
        </tr>
        <tr>
          <td></td><td class="meta-cell"><a href="{song_href}" target="_self" class="clip song">{esc(s_val)}</a></td>
          <td>{fmt(r["bonus_score"], 3)}</td><td>{fmt(r["vibrato_longtone"])}</td><td>{fmt(r["stability"])}</td><td>{fmt(r["kobushi_count"])}</td><td>{fmt(r["fall_count"])}</td><td>{fmt(r["vibrato_count"])}</td> 
        </tr>
        <tr class="record-bottom">
          <td></td><td class="meta-cell"><div class="clip artist">{esc(a_val)}</div></td>
          <td>{esc(r["bonus_type_short"])}</td><td>{fmt(r["rhythm"])}</td><td>{fmt(r["expressive"])}</td><td>{fmt(r["longtone_skill"])}</td><td>{fmt(r["vibrato_skill"])}</td><td>{esc(r["vibrato_type_label"])}</td>
        </tr>
        """)
    rows_html.append("</tbody></table>")
    return "".join(rows_html)

def render_pc_table(df, sort_col, sort_dir, date, song, artist, mode, search):
    rows_html = []
    headers_html = ['<th class="no-col pc-th-first">No.</th>']
    for col_key, label in HEADER_CONFIG_PC:
        href = make_sort_href(col_key, sort_col, sort_dir, date, song, artist, mode, search)
        active_class = (" active-desc" if sort_dir == "desc" else " active-asc") if col_key == sort_col else ""
        
        if col_key == "play_dt":
            w_class = " pc-th-date"
        elif col_key == "song_name":
            w_class = " pc-th-song"
        else:
            w_class = " pc-th-normal"
            
        headers_html.append(f'<th class="{w_class}"><a href="{href}" target="_self" class="sort-link{active_class}">{label}</a></th>')

    rows_html.append(f'<table class="dxg-table pc-table"><thead><tr>{"".join(headers_html)}</tr></thead><tbody>')

    for i, r in df.reset_index(drop=True).iterrows():
        bg = score_color(r["total_score"], r["bonus_score"])
        d_val = "" if pd.isna(r["play_date"]) else str(r["play_date"])
        s_val = str(r["song_name"]) if not pd.isna(r["song_name"]) else ""
        a_val = str(r["artist_name"]) if not pd.isna(r["artist_name"]) else ""
        
        date_href = f"?{urlencode({'date': d_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': mode, 'search': search})}" if d_val else "#"
        song_href = f"?{urlencode({'song': s_val, 'artist': a_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': mode, 'search': search})}" if s_val else "#"

        rows_html.append(f"""
        <tr>
          <td>{i+1}</td>
          <td><a href="{date_href}" target="_self" class="date-text">{esc(d_val)}</a></td>
          <td class="meta-cell-pc"><a href="{song_href}" target="_self" class="song-pc">{esc(s_val)}</a> <span class="artist-pc">/ {esc(a_val)}</span></td>
          <td class="score-cell-pc" style="background:{bg};">{fmt(r["total_score"], 3)}</td>
          <td>{fmt(r["base_score"], 3)}</td>
          <td>{fmt(r["bonus_score"], 3)}</td>
          <td>{esc(r["bonus_type_short"])}</td>
          <td>{fmt(r["chart_total"])}</td>
          <td>{fmt(r["pitch"])}</td>
          <td>{fmt(r["stability"])}</td>
          <td>{fmt(r["expressive"])}</td>
          <td>{fmt(r["rhythm"])}</td>
          <td>{fmt(r["vibrato_longtone"])}</td>
          <td>{fmt(r["emphasis"])}</td>
          <td>{fmt(r["shakuri_count"])}</td>
          <td>{fmt(r["kobushi_count"])}</td>
          <td>{fmt(r["fall_count"])}</td>
          <td>{fmt(r["longtone_skill"])}</td>
          <td>{fmt(r["vibrato_skill"])}</td>
          <td>{fmt(r["vibrato_seconds"], 1)}</td>
          <td>{fmt(r["vibrato_count"])}</td>
          <td>{esc(r["vibrato_type_label"])}</td>
        </tr>
        """)
    rows_html.append("</tbody></table>")
    return "".join(rows_html)

st.set_page_config(page_title="DX-G Viewer", layout="wide")

DXG_CSS = """
<style>
/* --- 全体共通 --- */
.dxg-table {
  border-collapse: collapse;
  font-family: Arial, "Yu Gothic", sans-serif;
  font-size: 14px;
}
.dxg-table th, .dxg-table td {
  border: 1px solid #bdbdbd;
  padding: 4px 5px;
  text-align: right;
  vertical-align: middle;
  white-space: nowrap;
}

/* --- ヘッダースクロール追従の完全固定（Streamlitバー対策） --- */
.dxg-table thead th {
  position: sticky;
  top: 56px; /* Streamlitのデフォルトヘッダー分（約56px）を避ける */
  z-index: 100;
  background-color: #f8f8f8 !important;
  font-weight: bold;
  color: #222;
  padding: 0 !important;
  height: 1px;
  box-shadow: 0 -1px 0 #bdbdbd, 0 1px 0 #bdbdbd; 
}

/* No.カラムのアライメント修正 */
.dxg-table th.no-col { text-align: left !important; padding-left: 8px !important; }
.dxg-table td:first-child { text-align: right !important; padding-right: 8px !important; }

.sort-link {
  display: flex; align-items: center; justify-content: center;
  padding: 4px 6px; color: #222 !important; text-decoration: none !important;
  box-sizing: border-box; height: 100%; border-radius: 0 !important;
}
.sort-link:hover { background: rgba(0,0,0,0.05); }
.sort-link.active-desc { background: #b00000 !important; color: white !important; }
.sort-link.active-asc { background: #0044b0 !important; color: white !important; }

/* --- カスタムナビゲーション (1440px統一) --- */
.custom-nav {
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 2px solid #ddd; padding: 0 10px; margin-bottom: 15px;
  max-width: 1440px; /* 表と端を揃える */
  margin: 0 auto 15px auto;
}
.nav-brand { font-size: 24px; font-weight: bold; color: #1666aa; }
.nav-tabs { display: flex; align-items: center; }
.nav-tabs a {
  padding: 10px 20px; color: #555 !important; text-decoration: none !important;
  font-weight: bold; border-bottom: 3px solid transparent; border-radius: 0 !important;
}
.nav-tabs a:hover { background: #f0f0f0; }
.nav-tabs a.active { border-bottom: 3px solid #1666aa; color: #1666aa !important; }

.pc-search-form { margin-right: 20px; display: flex; align-items: center; }

/* SP用アイコン・隠しメニュー */
.nav-sp-icons { display: none; font-size: 20px; color: #555; gap: 10px; align-items: center; }
.icon-label { cursor: pointer; padding: 6px 10px; border: 1px solid #ddd; background: #f8f8f8; border-radius: 4px; user-select: none; }
.icon-label:active { background: #eee; }
.hidden-toggle { display: none; }

.sp-search-bar { display: none; padding: 10px; background: #f8f8f8; border-bottom: 1px solid #ddd; margin-bottom: 15px; }
#search-toggle:checked ~ .sp-search-bar { display: block; }

.sp-dropdown { display: none; flex-direction: column; background: #f8f8f8; border-bottom: 1px solid #ddd; margin-bottom: 15px; }
.sp-dropdown a { padding: 12px; border-bottom: 1px solid #eee; color: #333 !important; text-decoration: none !important; font-weight: bold;}
#menu-toggle:checked ~ .sp-dropdown { display: flex; }

/* --- 全体のスクロール制限を解除 --- */
.view-pc, .view-sp {
  padding-bottom: 40px;
  overflow: visible !important;
}

/* --- PC専用スタイル（1440px統一 & カラム比率調整） --- */
.pc-table-wrapper {
  max-width: 1440px; /* 大画面での間延びを防ぎ、ナビゲーションと揃える */
  margin: 0 auto;
}
.pc-table { 
  width: 100%; 
  table-layout: fixed; 
}
.pc-table td { 
  text-align: center; 
  font-size: 14px !important;
  overflow: hidden;
  white-space: nowrap;
}
.pc-table a, .pc-table span {
  font-size: 14px !important;
}

/* PC版 各列の横幅比率（合計100%） - 曲名列の伸びすぎを防止 */
.pc-table th:nth-child(1) { width: 3.5%; }  /* No. */
.pc-table th:nth-child(2) { width: 7.0%; }  /* Date */
.pc-table th:nth-child(3) { width: 19.5%; } /* Song/Artist (-2%削減) */
.pc-table th:nth-child(4) { width: 7.0%; }  /* Score */
.pc-table th:nth-child(5) { width: 7.0; }  /* Base */
.pc-table th:nth-child(6) { width: 5.0%; }  /* Bonus */
.pc-table th:nth-child(7) { width: 3.5%; }  /* BonType (+1%追加) */
.pc-table th:nth-child(8) { width: 3.5%; }  /* Chart */
.pc-table th:nth-child(9), .pc-table th:nth-child(10), .pc-table th:nth-child(11),
.pc-table th:nth-child(12), .pc-table th:nth-child(13), .pc-table th:nth-child(14) { width: 3.5%; } /* 音〜抑 */
.pc-table th:nth-child(15), .pc-table th:nth-child(16), .pc-table th:nth-child(17),
.pc-table th:nth-child(18), .pc-table th:nth-child(19) { width: 2.5%; } /* し〜ビ */
.pc-table th:nth-child(20) { width: 3.5%; } /* V-Sec */
.pc-table th:nth-child(21) { width: 3.5%; } /* V-Cnt (+1%追加) */
.pc-table th:nth-child(22) { width: 3.5%; } /* V-Type */

.meta-cell-pc { 
  text-align: left !important; 
  text-overflow: ellipsis; 
}
.song-pc { color: #1670a8; text-decoration: underline; }
.artist-pc { color: #666; }

/* --- SP専用スタイル --- */
.header-container { display: flex; flex-direction: column; height: 100%; }
.right-align .sort-link { justify-content: flex-end; }
.sp-table .score-cell { text-align: center; font-weight: 500; box-shadow: inset 0 0 8px rgba(255,255,255,0.45); }
.sp-table .meta-cell { text-align: left; }
.sp-table .clip { display: block; width: 100%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.sp-table .song { color: #1670a8; text-decoration: underline; }
.sp-table .artist { color: #333; text-decoration: none; }
.sp-table .record-top td { border-top: 2px solid #666; } 
.sp-table .record-bottom td { border-bottom: 2px solid #666; }
.date-text { color: #1666aa; text-decoration: underline; }

/* --- レスポンシブ切り替え --- */
@media screen and (min-width: 1181px) {
  .view-sp, .sp-search-bar, .sp-dropdown, .hidden-toggle { display: none !important; }
  .view-pc { display: block; width: 100%; }
}
@media screen and (max-width: 1180px) {
  .view-pc { display: none !important; }
  .view-sp { display: block; width: 100%; } 
  
  .nav-tabs { display: none; }
  .nav-sp-icons { display: flex; }
  
  .sp-table { width: 100%; table-layout: fixed; font-size: 11px !important; }
  .sp-table th, .sp-table td { padding: 3px 1px; white-space: nowrap; overflow: hidden; }
  
  .sp-table .header-container .sort-link { justify-content: center !important; }

  /* スマホ版 横幅比率 */
  .sp-table th:nth-child(1) { width: 10%; } 
  .sp-table th:nth-child(2) { width: 28.5%; } 
  .sp-table th:nth-child(3) { width: 14%; } 
  .sp-table th:nth-child(4) { width: 12.5%; } 
  .sp-table th:nth-child(5) { width: 9%; }  
  .sp-table th:nth-child(6) { width: 6%; }  
  .sp-table th:nth-child(7) { width: 6%; }  
  .sp-table th:nth-child(8) { width: 6%; }  
  .sp-table th:nth-child(9) { width: 8%; }  
  
  /* スマホ版の点数フォントサイズを 13.5px にナーフ */
  .sp-table .score-cell { font-size: 12.5px !important; letter-spacing: -0.5px; } 
  .sp-table .sort-link { padding: 3px 2px; font-size: 11px; }
}
</style>
"""

csv_path = get_latest_csv()

if csv_path is None:
    st.error(f"CSVが見つかりません: {BACKUP_DIR}")
    st.stop()

raw = read_csv_safely(csv_path)
df = normalize(raw)

# URLパラメータ取得
mode = get_query_param("mode") or "history"
selected_date = get_query_param("date")
selected_song = get_query_param("song")
selected_artist = get_query_param("artist")
keyword = get_query_param("search")

sort_col = get_query_param("sort_col")
sort_dir = get_query_param("sort_dir")

# フィルタやモードによる並び順の初期設定
if mode == "best":
    idx = df.groupby(['song_name', 'artist_name'])['total_score'].idxmax()
    df = df.loc[idx]
    if not sort_col:
        sort_col = "total_score"
        sort_dir = "desc"
else:
    if not sort_col:
        sort_col = "play_dt"
        sort_dir = "desc"

# --- ナビゲーションバーのHTML生成 ---
active_hist = "active" if mode == "history" else ""
active_best = "active" if mode == "best" else ""
search_checked = 'checked="checked"' if keyword else ""

# 検索バーのiframe生成
iframe_srcdoc = get_search_iframe_srcdoc(keyword)

nav_html = f"""
<div class="custom-nav">
  <div class="nav-brand">精密集計DX-G</div>
  
  <div class="nav-tabs">
    <div class="pc-search-form">
      <iframe srcdoc="{iframe_srcdoc}" style="width: 220px; height: 32px; border: none; overflow: hidden;" scrolling="no" frameborder="0"></iframe>
    </div>
    <a href="?mode=history" target="_self" class="{active_hist}">歌唱履歴</a>
    <a href="?mode=best" target="_self" class="{active_best}">曲別最高点</a>
    <a href="#" target="_self">その他集計</a>
  </div>
  
  <div class="nav-sp-icons">
    <label for="search-toggle" class="icon-label">🔍</label>
    <label for="menu-toggle" class="icon-label">☰</label>
  </div>
</div>

<input type="checkbox" id="search-toggle" class="hidden-toggle" {search_checked}>
<div class="sp-search-bar">
  <iframe srcdoc="{iframe_srcdoc}" style="width: 100%; height: 32px; border: none; overflow: hidden;" scrolling="no" frameborder="0"></iframe>
</div>

<input type="checkbox" id="menu-toggle" class="hidden-toggle">
<div class="sp-dropdown">
  <a href="?mode=history" target="_self" class="{active_hist}">歌唱履歴</a>
  <a href="?mode=best" target="_self" class="{active_best}">曲別最高点</a>
  <a href="#" target="_self">その他集計</a>
</div>
"""

st.markdown(DXG_CSS + nav_html, unsafe_allow_html=True)

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

# 並び替え実行
if sort_col in view.columns:
    if sort_col in ["song_name", "artist_name", "vibrato_type_code"]:
        is_ascending = (sort_dir == "desc")
    else:
        is_ascending = (sort_dir == "asc")
    view = view.sort_values(sort_col, ascending=is_ascending)

active_filters = []
if selected_date: active_filters.append(f"日付: {selected_date}")
if selected_song and selected_artist: active_filters.append(f"楽曲: {selected_song}")
if keyword: active_filters.append(f"検索: {keyword}")

# --- HTMLテーブルの生成と描画 ---
html_sp = render_sp_table(view, sort_col, sort_dir, selected_date, selected_song, selected_artist, mode, keyword)
html_pc = render_pc_table(view, sort_col, sort_dir, selected_date, selected_song, selected_artist, mode, keyword)

html_string = f"""
<div class="view-pc"><div class="pc-table-wrapper">{html_pc}</div></div>
<div class="view-sp">{html_sp}</div>
"""
clean_html = "\n".join([line.strip() for line in html_string.split("\n")])
st.markdown(clean_html, unsafe_allow_html=True)