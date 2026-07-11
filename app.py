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

PC_NUM_SLOT_WIDTH = {
    "base_score": 6.4, "bonus_score": 4.4, "chart_total": 3,
    "pitch": 3, "stability": 3, "expressive": 3,
    "rhythm": 3, "vibrato_longtone": 3, "emphasis": 3,
    "shakuri_count": 2, "kobushi_count": 2, "fall_count": 2,
    "longtone_skill": 2, "vibrato_skill": 2,
    "vibrato_seconds": 3.4, "vibrato_count": 3,
}

SP_NUM_SLOT_WIDTH = {
    "base_score": 6.4, "bonus_score": 6.4, "bonus_type_short": 6.4,
    "chart_total": 3, "vibrato_longtone": 3, "rhythm": 3,
    "pitch": 3, "stability": 3, "expressive": 3,
    "emphasis": 3, "kobushi_count": 3, "longtone_skill": 3,
    "shakuri_count": 2, "fall_count": 2, "vibrato_skill": 2,
    "vibrato_seconds": 3.4, "vibrato_count": 3.4, "vibrato_type_label": 3.4,
}

# 案B: header table と body table を分離するため、列幅を colgroup で明示指定。
# 両テーブルで同じ列幅リストを共有することで列幅を完全同期させる。
PC_COL_WIDTHS = [
    "5.5%",  # No.
    "7.0%",  # 日付
    "23.0%", # 曲名/歌手名
    "6.5%",  # 点数
    "6.5%",  # 素点
    "4.5%",  # ボ点
    "3.5%",  # ボタ
    "3.5%",  # チ計
    "3.5%",  # 音
    "3.5%",  # 安
    "3.5%",  # 表
    "3.5%",  # リ
    "3.5%",  # VL
    "3.5%",  # 抑
    "2.5%",  # し
    "2.5%",  # こ
    "2.5%",  # フ
    "2.5%",  # ロ
    "2.5%",  # ビ
    "3.5%",  # ビ秒
    "3.5%",  # ビ回
    "3.5%",  # ビタ
]

SP_COL_WIDTHS = [
    "39%",   # No + 日付/曲名/歌手名
    "14%",   # 点数
    "13%",   # 素点/ボ点/ボタ
    "7%",    # チ計/VL/リ
    "7%",    # 音/安/表
    "7%",    # 抑/こ/ロ
    "6%",    # し/フ/ビ
    "7%",    # ビ秒/ビ回/ビタ
]


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


def num_slot(value, width):
    return '<span class="num-slot" style="width:' + str(width) + 'ch">' + str(value) + '</span>'


