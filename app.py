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

HEADER_CONFIG_PC = [
    ("play_dt", "日付"), ("song_name", "曲名 / 歌手名"), ("total_score", "点数"),
    ("base_score", "素点"), ("bonus_score", "ボ点"), ("bonus_type_short", "ボタ"),
    ("chart_total", "チ計"), ("pitch", "音"), ("stability", "安"), ("expressive", "表"),
    ("rhythm", "リ"), ("vibrato_longtone", "VL"), ("emphasis", "抑"),
    ("shakuri_count", "し"), ("kobushi_count", "こ"), ("fall_count", "フ"),
    ("longtone_skill", "ロ"), ("vibrato_skill", "ビ"), ("vibrato_seconds", "ビ秒"),
    ("vibrato_count", "ビ回"), ("vibrato_type_code", "ビタ")
]

PC_NUM_RIGHT_KEYS = {
    "base_score", "bonus_score", "chart_total", "pitch", "stability",
    "expressive", "rhythm", "vibrato_longtone", "emphasis",
    "shakuri_count", "kobushi_count", "fall_count",
    "longtone_skill", "vibrato_skill", "vibrato_seconds", "vibrato_count",
}


# =========================================================
# HTMLビルダーヘルパー
# =========================================================
_LT = chr(60)
_GT = chr(62)

def tag_open(name, **attrs):
    parts = [_LT, name]
    for k, v in attrs.items():
        if v is None or v == "":
            continue
        key = "class" if k == "cls" else k
        parts.append(' ' + key + '="' + str(v) + '"')
    parts.append(_GT)
    return "".join(parts)

def tag_close(name):
    return _LT + "/" + name + _GT

def anchor(href, text, cls=None, target="_self"):
    return tag_open("a", href=href, target=target, cls=cls) + text + tag_close("a")


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
        "vl": pick_col(df, ["ビブラート/ロングトーン", "ビブラート/ロングトーン", "radarChartVibratoLongtone"]),
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

def get_search_iframe_srcdoc(keyword):
    srcdoc = """
    <!DOCTYPE html>
    <html><head><style>
      body { margin: 0; padding: 0; background: transparent; font-family: sans-serif; }
      form { margin: 0; display: flex; }
      input {
        width: 100%; height: 32px; padding: 6px 12px; border: 1px solid #ccc;
        border-radius: 4px; color: #333; font-size: 14px; outline: none; box-sizing: border-box;
      }
      input:focus { border-color: #1666aa; box-shadow: 0 0 4px rgba(22,102,170,0.3); }
      input::placeholder { color: #aaa; }
    </style>
    <script>
      function submitSearch(e, form) {
        e.preventDefault();
        var val = form.search.value;
        var topUrl = new URL(window.top.location.href);
        if (val) {
          topUrl.searchParams.set('search', val);
        } else {
          topUrl.searchParams.delete('search');
        }
        window.top.location.href = topUrl.toString();
      }
    </script>
    </head>
    <body>
      <form onsubmit='submitSearch(event, this)'>
        <input type='text' name='search' value='__KW__' placeholder='\U0001F50D 曲名 or 歌手名'>
      </form>
    </body></html>
    """
    srcdoc = srcdoc.replace("__KW__", html.escape(keyword))
    return html.escape(srcdoc)