def build_colgroup(widths):
    """colgroup要素を生成。両テーブル間で共有することで列幅を同期させる。"""
    cols = ''.join(['<col style="width:' + w + '">' for w in widths])
    return '<colgroup>' + cols + '</colgroup>'


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
        out["play_dt"] = pd.to_datetime(out["play_datetime"], format="mixed", errors="coerce")
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
        width: 100%; height: 32px; 
        padding: 6px 12px 6px 30px;
        border: 1px solid #ccc;
        border-radius: 4px; color: #333; font-size: 14px; outline: none; box-sizing: border-box;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="%23888888" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>');
        background-repeat: no-repeat;
        background-position: 8px center;
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
        <input type='text' name='search' value='__KW__' placeholder='曲名 or 歌手名'>
      </form>
    </body></html>
    """
    srcdoc = srcdoc.replace("__KW__", html.escape(keyword))
    return html.escape(srcdoc)


# ========== SP版 header table (thead 1行だけ) ==========
def render_sp_header(sort_col, sort_dir, date, song, artist, mode, search):
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

    return (
        '<table class="dxg-table sp-header-table">'
        + build_colgroup(SP_COL_WIDTHS)
        + '<thead><tr>' + "".join(header_cells) + '</tr></thead>'
        + '</table>'
    )


# ========== SP版 body table (tbody だけ) ==========
def render_sp_body(df, sort_col, sort_dir, date, song, artist, mode, search):
    parts = ['<table class="dxg-table sp-body-table">' + build_colgroup(SP_COL_WIDTHS) + '<tbody>']

    if df.empty:
        colspan = len(SP_COL_WIDTHS)
        parts.append(
            '<tr class="empty-row"><td colspan="' + str(colspan)
            + '" class="empty-cell">該当する曲はありません</td></tr>'
        )
    else:
        for i, r in df.reset_index(drop=True).iterrows():
            bg = score_color(r["total_score"], r["bonus_score"])
            d_val = "" if pd.isna(r["play_date"]) else str(r["play_date"])
            s_val = str(r["song_name"]) if not pd.isna(r["song_name"]) else ""
            a_val = str(r["artist_name"]) if not pd.isna(r["artist_name"]) else ""

            date_href = "?" + urlencode({'date': d_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': 'history', 'search': search}) if d_val else "#"
            song_href = "?" + urlencode({'song': s_val, 'artist': a_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': 'history', 'search': search}) if s_val else "#"

            # 絞り込み条件と一致する日付/曲名はリンク化しない
            if date == d_val:
                date_link = '<span class="date-plain sp-date-val">' + esc(d_val) + '</span>'
            else:
                date_link = anchor(date_href, esc(d_val), cls="date-text sp-date-val")

            if song == s_val and artist == a_val:
                song_link = '<span class="song-plain clip song-nolink">' + esc(s_val) + '</span>'
            else:
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
                + '<td>' + num_slot(fmt(r["base_score"], 3), SP_NUM_SLOT_WIDTH["base_score"]) + '</td>'
                + '<td>' + num_slot(fmt(r["chart_total"]), SP_NUM_SLOT_WIDTH["chart_total"]) + '</td>'
                + '<td>' + num_slot(fmt(r["pitch"]), SP_NUM_SLOT_WIDTH["pitch"]) + '</td>'
                + '<td>' + num_slot(fmt(r["emphasis"]), SP_NUM_SLOT_WIDTH["emphasis"]) + '</td>'
                + '<td>' + num_slot(fmt(r["shakuri_count"]), SP_NUM_SLOT_WIDTH["shakuri_count"]) + '</td>'
                + '<td>' + num_slot(fmt(r["vibrato_seconds"], 1), SP_NUM_SLOT_WIDTH["vibrato_seconds"]) + '</td>'
                + '</tr>'
            )
            row2 = (
                '<tr>'
                + '<td class="meta-cell">'
                +   '<div class="sp-nodate-row">'
                +     '<div class="sp-song-val">' + song_link + '</div>'
                +   '</div>'
                + '</td>'
                + '<td>' + num_slot(fmt(r["bonus_score"], 3), SP_NUM_SLOT_WIDTH["bonus_score"]) + '</td>'
                + '<td>' + num_slot(fmt(r["vibrato_longtone"]), SP_NUM_SLOT_WIDTH["vibrato_longtone"]) + '</td>'
                + '<td>' + num_slot(fmt(r["stability"]), SP_NUM_SLOT_WIDTH["stability"]) + '</td>'
                + '<td>' + num_slot(fmt(r["kobushi_count"]), SP_NUM_SLOT_WIDTH["kobushi_count"]) + '</td>'
                + '<td>' + num_slot(fmt(r["fall_count"]), SP_NUM_SLOT_WIDTH["fall_count"]) + '</td>'
                + '<td>' + num_slot(fmt(r["vibrato_count"]), SP_NUM_SLOT_WIDTH["vibrato_count"]) + '</td>'
                + '</tr>'
            )
            row3 = (
                '<tr class="record-bottom">'
                + '<td class="meta-cell">'
                +   '<div class="sp-nodate-row">'
                +     '<div class="sp-artist-val clip artist">' + esc(a_val) + '</div>'
                +   '</div>'
                + '</td>'
                + '<td>' + num_slot(esc(r["bonus_type_short"]), SP_NUM_SLOT_WIDTH["bonus_type_short"]) + '</td>'
                + '<td>' + num_slot(fmt(r["rhythm"]), SP_NUM_SLOT_WIDTH["rhythm"]) + '</td>'
                + '<td>' + num_slot(fmt(r["expressive"]), SP_NUM_SLOT_WIDTH["expressive"]) + '</td>'
                + '<td>' + num_slot(fmt(r["longtone_skill"]), SP_NUM_SLOT_WIDTH["longtone_skill"]) + '</td>'
                + '<td>' + num_slot(fmt(r["vibrato_skill"]), SP_NUM_SLOT_WIDTH["vibrato_skill"]) + '</td>'
                + '<td>' + num_slot(esc(r["vibrato_type_label"]), SP_NUM_SLOT_WIDTH["vibrato_type_label"]) + '</td>'
                + '</tr>'
            )
            parts.append(row1 + row2 + row3)

    parts.append("</tbody></table>")
    return "".join(parts)


# ========== PC版 header table (thead 1行だけ) ==========
def render_pc_header(sort_col, sort_dir, date, song, artist, mode, search):
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

    return (
        '<table class="dxg-table pc-header-table">'
        + build_colgroup(PC_COL_WIDTHS)
        + '<thead><tr>' + "".join(header_cells) + '</tr></thead>'
        + '</table>'
    )


# ========== PC版 body table (tbody だけ) ==========
def render_pc_body(df, sort_col, sort_dir, date, song, artist, mode, search):
    parts = ['<table class="dxg-table pc-body-table">' + build_colgroup(PC_COL_WIDTHS) + '<tbody>']

    def td_num(key, value):
        w = PC_NUM_SLOT_WIDTH.get(key)
        if w is None:
            return '<td>' + str(value) + '</td>'
        return '<td>' + num_slot(value, w) + '</td>'

    if df.empty:
        colspan = len(PC_COL_WIDTHS)
        parts.append(
            '<tr class="empty-row"><td colspan="' + str(colspan)
            + '" class="empty-cell">該当する曲はありません</td></tr>'
        )
    else:
        for i, r in df.reset_index(drop=True).iterrows():
            bg = score_color(r["total_score"], r["bonus_score"])
            d_val = "" if pd.isna(r["play_date"]) else str(r["play_date"])
            s_val = str(r["song_name"]) if not pd.isna(r["song_name"]) else ""
            a_val = str(r["artist_name"]) if not pd.isna(r["artist_name"]) else ""

            date_href = "?" + urlencode({'date': d_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': 'history', 'search': search}) if d_val else "#"
            song_href = "?" + urlencode({'song': s_val, 'artist': a_val, 'sort_col': sort_col, 'sort_dir': sort_dir, 'mode': 'history', 'search': search}) if s_val else "#"
            
            if date == d_val:
                date_link = '<span class="date-plain">' + esc(d_val) + '</span>'
            else:
                date_link = anchor(date_href, esc(d_val), cls="date-text")

            if song == s_val and artist == a_val:
                song_link = '<span class="song-plain">' + esc(s_val) + '</span>'
            else:
                song_link = anchor(song_href, esc(s_val), cls="song-pc")

            row = (
                '<tr>'
                + '<td>' + str(i+1) + '</td>'
                + '<td>' + date_link + '</td>'
                + '<td class="meta-cell-pc pc-txt-cell">' + song_link + ' <span class="artist-pc">/ ' + esc(a_val) + '</span></td>'
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


# Streamlit skeleton (ロード中の灰色プレースホルダ) を早期非表示化。
# st.set_page_config 直後に注入することで、Python 実行中に見える
# skeleton の表示時間を短縮する（ゼロにはできないが体感的に消える）。
# e2obbcf 系は Streamlit の skeleton コンポーネント (Emotion CSS)、
# .stAppSkeleton は skeleton のルート要素。
# html セレクタを頭に付けて specificity を 0,1,1 に上げ、
# Streamlit 側の CSS (0,1,0) に勝つ。

st.markdown("""
<style>
html [class*="e2obbcf"] {
  display: none !important;
}
html .stAppSkeleton {
  display: none !important;
}
</style>
""", unsafe_allow_html=True)

DXG_CSS = """
<style>
:root {
  --pc-td-pad-num: 0px;
  --pc-td-pad-txt: clamp(4.5px, calc(-19.5px + 2.4vw), 15.06px);
}