def render_sp_table(df, sort_col, sort_dir, date, song, artist, mode, search):
    parts = []
    header_cells = []

    for idx, col_data in enumerate(HEADER_CONFIG_SP):
        align = col_data["align"]
        items = col_data["items"]
        links = []
        for i, (col_key, label) in enumerate(items):
            href = make_sort_href(col_key, sort_col, sort_dir, date, song, artist, mode, search)
            active_class = ("active-desc" if sort_dir == "desc" else "active-asc") if col_key == sort_col else ""
            link_cls = ("sort-link " + active_class).strip()

            if idx == 0 and i == 0:
                inner = (
                    '<div class="sp-nodate-header">'
                    + '<div class="sp-no-label">No.</div>'
                    + anchor(href, label, cls=(link_cls + " sp-date-label").strip())
                    + '</div>'
                )
                links.append(inner)
            else:
                links.append(anchor(href, label, cls=link_cls))

        cell = (
            '<th class="col-header ' + align + '-align">'
            + '<div class="header-container">' + "".join(links) + '</div>'
            + '</th>'
        )
        header_cells.append(cell)

    parts.append('<table class="dxg-table sp-table"><thead><tr>' + "".join(header_cells) + '</tr></thead><tbody>')

    for i, r in df.reset_index(drop=True).iterrows():
        bg = score_color(r["total_score"], r["bonus_score"])
        d_val = "" if pd.isna(r["play_date"]) else str(r["play_date"])
        s_val = str(r["song_name"]) if not pd.isna(r["song_name"]) else ""
        a_val = str(r["artist_name"]) if not pd.isna(r["artist_name"]) else ""

        date_href = "?" + urlencode({'date': d_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': 'history', 'search': search}) if d_val else "#"
        song_href = "?" + urlencode({'song': s_val, 'artist': a_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': 'history', 'search': search}) if s_val else "#"

        date_link = anchor(date_href, esc(d_val), cls="date-text sp-date-val")
        song_link = anchor(song_href, esc(s_val), cls="clip song")

        row1 = (
            '<tr class="record-top">'
            + '<td class="meta-cell">'
            +   '<div class="sp-nodate-row">'
            +     '<span class="sp-no-num">' + str(i+1) + '</span>'
            +     date_link
            +   '</div>'
            + '</td>'
            + '<td rowspan="3" class="score-cell" style="background:' + str(bg) + ';">' + fmt(r["total_score"], 3) + '</td>'
            + '<td>' + fmt(r["base_score"], 3) + '</td>'
            + '<td>' + fmt(r["chart_total"]) + '</td>'
            + '<td>' + fmt(r["pitch"]) + '</td>'
            + '<td>' + fmt(r["emphasis"]) + '</td>'
            + '<td>' + fmt(r["shakuri_count"]) + '</td>'
            + '<td>' + fmt(r["vibrato_seconds"], 1) + '</td>'
            + '</tr>'
        )
        row2 = (
            '<tr>'
            + '<td class="meta-cell">'
            +   '<div class="sp-nodate-row">'
            +     '<div class="sp-song-val">' + song_link + '</div>'
            +   '</div>'
            + '</td>'
            + '<td>' + fmt(r["bonus_score"], 3) + '</td>'
            + '<td>' + fmt(r["vibrato_longtone"]) + '</td>'
            + '<td>' + fmt(r["stability"]) + '</td>'
            + '<td>' + fmt(r["kobushi_count"]) + '</td>'
            + '<td>' + fmt(r["fall_count"]) + '</td>'
            + '<td>' + fmt(r["vibrato_count"]) + '</td>'
            + '</tr>'
        )
        row3 = (
            '<tr class="record-bottom">'
            + '<td class="meta-cell">'
            +   '<div class="sp-nodate-row">'
            +     '<div class="sp-artist-val clip artist">' + esc(a_val) + '</div>'
            +   '</div>'
            + '</td>'
            + '<td>' + esc(r["bonus_type_short"]) + '</td>'
            + '<td>' + fmt(r["rhythm"]) + '</td>'
            + '<td>' + fmt(r["expressive"]) + '</td>'
            + '<td>' + fmt(r["longtone_skill"]) + '</td>'
            + '<td>' + fmt(r["vibrato_skill"]) + '</td>'
            + '<td>' + esc(r["vibrato_type_label"]) + '</td>'
            + '</tr>'
        )
        parts.append(row1 + row2 + row3)

    parts.append("</tbody></table>")
    return "".join(parts)


def render_pc_table(df, sort_col, sort_dir, date, song, artist, mode, search):
    parts = []
    header_cells = ['<th class="no-col pc-th-first">No.</th>']

    for col_key, label in HEADER_CONFIG_PC:
        href = make_sort_href(col_key, sort_col, sort_dir, date, song, artist, mode, search)
        active_class = ("active-desc" if sort_dir == "desc" else "active-asc") if col_key == sort_col else ""
        link_cls = ("sort-link " + active_class).strip()

        if col_key == "play_dt":
            w_class = "pc-th-date"
        elif col_key == "song_name":
            w_class = "pc-th-song"
        else:
            w_class = "pc-th-normal"

        header_cells.append('<th class="' + w_class + '">' + anchor(href, label, cls=link_cls) + '</th>')

    parts.append('<table class="dxg-table pc-table"><thead><tr>' + "".join(header_cells) + '</tr></thead><tbody>')

    def td_num(key, value):
        cls_attr = ' class="num-right"' if key in PC_NUM_RIGHT_KEYS else ''
        return '<td' + cls_attr + '>' + str(value) + '</td>'

    for i, r in df.reset_index(drop=True).iterrows():
        bg = score_color(r["total_score"], r["bonus_score"])
        d_val = "" if pd.isna(r["play_date"]) else str(r["play_date"])
        s_val = str(r["song_name"]) if not pd.isna(r["song_name"]) else ""
        a_val = str(r["artist_name"]) if not pd.isna(r["artist_name"]) else ""

        date_href = "?" + urlencode({'date': d_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': 'history', 'search': search}) if d_val else "#"
        song_href = "?" + urlencode({'song': s_val, 'artist': a_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': 'history', 'search': search}) if s_val else "#"

        date_link = anchor(date_href, esc(d_val), cls="date-text")
        song_link = anchor(song_href, esc(s_val), cls="song-pc")

        row = (
            '<tr>'
            + '<td>' + str(i+1) + '</td>'
            + '<td>' + date_link + '</td>'
            + '<td class="meta-cell-pc">' + song_link + ' <span class="artist-pc">/ ' + esc(a_val) + '</span></td>'
            + '<td class="score-cell-pc" style="background:' + str(bg) + ';">' + fmt(r["total_score"], 3) + '</td>'
            + td_num("base_score", fmt(r["base_score"], 3))
            + td_num("bonus_score", fmt(r["bonus_score"], 3))
            + '<td>' + esc(r["bonus_type_short"]) + '</td>'
            + td_num("chart_total", fmt(r["chart_total"]))
            + td_num("pitch", fmt(r["pitch"]))
            + td_num("stability", fmt(r["stability"]))
            + td_num("expressive", fmt(r["expressive"]))
            + td_num("rhythm", fmt(r["rhythm"]))
            + td_num("vibrato_longtone", fmt(r["vibrato_longtone"]))
            + td_num("emphasis", fmt(r["emphasis"]))
            + td_num("shakuri_count", fmt(r["shakuri_count"]))
            + td_num("kobushi_count", fmt(r["kobushi_count"]))
            + td_num("fall_count", fmt(r["fall_count"]))
            + td_num("longtone_skill", fmt(r["longtone_skill"]))
            + td_num("vibrato_skill", fmt(r["vibrato_skill"]))
            + td_num("vibrato_seconds", fmt(r["vibrato_seconds"], 1))
            + td_num("vibrato_count", fmt(r["vibrato_count"]))
            + '<td>' + esc(r["vibrato_type_label"]) + '</td>'
            + '</tr>'
        )
        parts.append(row)

    parts.append("</tbody></table>")
    return "".join(parts)


st.set_page_config(page_title="DX-G Viewer", layout="wide")

DXG_CSS = """
<style>
/* Streamlit の block-container 幅段階変化を殺す（864px対策） */
[data-testid="stMainBlockContainer"],
section.main > div.block-container,
.stApp .main .block-container,
.stApp .block-container {
  max-width: 100% !important;
  padding-left: 1rem !important;
  padding-right: 1rem !important;
  padding-top: 1rem !important;
}

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

/* 二段sticky */
.custom-nav {
  position: sticky;
  top: 0;
  z-index: 300;
  background: #ffffff;
}
.sp-search-bar, .sp-dropdown {
  position: sticky;
  top: 56px;
  z-index: 250;
  background: #f8f8f8;
}
.dxg-table thead th {
  position: sticky;
  top: 56px;
  z-index: 100;
  background-color: #f8f8f8 !important;
  font-weight: bold;
  color: #222;
  padding: 0 !important;
  height: 1px;
  box-shadow: 0 -1px 0 #bdbdbd, 0 1px 0 #bdbdbd;
}

.dxg-table th.no-col { text-align: left !important; padding-left: 8px !important; }
.dxg-table td:first-child { text-align: right !important; padding-right: 8px !important; }

.sort-link {
  display: flex; align-items: center; justify-content: center;
  padding: 4px 6px; color: #222 !important; text-decoration: none !important;
  box-sizing: border-box; height: 100%; border-radius: 0 !important;
}
.sort-link:hover { background: rgba(0,0,0,0.05); }
.sort-link.active-desc { background: #b00000 !important; color: white !important; }
.sort-link.active-asc  { background: #0044b0 !important; color: white !important; }

.custom-nav {
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 2px solid #ddd; padding: 0 10px;
  max-width: 1440px;
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

.nav-sp-icons { display: none; font-size: 20px; color: #555; gap: 10px; align-items: center; }
.icon-label { cursor: pointer; padding: 6px 10px; border: 1px solid #ddd; background: #f8f8f8; border-radius: 4px; user-select: none; }
.icon-label:active { background: #eee; }
.hidden-toggle { display: none; }

.sp-search-bar { display: none; padding: 10px; border-bottom: 1px solid #ddd; margin-bottom: 15px; }
#search-toggle:checked ~ .sp-search-bar { display: block; }

.sp-dropdown { display: none; flex-direction: column; border-bottom: 1px solid #ddd; margin-bottom: 15px; }
.sp-dropdown a { padding: 12px; border-bottom: 1px solid #eee; color: #333 !important; text-decoration: none !important; font-weight: bold;}
#menu-toggle:checked ~ .sp-dropdown { display: flex; }

.view-pc, .view-sp {
  padding-bottom: 40px;
  overflow: visible !important;
}

/* PC版：外枠および横線を太くする（スマホ版の 2px solid #666 と同様に） */
.pc-table-wrapper { max-width: 1440px; margin: 0 auto; }
.pc-table { 
  width: 100%; 
  table-layout: fixed; 
  border: 2px solid #666; /* 外枠を太く */
}
.pc-table td { 
  text-align: center; 
  font-size: 14px !important; 
  overflow: hidden; 
  white-space: nowrap; 
  border-top: 2px solid #666 !important;    /* 各行の横線を太く */
  border-bottom: 2px solid #666 !important; /* 各行の横線を太く */
}
.pc-table thead th {
  /* PC版ヘッダーの上下境界も太くする */
  box-shadow: 0 -2px 0 #666, 0 2px 0 #666 !important;
}
.pc-table a, .pc-table span { font-size: 14px !important; }

/* PC版：指定16項目の数値セルだけ右揃え */
.pc-table td.num-right {
  text-align: right !important;
  padding-right: 10px !important;
  font-variant-numeric: tabular-nums;
}

.pc-table th:nth-child(1) { width: 3.5%; }
.pc-table th:nth-child(2) { width: 7.0%; }
.pc-table th:nth-child(3) { width: 23.0%; }
.pc-table th:nth-child(4) { width: 7.0%; }
.pc-table th:nth-child(5) { width: 7.0%; }
.pc-table th:nth-child(6) { width: 5.0%; }
.pc-table th:nth-child(7) { width: 4.0%; }
.pc-table th:nth-child(8) { width: 3.5%; }
.pc-table th:nth-child(9), .pc-table th:nth-child(10), .pc-table th:nth-child(11),
.pc-table th:nth-child(12), .pc-table th:nth-child(13), .pc-table th:nth-child(14) { width: 3.5%; }
.pc-table th:nth-child(15), .pc-table th:nth-child(16), .pc-table th:nth-child(17),
.pc-table th:nth-child(18), .pc-table th:nth-child(19) { width: 2.5%; }
.pc-table th:nth-child(20) { width: 3.5%; }
.pc-table th:nth-child(21) { width: 3.5%; }
.pc-table th:nth-child(22) { width: 3.5%; }

.meta-cell-pc { text-align: left !important; text-overflow: ellipsis; }
.song-pc { color: #1670a8; text-decoration: underline; }
.artist-pc { color: #666; }

.header-container { display: flex; flex-direction: column; height: 100%; }
.right-align .sort-link { justify-content: flex-end; }
.sp-table .score-cell {
  text-align: center;
  font-weight: 500;
  box-shadow: inset 0 0 8px rgba(255,255,255,0.45);
  border-bottom: 2px solid #666;
}
.sp-table .meta-cell { text-align: left; padding: 0 !important; }
.sp-table .clip { display: block; width: 100%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.sp-table .song { color: #1670a8; text-decoration: underline; }
.sp-table .artist { color: #333; text-decoration: none; }
.sp-table .record-top td { border-top: 2px solid #666; }
.sp-table .record-bottom td { border-bottom: 2px solid #666; }
.date-text { color: #1666aa; text-decoration: underline; }

/* SP版：No.（左揃え・42px）＋ 日付/曲名/歌手名（縦線を全3行に貫通） */
.sp-nodate-header {
  display: flex;
  align-items: stretch;
  width: 100%;
  height: 100%;
}
.sp-no-label {
  flex: 0 0 42px;
  min-width: 42px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  font-weight: bold;
  color: #222;
  border-right: 1px solid #bdbdbd;
  box-sizing: border-box;
}
.sp-date-label {
  flex: 1 1 auto;
  justify-content: center !important;
}

/* 本文3行共通のflex行 */
.sp-nodate-row {
  display: flex;
  align-items: stretch;
  width: 100%;
  min-height: 100%;
}

/* 1行目：No.の数値 */
.sp-no-num {
  flex: 0 0 42px;
  min-width: 42px;
  padding: 3px 4px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  color: #222;
  border-right: 1px solid #bdbdbd;
  box-sizing: border-box;
}
/* 1行目：日付 */
.sp-date-val {
  flex: 1 1 auto;
  padding: 3px 4px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 2行目：曲名（左寄せ） */
.sp-song-val {
  flex: 1 1 auto;
  padding: 3px 4px;
  text-align: left;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
}
/* 3行目：歌手名（左寄せ） */
.sp-artist-val {
  flex: 1 1 auto;
  padding: 3px 4px;
  text-align: left;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
}

@media screen and (min-width: 900px) {
  .view-sp, .sp-search-bar, .sp-dropdown, .hidden-toggle { display: none !important; }
  .view-pc { display: block; width: 100%; }
}
@media screen and (max-width: 899px) {
  .view-pc { display: none !important; }
  .view-sp { display: block; width: 100%; }

  .nav-tabs { display: none; }
  .nav-sp-icons { display: flex; }

  /* SP版：表全体を2pxの黒線で囲う */
  .sp-table { 
    width: 100%; 
    table-layout: fixed; 
    font-size: 11px !important; 
    border: 2px solid #666; 
  }
  .sp-table th, .sp-table td { padding: 3px 1px; white-space: nowrap; overflow: hidden; }
  /* meta-cell は padding: 0 を維持（縦線を上下いっぱいに引くため） */
  .sp-table td.meta-cell { padding: 0 !important; }

  .sp-table .header-container .sort-link { justify-content: center !important; }

  /* SP版ヘッダー内の仕切り罫線 */
  .sp-table .header-container > div:not(:last-child),
  .sp-table .header-container > a:not(:last-child) {
    border-bottom: 1px solid #bdbdbd;
  }

  .sp-table th:nth-child(1) { width: 39%; }
  .sp-table th:nth-child(2) { width: 14%; }
  .sp-table th:nth-child(3) { width: 13%; }
  .sp-table th:nth-child(4) { width: 7%; }
  .sp-table th:nth-child(5) { width: 7%; }
  .sp-table th:nth-child(6) { width: 7%; }
  .sp-table th:nth-child(7) { width: 6%; }
  .sp-table th:nth-child(8) { width: 7%; }

  .sp-table .score-cell { font-size: 12px !important; letter-spacing: -0.7px; }

  /* SP版ヘッダーの高さ圧縮（paddingとline-heightを詰める） */
  .sp-table .sort-link { padding: 1px 2px !important; font-size: 11px; line-height: 1.15; }
  .sp-no-label { padding: 1px 4px !important; line-height: 1.15; }
}
</style>
"""

csv_path = get_latest_csv()

if csv_path is None:
    st.error("CSVが見つかりません: " + str(BACKUP_DIR))
    st.stop()

raw = read_csv_safely(csv_path)
df = normalize(raw)

mode = get_query_param("mode") or "history"
selected_date = get_query_param("date")
selected_song = get_query_param("song")
selected_artist = get_query_param("artist")
keyword = get_query_param("search")

sort_col = get_query_param("sort_col")
sort_dir = get_query_param("sort_dir")

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

active_hist = "active" if mode == "history" else ""
active_best = "active" if mode == "best" else ""
search_checked = 'checked="checked"' if keyword else ""

iframe_srcdoc = get_search_iframe_srcdoc(keyword)

nav_tab_hist = anchor("?mode=history", "歌唱履歴", cls=active_hist)
nav_tab_best = anchor("?mode=best", "曲別最高点", cls=active_best)
nav_tab_other = anchor("#", "その他集計")

sp_tab_hist = anchor("?mode=history", "歌唱履歴", cls=active_hist)
sp_tab_best = anchor("?mode=best", "曲別最高点", cls=active_best)
sp_tab_other = anchor("#", "その他集計")

nav_html = (
    '<div class="custom-nav">'
    + '<div class="nav-brand">精密集計DX-G</div>'
    + '<div class="nav-tabs">'
    +   '<div class="pc-search-form">'
    +     '<iframe srcdoc="' + iframe_srcdoc + '" style="width: 220px; height: 32px; border: none; overflow: hidden;" scrolling="no" frameborder="0"></iframe>'
    +   '</div>'
    +   nav_tab_hist + nav_tab_best + nav_tab_other
    + '</div>'
    + '<div class="nav-sp-icons">'
    +   '<label for="search-toggle" class="icon-label">\U0001F50D</label>'
    +   '<label for="menu-toggle" class="icon-label">\u2630</label>'
    + '</div>'
    + '</div>'
    + '<input type="checkbox" id="search-toggle" class="hidden-toggle" ' + search_checked + '>'
    + '<div class="sp-search-bar">'
    +   '<iframe srcdoc="' + iframe_srcdoc + '" style="width: 100%; height: 32px; border: none; overflow: hidden;" scrolling="no" frameborder="0"></iframe>'
    + '</div>'
    + '<input type="checkbox" id="menu-toggle" class="hidden-toggle">'
    + '<div class="sp-dropdown">'
    +   sp_tab_hist + sp_tab_best + sp_tab_other
    + '</div>'
)

view = df.copy()

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

if sort_col in view.columns:
    if sort_col in ["song_name", "artist_name", "vibrato_type_code"]:
        is_ascending = (sort_dir == "desc")
    else:
        is_ascending = (sort_dir == "asc")
    view = view.sort_values(sort_col, ascending=is_ascending)

active_filters = []
if selected_date: active_filters.append("日付: " + str(selected_date))
if selected_song and selected_artist: active_filters.append("楽曲: " + str(selected_song))
if keyword: active_filters.append("検索: " + str(keyword))

html_sp = render_sp_table(view, sort_col, sort_dir, selected_date, selected_song, selected_artist, mode, keyword)
html_pc = render_pc_table(view, sort_col, sort_dir, selected_date, selected_song, selected_artist, mode, keyword)

html_string = (
    '<div class="dxg-scroll-wrapper">'
    + '<div class="view-pc"><div class="pc-table-wrapper">' + html_pc + '</div></div>'
    + '<div class="view-sp">' + html_sp + '</div>'
    + '</div>'
)

combined = DXG_CSS + nav_html + html_string
clean_html = "\n".join([line.strip() for line in combined.split("\n")])
st.markdown(clean_html, unsafe_allow_html=True)