header[data-testid="stHeader"] {
  display: none !important;
}

[data-testid="stMainBlockContainer"],
section.main > div.block-container,
.stApp .main .block-container,
.stApp .block-container {
  max-width: 100% !important;
  padding-left: 1rem !important;
  padding-right: 1rem !important;
  padding-top: 0 !important;
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

/* Streamlit の stVerticalBlock は縦積み flex + gap: 1rem (16px) で、
   最初の要素 (nav) の上に 16px の隙間ができる。
   sticky nav 発動時にこの隙間分ずれて見えるため、gap を 0 に潰す。 */
.stVerticalBlock {
  gap: 0 !important;
}

/* nav 系 (変更なし) */
.custom-nav {
  position: sticky;
  top: 0;
  z-index: 300;
  background: #ffffff;
  height: 70px;
  box-sizing: border-box;
}
.sp-search-bar, .sp-dropdown {
  position: sticky;
  top: 70px;
  z-index: 250;
  background: #f8f8f8;
}

.dxg-table th.no-col { text-align: left !important; padding-left: 8px !important; }

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
  padding: 0 10px 14px 10px;
  max-width: 1440px;
  margin: 0 auto;
}
.custom-nav::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 12px;
  height: 2px;
  background: #ddd;
}

.nav-brand {
  font-size: 24px; font-weight: bold; color: #1666aa;
  display: inline-flex; align-items: center;
  height: 40px;
}
.nav-tabs { display: flex; align-items: center; }
.nav-tabs a {
  padding: 0 20px;
  height: 40px;
  display: inline-flex; align-items: center;
  box-sizing: border-box;
  color: #555 !important; text-decoration: none !important;
  font-weight: bold; border-radius: 0 !important;
}
.nav-tabs a:hover { background: #f0f0f0; }
.nav-tabs a.active { color: #1666aa !important; }

.pc-search-form {
  margin-right: 20px;
  height: 40px;
  display: inline-flex; align-items: center;
}

.nav-sp-icons { display: none; font-size: 20px; color: #555; gap: 10px; align-items: center; }
.icon-label { cursor: pointer; border: 1px solid #ddd; background: #f8f8f8; border-radius: 4px; user-select: none; }
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
.view-sp {
  display: flex;
  flex-direction: column;
}

/* 検索結果 0 件時の空状態メッセージ。表1/表2 は非表示なので、
   スペースの中央あたりにテキストだけ表示する。 */
.empty-state {
  max-width: 1440px;
  /* 上下のマージンを 0 に、余白は padding のみで確保。
     結果としてビューの最上部（灰色線の直下）に貼り付く形になる。 */
  margin: 0 auto;
  padding: 0px 0px;
  text-align: center;
  color: #888;
  font-size: 20px;
  font-family: Arial, "Source Sans", sans-serif;
}

/* ========================================
   案B: PC版 header table (テーブル全体を sticky) 
   ======================================== */
.pc-table-wrapper {
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
}

/* Streamlit または markdown パーサが挿入する余計な margin を潰す。
   header table は margin 0、body table は margin-top: -1px で
   1px の隙間を吸収して表2の上に見える灰色1px線を潰す。 */
.pc-header-table,
.sp-header-table {
  margin: 0 !important;
}
.pc-body-table,
.sp-body-table {
  margin: -1px 0 0 0 !important;
}

.pc-header-table {
  width: 100%;
  table-layout: fixed;
  border: 2px solid #666;
  position: sticky;
  top: 70px;
  z-index: 100;
  background: #f8f8f8;
}
.pc-header-table thead th {
  background-color: #f8f8f8;
  font-weight: bold;
  color: #222;
  padding: 0;
  height: 1px;
  border: 1px solid #bdbdbd;
}
.pc-header-table thead th:first-child {
  text-align: left;
  padding-left: 8px;
}
.pc-header-table a, .pc-header-table span { font-size: 14px !important; }

/* PC版 body table (通常テーブル、border-topを削って header との境界を統一) */
.pc-body-table {
  width: 100%;
  table-layout: fixed;
  border: 2px solid #666;
  border-top: 0;
}
.pc-body-table td {
  text-align: center;
  font-size: 14px !important;
  overflow: hidden;
  white-space: nowrap;
  /* border-top を 0 にして、各行間の2px黒は border-bottom のみで表現する。これにより表2の最上行と表1の下罫線が重複せず、綺麗に繋がる。 */
  border-top: 0 !important;
  border-bottom: 2px solid #666;
  border-left: 1px solid #bdbdbd;
  border-right: 1px solid #bdbdbd;
  padding: 4px var(--pc-td-pad-num);
}

.pc-body-table td.pc-txt-cell {
  padding: 4px var(--pc-td-pad-txt);
}
.pc-body-table td:first-child {
  text-align: right;
  padding-right: 8px;
}
.pc-body-table a, .pc-body-table span { font-size: 14px !important; }

/* 数値スロット */
.num-slot {
  display: inline-block;
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: pre;
  padding: 0;
}

.meta-cell-pc { text-align: left !important; text-overflow: ellipsis; }
.song-pc { color: #1670a8; text-decoration: underline; }
.artist-pc { color: #31333F; }

.header-container {
  display: grid;
  grid-template-rows: repeat(3, 1fr);
  height: 100%;
}
.header-container > * {
  min-height: 0;
  display: flex;
  align-items: center;
}
.sp-header-table .center-align .header-container > *,
.pc-header-table .center-align .header-container > * {
  grid-row: 1 / -1;
}
.right-align .sort-link { justify-content: flex-end; }

/* ========================================
   検索0件時の空状態メッセージ
   header table の border-bottom (2px黒) を上罫線として利用し、
   左右下は自身の border で 2px 黒外枠を完成させる。
   ======================================== */
.empty-cell {
  text-align: center !important;
  padding: 40px 10px !important;
  color: #888 !important;
  font-size: 15px !important;
  border-left: 2px solid #666 !important;
  border-right: 2px solid #666 !important;
  border-bottom: 2px solid #666 !important;
  border-top: 0 !important;
}

/* ========================================
   案B: SP版 header/body table
   ======================================== */
.sp-header-table {
  width: 100%;
  table-layout: fixed;
  font-size: 11px;
  border: 2px solid #666;
  position: sticky;
  top: 70px;
  z-index: 100;
  background: #f8f8f8;
}
.sp-body-table {
  width: 100%;
  table-layout: fixed;
  font-size: 11px;
  border: 2px solid #666;
  border-top: 0;
}
.sp-header-table thead th {
  background-color: #f8f8f8;
  font-weight: bold;
  color: #222;
  padding: 0;
  border: 1px solid #bdbdbd;
  height: 1px;
}

.sp-body-table td { text-align: center; }
.sp-body-table .score-cell {
  text-align: center;
  font-weight: 500;
  box-shadow: inset 0 0 8px rgba(255,255,255,0.45);
  border-bottom: 2px solid #666;
}
.sp-body-table .meta-cell { text-align: left; padding: 0 !important; }
.sp-body-table .clip { display: block; width: 100%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.sp-body-table .song { color: #0054a3; text-decoration: underline; }
.sp-body-table .artist { color: #31333F; text-decoration: none; }
/* record-top 行の td 上罫線 2px黒。ただし最初の record-top（表2の一番上の行）は、表1の下罫線と重なるため 0 にする。 */
.sp-body-table .record-top td { border-top: 0 !important; }
.sp-body-table .record-bottom td { border-bottom: 2px solid #666; }
.date-text { color: #1666aa; text-decoration: underline; }

/* 絞り込み中の一致要素はプレーンテキスト（黒文字、下線なし）で表示。
   通常表示時のリンク（青文字下線）と区別する。 */
.date-plain {
  color: #31333F;
  text-decoration: none;
}
.song-plain {
  color: #31333F;
  text-decoration: none;
}
.sp-body-table .song-plain {
  color: #31333F !important;
  text-decoration: none !important;
}

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

.sp-nodate-row {
  display: flex;
  align-items: stretch;
  width: 100%;
  min-height: 100%;
}

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
.sp-date-val {
  flex: 1 1 auto;
  padding: 3px 4px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  overflow: hidden;
  text-overflow: ellipsis;
}
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

@media screen and (min-width: 1000px) {
  .view-sp, .sp-search-bar, .sp-dropdown, .hidden-toggle { display: none !important; }
  .view-pc { display: block; width: 100%; }
}
@media screen and (max-width: 999px) {
  .view-pc { display: none !important; }
  .view-sp { display: block; width: 100%; }

  .nav-tabs { display: none; }
  .nav-sp-icons { display: flex; }

  .sp-body-table th, .sp-body-table td { padding: 3px 0px; white-space: nowrap; overflow: hidden; }
  .sp-body-table td.meta-cell { padding: 0 !important; }
  .sp-body-table .num-slot { padding: 0; }
  .sp-header-table th { padding: 3px 0px; }

  .sp-body-table .num-slot {
    font-family: Arial, "Helvetica Neue", sans-serif;
    letter-spacing: -0.3px;
  }

  /* SP版 header-container を grid に切り替えて子要素を等分ストレッチ。
     flex column + flex-grow は Safari の一部で main-axis 拡張が効かないことがあるため
     grid が確実に動作する。
     - 点数セル（子1個）: 1行が th 全高を占有 → sort-link 全体が背景色＋クリック可
     - 3項目セル（素点/ボ点/ボタ 等）: 3行が th 全高を均等に 1/3 ずつ占有
     min-height: 0 は grid item のデフォルト min-height: auto を上書きし、
     子要素が想定以上に膨らむのを防ぐ。 */
  .sp-header-table .header-container {
    display: grid;
    grid-auto-rows: 1fr;
    grid-template-columns: 100%;  /* 1列で幅100% */
    /* または grid-template-columns: minmax(0, 1fr); */
  }
  .sp-header-table .header-container > * {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    box-sizing: border-box;
  }
  .sp-header-table .header-container .sort-link { justify-content: center !important; }

  .sp-header-table .header-container > div:not(:last-child),
  .sp-header-table .header-container > a:not(:last-child) {
    border-bottom: 1px solid #bdbdbd;
  }

  .sp-body-table .score-cell { font-size: 12px !important; letter-spacing: -0.7px; }

  .sp-header-table .sort-link { padding: 1px 2px !important; font-size: 11px; line-height: 1.15; }
  .sp-no-label { padding: 1px 4px !important; line-height: 1.15; }

  /* SP版の空状態メッセージ：フォントサイズと padding を SP 用に調整 */
  .sp-body-table .empty-cell {
    font-size: 12px !important;
    padding: 30px 10px !important;
  }
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

search_svg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>'
menu_svg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>'

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
    +   '<label for="search-toggle" class="icon-label" style="display:flex; align-items:center; padding: 6px 8px;">' + search_svg + '</label>'
    +   '<label for="menu-toggle" class="icon-label" style="display:flex; align-items:center; padding: 6px 8px;">' + menu_svg + '</label>'
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

# 検索結果が0件のときは表を非表示にし、「該当する曲はありません」を表示。
# それ以外は案B: header/body の 2テーブル構造で HTML を組み立てる。
if view.empty:
    empty_msg = '<div class="empty-state">該当する曲はありません</div>'
    html_string = (
        '<div class="dxg-scroll-wrapper">'
        + '<div class="view-pc">' + empty_msg + '</div>'
        + '<div class="view-sp">' + empty_msg + '</div>'
        + '</div>'
    )
else:
    html_sp_header = render_sp_header(sort_col, sort_dir, selected_date, selected_song, selected_artist, mode, keyword)
    html_sp_body = render_sp_body(view, sort_col, sort_dir, selected_date, selected_song, selected_artist, mode, keyword)
    html_pc_header = render_pc_header(sort_col, sort_dir, selected_date, selected_song, selected_artist, mode, keyword)
    html_pc_body = render_pc_body(view, sort_col, sort_dir, selected_date, selected_song, selected_artist, mode, keyword)

    html_string = (
        '<div class="dxg-scroll-wrapper">'
        + '<div class="view-pc"><div class="pc-table-wrapper">' + html_pc_header + html_pc_body + '</div></div>'
        + '<div class="view-sp">' + html_sp_header + html_sp_body + '</div>'
        + '</div>'
    )

combined = DXG_CSS + nav_html + html_string
clean_html = "\n".join([line.strip() for line in combined.split("\n")])
st.markdown(clean_html, unsafe_allow_html=True)
