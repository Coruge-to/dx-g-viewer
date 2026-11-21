// 精密集計DX-G の画面(静的サイト版)。Streamlit 版 (app.py) の、表の部分の移植。
// データ(dataset/history.jsonl)を読み、歌唱履歴・曲別最高点の表(PC版・スマホ版)と、ページ送りを、ブラウザの中で作る。
// 並べ替え・絞り込み・検索・ページ送りは、アドレスの条件(?mode=...&sort_col=...)で決まる(Streamlit 版と同じアドレスの形。画面の名前は、短い別名 ?best ?stats も使える)。
// 見た目は、Streamlit 版と同じにする(CSSは viewer.css。HTMLの形も同じ)。

const VIBRATO_TYPE_MAP = { 0: "N", 1: "A-1", 2: "B-1", 3: "C-1", 4: "A-2", 5: "B-2", 6: "C-2", 7: "A-3", 8: "B-3", 9: "C-3", 10: "D", 11: "E", 12: "F", 13: "G", 14: "H" };
const VIB_TYPE = Object.fromEntries(Object.entries(VIBRATO_TYPE_MAP).map(([k, v]) => [v, Number(k)]));
const BONUS_TYPE = { 1: "音程ボーナス", 2: "ビブラートボーナス", 3: "表現力ボーナス" };
const BONUS_SHORT_MAP = { "音程ボーナス": "音", "ビブラートボーナス": "ビ", "表現力ボーナス": "表" };

const HEADER_CONFIG_SP = [
  { align: "right", items: [["play_dt", "日付"], ["song_name", "曲名"], ["artist_name", "歌手名"]] },
  { align: "center", items: [["total_score", "点数"]] },
  { align: "right", items: [["base_score", "素点"], ["bonus_score", "ボ点"], ["bonus_type_short", "ボタ"]] },
  { align: "right", items: [["chart_total", "チ計"], ["vibrato_longtone", "VL"], ["rhythm", "リ"]] },
  { align: "right", items: [["pitch", "音"], ["stability", "安"], ["expressive", "表"]] },
  { align: "right", items: [["emphasis", "抑"], ["kobushi_count", "こ"], ["longtone_skill", "ロ"]] },
  { align: "right", items: [["shakuri_count", "し"], ["fall_count", "フ"], ["vibrato_skill", "ビ"]] },
  { align: "right", items: [["vibrato_seconds", "ビ秒"], ["vibrato_count", "ビ回"], ["vibrato_type_code", "ビタ"]] },
];

const HEADER_CONFIG_PC = [
  ["play_dt", "日付"], ["song_name", "曲名 / 歌手名"], ["total_score", "点数"],
  ["base_score", "素点"], ["bonus_score", "ボ点"], ["bonus_type_short", "ボタ"],
  ["chart_total", "チ計"], ["pitch", "音"], ["stability", "安"], ["expressive", "表"],
  ["rhythm", "リ"], ["vibrato_longtone", "VL"], ["emphasis", "抑"],
  ["shakuri_count", "し"], ["kobushi_count", "こ"], ["fall_count", "フ"],
  ["longtone_skill", "ロ"], ["vibrato_skill", "ビ"], ["vibrato_seconds", "ビ秒"],
  ["vibrato_count", "ビ回"], ["vibrato_type_code", "ビタ"],
];
// 曲別最高点(mode=best)だけ、日付の右に「回数」(過去に歌った回数。最大2桁)を足す。歌唱履歴の表は、変えない。
const HEADER_CONFIG_PC_BEST = [HEADER_CONFIG_PC[0], ["sing_count", "回数"], ...HEADER_CONFIG_PC.slice(1)];

const PC_NUM_SLOT_WIDTH = {
  sing_count: 3,
  base_score: 6.4, bonus_score: 4.4, chart_total: 3,
  pitch: 3, stability: 3, expressive: 3,
  rhythm: 3, vibrato_longtone: 3, emphasis: 3,
  shakuri_count: 2, kobushi_count: 2, fall_count: 2,
  longtone_skill: 2, vibrato_skill: 2,
  vibrato_seconds: 3.4, vibrato_count: 3,
};

const SP_NUM_SLOT_WIDTH = {
  base_score: 6.4, bonus_score: 6.4, bonus_type_short: 6.4,
  chart_total: 3, vibrato_longtone: 3, rhythm: 3,
  pitch: 3, stability: 3, expressive: 3,
  emphasis: 3, kobushi_count: 3, longtone_skill: 3,
  shakuri_count: 2, fall_count: 2, vibrato_skill: 2,
  vibrato_seconds: 3.4, vibrato_count: 3.4, vibrato_type_label: 3.4,
};

// header table と body table は、列幅(colgroup)を共有して、列の幅を完全にそろえる
const PC_COL_WIDTHS = [
  "5.5%", "7.0%", "23.0%", "6.5%", "6.5%", "4.5%", "3.5%", "3.5%", "3.5%", "3.5%", "3.5%", "3.5%",
  "3.5%", "3.5%", "2.5%", "2.5%", "2.5%", "2.5%", "2.5%", "3.5%", "3.5%", "3.5%",
];
// 日付の右に回数(3.5%。ビ回・ビタと同じ)を足し、曲名/歌手名(23.0%)から、その分(3.5%)を削る
const PC_COL_WIDTHS_BEST = [PC_COL_WIDTHS[0], PC_COL_WIDTHS[1], "3.5%", "19.5%", ...PC_COL_WIDTHS.slice(3)];
const SP_COL_WIDTHS = ["39%", "14%", "13%", "7%", "7%", "7%", "6%", "7%"];

const PAGE_SIZE = 50;

// ---------- 小さな部品 ----------
const isNa = (v) => v === null || v === undefined || (typeof v === "number" && Number.isNaN(v));

/** Python の html.escape と同じ */
function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
}
const esc = (v) => (isNa(v) ? "" : escHtml(v));

/** Python の urllib.parse.urlencode と同じ形(空白は +、! ' ( ) * は %XX) */
function urlencode(obj) {
  const enc = (s) => encodeURIComponent(String(s)).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase()).replace(/%20/g, "+");
  return Object.entries(obj).map(([k, v]) => enc(k) + "=" + enc(v)).join("&");
}

function anchor(href, text, cls, target = "_self") {
  let s = '<a href="' + href + '" target="' + target + '"';
  if (cls) s += ' class="' + cls + '"';
  return s + ">" + text + "</a>";
}

function fmt(v, digits) {
  if (isNa(v)) return "";
  if (digits !== undefined) return Number(v).toFixed(digits);
  const f = Number(v);
  if (Number.isNaN(f)) return String(v);
  return Number.isInteger(f) ? String(f) : String(f);
}

const numSlot = (value, width) => '<span class="num-slot" style="width:' + String(width) + 'ch">' + value + "</span>";
const colgroup = (widths) => "<colgroup>" + widths.map((w) => '<col style="width:' + w + '">').join("") + "</colgroup>";

function scoreColor(score, bonus) {
  if (isNa(score)) return "#FFFFFF";
  const b = isNa(bonus) ? null : Number(bonus);
  if (score >= 100 && b !== null && Math.abs(b) < 0.0005) {
    return "linear-gradient(135deg, #fff8ba 0%, #ffe66d 24%, #ffd034 48%, #c99700 72%, #fff0a0 100%)";
  }
  if (score >= 100) return "#FFF650";
  if (score >= 99) return "#FFFFAC";
  if (score >= 98) return "#CCFFCD";
  if (score >= 95) return "#A9FFFE";
  if (score >= 90) return "#CFCEFF";
  if (score >= 85) return "#FCBCFA";
  if (score >= 80) return "#FDCCDC";
  return "#FFFFFF";
}

// ---------- データ(公式APIから集めた保管庫 → 表の1行) ----------
const num = (v) => (v === "" || v === null || v === undefined ? NaN : Number(v));

/** 保管庫の1件 → 表の1行(app.py の normalize と table_data.py の変換と同じ) */
function toRow(d) {
  const dt = d.scoringDateTime || "";
  const code = VIB_TYPE[d.vibratoType ?? "N"] ?? 0;
  const bonusType = BONUS_TYPE[String(d.bonusType ?? "")] ?? (d.bonusTypeText ?? "");
  const r = {
    score_id: String(d.scoringDxgId).replace(/\.0$/, ""),
    request_no: d.requestNo ?? "",
    song_name: d.contentsName ?? "",
    artist_name: d.artistName ?? "",
    play_datetime: dt,
    play_dt: dt,
    play_date: dt.length >= 10 ? dt.slice(2, 10) : "",
    total_score: num(d.totalPoint),
    pitch: num(d.radarChartPitch),
    stability: num(d.radarChartStability),
    expressive: num(d.radarChartExpressive),
    rhythm: num(d.radarChartRhythm),
    vibrato_longtone: num(d.radarChartVibratoLongtone),
    vibrato_count: num(d.vibratoCount),
    vibrato_skill: num(d.vibratoSkill),
    vibrato_seconds: num(d.vibratoTotalSecond),
    vibrato_type_code: code,
    kobushi_count: num(d.kobushiCount),
    shakuri_count: num(d.shakuriCount),
    fall_count: num(d.fallCount),
    emphasis: num(d.intonation),
    bonus_score: num(d.bonusPoint),
    longtone_skill: num(d.longtoneSkill),
    rhythm_timing: num(d.timing),
  };
  r.base_score = r.total_score - r.bonus_score;
  r.chart_total = r.pitch + r.stability + r.expressive + r.rhythm + r.vibrato_longtone;
  r.bonus_type = bonusType;
  r.bonus_type_short = BONUS_SHORT_MAP[bonusType] ?? bonusType;
  r.vibrato_type_label = VIBRATO_TYPE_MAP[code] ?? "";
  return r;
}

/** 新しい順(同じ日時は、保管庫の順のまま) */
function toRows(records) {
  return records.map(toRow).sort((a, b) => (a.play_dt < b.play_dt ? 1 : a.play_dt > b.play_dt ? -1 : 0));
}

/** 曲別最高点: 同じ曲名・歌手名ごとに、最高点の1件にまとめる。回数 = まとめる前の件数 */
function bestRows(rows) {
  const groups = new Map();
  for (const r of rows) {
    const k = r.song_name + "\u0001" + r.artist_name;
    let g = groups.get(k);
    if (!g) groups.set(k, (g = { key: [r.song_name, r.artist_name], best: null, n: 0 }));
    g.n++;
    if (!isNa(r.total_score) && (g.best === null || r.total_score > g.best.total_score)) g.best = r;   // 同点は、新しいほう(先に出てきた1件)
  }
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  return [...groups.values()]
    .filter((g) => g.best)
    .sort((a, b) => cmp(a.key[0], b.key[0]) || cmp(a.key[1], b.key[1]))
    .map((g) => ({ ...g.best, sing_count: g.n }));
}

/** 並べ替え。空(NaN)は、昇順・降順のどちらでも最後。文字の列は、最初のクリック(desc)で、A→Z */
function sortRows(rows, col, dir) {
  if (!rows.length || !(col in rows[0])) return rows;
  const textCols = new Set(["song_name", "artist_name", "vibrato_type_code"]);
  const asc = textCols.has(col) ? dir === "desc" : dir === "asc";
  return [...rows].sort((a, b) => {
    const x = a[col], y = b[col];
    const nx = isNa(x), ny = isNa(y);
    if (nx && ny) return 0;
    if (nx) return 1;
    if (ny) return -1;
    const c = x < y ? -1 : x > y ? 1 : 0;
    return asc ? c : -c;
  });
}

// ---------- アドレスの条件 ----------
// 画面の名前: history(歌唱履歴) / best(曲別最高点) / stats(その他集計)。
// アドレスは、?mode=best の形に加えて、短い別名 ?best ・ ?stats ・ ?history でも指定できる(他の条件とも併用できる: ?best&page=2)。
// 古い名前 others(その他集計の、もとの名前)・statistics も、別名として、残している(以前のブックマーク・共有のアドレスが、そのまま開く)。
const MODES = ["history", "best", "stats"];
const MODE_ALIASES = { others: "stats", statistics: "stats" };
function readMode(q) {
  const norm = (m) => (MODES.includes(m) ? m : MODE_ALIASES[m] ?? null);
  const explicit = q.get("mode");
  if (explicit) return norm(explicit) ?? "history";
  for (const [k, v] of q) if (v === "" && norm(k)) return norm(k);     // ?best など(値の無い名前)
  return "history";
}

function readState() {
  const q = new URLSearchParams(location.search);
  const g = (k) => q.get(k) || "";
  const st = {
    mode: readMode(q),
    date: g("date"), song: g("song"), artist: g("artist"), search: g("search"),
    sortCol: g("sort_col"), sortDir: g("sort_dir"),
    page: parseInt(g("page") || "1", 10),
  };
  if (Number.isNaN(st.page)) st.page = 1;
  if (!st.sortCol) {
    if (st.mode === "best") { st.sortCol = "total_score"; st.sortDir = "desc"; }
    else { st.sortCol = "play_dt"; st.sortDir = "desc"; }
  }
  return st;
}

function sortHref(colKey, st) {
  let nextDir = "desc";
  if (colKey === st.sortCol) nextDir = st.sortDir === "desc" ? "asc" : "desc";
  const p = { sort_col: colKey, sort_dir: nextDir, mode: st.mode };
  if (st.date) p.date = st.date;
  if (st.song) p.song = st.song;
  if (st.artist) p.artist = st.artist;
  if (st.search) p.search = st.search;
  return "?" + urlencode(p);
}

// ---------- スマホ版の表 ----------
function renderSpHeader(st) {
  const cells = HEADER_CONFIG_SP.map((col, idx) => {
    const links = col.items.map(([key, label], i) => {
      const href = sortHref(key, st);
      const active = key === st.sortCol ? (st.sortDir === "desc" ? "active-desc" : "active-asc") : "";
      const linkCls = ("sort-link " + active).trim();
      if (idx === 0 && i === 0) {
        let cntLabel = "";
        if (st.mode === "best") {      // 曲別最高点だけ: 日付の右に「回数」(日付の幅を詰めて、その分にする。列の幅は、変えない)
          const cntActive = st.sortCol === "sing_count" ? (st.sortDir === "desc" ? "active-desc" : "active-asc") : "";
          cntLabel = anchor(sortHref("sing_count", st), "回数", ("sort-link sp-cnt-label " + cntActive).trim());
        }
        return '<div class="sp-nodate-header"><div class="sp-no-label">No.</div>' + anchor(href, label, (linkCls + " sp-date-label").trim()) + cntLabel + "</div>";
      }
      return anchor(href, label, linkCls);
    });
    return '<th class="col-header ' + col.align + '-align"><div class="header-container">' + links.join("") + "</div></th>";
  });
  return '<table class="dxg-table sp-header-table">' + colgroup(SP_COL_WIDTHS) + "<thead><tr>" + cells.join("") + "</tr></thead></table>";
}

function renderSpBody(rows, st, offset) {
  const parts = ['<table class="dxg-table sp-body-table">' + colgroup(SP_COL_WIDTHS) + "<tbody>"];
  if (!rows.length) {
    parts.push('<tr class="empty-row"><td colspan="' + SP_COL_WIDTHS.length + '" class="empty-cell">該当する曲はありません</td></tr>');
  } else {
    rows.forEach((r, i) => {
      const bg = scoreColor(r.total_score, r.bonus_score);
      const dVal = r.play_date, sVal = r.song_name, aVal = r.artist_name;
      const dateHref = dVal ? "?" + urlencode({ date: dVal, sort_col: st.sortCol, sort_dir: st.sortDir, mode: "history", search: st.search }) : "#";
      const songHref = sVal ? "?" + urlencode({ song: sVal, artist: aVal, sort_col: st.sortCol, sort_dir: st.sortDir, mode: "history", search: st.search }) : "#";
      // 絞り込み条件と一致する日付/曲名はリンク化しない
      const dateLink = st.date === dVal
        ? '<span class="date-plain sp-date-val">' + esc(dVal) + "</span>"
        : anchor(dateHref, esc(dVal), "date-text sp-date-val");
      const songLink = st.song === sVal && st.artist === aVal
        ? '<span class="song-plain clip song-nolink">' + esc(sVal) + "</span>"
        : anchor(songHref, esc(sVal), "clip song");
      const cntCell = st.mode === "best" ? '<span class="sp-cnt-val">' + fmt(r.sing_count) + "</span>" : "";   // 曲別最高点だけ
      const W = SP_NUM_SLOT_WIDTH;
      const row1 =
        '<tr class="record-top">'
        + '<td class="meta-cell"><div class="sp-nodate-row"><span class="sp-no-num">' + (offset + i + 1) + "</span>" + dateLink + cntCell + "</div></td>"
        + '<td rowspan="3" class="score-cell" data-sid="' + esc(r.score_id) + '" style="background:' + bg + ';">' + fmt(r.total_score, 3) + "</td>"
        + "<td>" + numSlot(fmt(r.base_score, 3), W.base_score) + "</td>"
        + "<td>" + numSlot(fmt(r.chart_total), W.chart_total) + "</td>"
        + "<td>" + numSlot(fmt(r.pitch), W.pitch) + "</td>"
        + "<td>" + numSlot(fmt(r.emphasis), W.emphasis) + "</td>"
        + "<td>" + numSlot(fmt(r.shakuri_count), W.shakuri_count) + "</td>"
        + "<td>" + numSlot(fmt(r.vibrato_seconds, 1), W.vibrato_seconds) + "</td>"
        + "</tr>";
      const row2 =
        "<tr>"
        + '<td class="meta-cell"><div class="sp-nodate-row"><div class="sp-song-val">' + songLink + "</div></div></td>"
        + "<td>" + numSlot(fmt(r.bonus_score, 3), W.bonus_score) + "</td>"
        + "<td>" + numSlot(fmt(r.vibrato_longtone), W.vibrato_longtone) + "</td>"
        + "<td>" + numSlot(fmt(r.stability), W.stability) + "</td>"
        + "<td>" + numSlot(fmt(r.kobushi_count), W.kobushi_count) + "</td>"
        + "<td>" + numSlot(fmt(r.fall_count), W.fall_count) + "</td>"
        + "<td>" + numSlot(fmt(r.vibrato_count), W.vibrato_count) + "</td>"
        + "</tr>";
      const row3 =
        '<tr class="record-bottom">'
        + '<td class="meta-cell"><div class="sp-nodate-row"><div class="sp-artist-val clip artist">' + esc(aVal) + "</div></div></td>"
        + "<td>" + numSlot(esc(r.bonus_type_short), W.bonus_type_short) + "</td>"
        + "<td>" + numSlot(fmt(r.rhythm), W.rhythm) + "</td>"
        + "<td>" + numSlot(fmt(r.expressive), W.expressive) + "</td>"
        + "<td>" + numSlot(fmt(r.longtone_skill), W.longtone_skill) + "</td>"
        + "<td>" + numSlot(fmt(r.vibrato_skill), W.vibrato_skill) + "</td>"
        + "<td>" + numSlot(esc(r.vibrato_type_label), W.vibrato_type_label) + "</td>"
        + "</tr>";
      parts.push(row1 + row2 + row3);
    });
  }
  parts.push("</tbody></table>");
  return parts.join("");
}

// ---------- PC版の表 ----------
function renderPcHeader(st) {
  const cells = ['<th class="no-col pc-th-first">No.</th>'];
  for (const [key, label] of st.mode === "best" ? HEADER_CONFIG_PC_BEST : HEADER_CONFIG_PC) {
    const href = sortHref(key, st);
    const active = key === st.sortCol ? (st.sortDir === "desc" ? "active-desc" : "active-asc") : "";
    const linkCls = ("sort-link " + active).trim();
    const w = key === "play_dt" ? "pc-th-date" : key === "song_name" ? "pc-th-song" : "pc-th-normal";
    cells.push('<th class="' + w + '">' + anchor(href, label, linkCls) + "</th>");
  }
  return '<table class="dxg-table pc-header-table">' + colgroup(st.mode === "best" ? PC_COL_WIDTHS_BEST : PC_COL_WIDTHS) + "<thead><tr>" + cells.join("") + "</tr></thead></table>";
}

function renderPcBody(rows, st, offset) {
  const widths = st.mode === "best" ? PC_COL_WIDTHS_BEST : PC_COL_WIDTHS;
  const parts = ['<table class="dxg-table pc-body-table">' + colgroup(widths) + "<tbody>"];
  const tdNum = (key, value) => {
    const w = PC_NUM_SLOT_WIDTH[key];
    return w === undefined ? "<td>" + value + "</td>" : "<td>" + numSlot(value, w) + "</td>";
  };
  if (!rows.length) {
    parts.push('<tr class="empty-row"><td colspan="' + widths.length + '" class="empty-cell">該当する曲はありません</td></tr>');
  } else {
    rows.forEach((r, i) => {
      const bg = scoreColor(r.total_score, r.bonus_score);
      const dVal = r.play_date, sVal = r.song_name, aVal = r.artist_name;
      const dateHref = dVal ? "?" + urlencode({ date: dVal, sort_col: st.sortCol, sort_dir: st.sortDir, mode: "history", search: st.search }) : "#";
      const songHref = sVal ? "?" + urlencode({ song: sVal, artist: aVal, sort_col: st.sortCol, sort_dir: st.sortDir, mode: "history", search: st.search }) : "#";
      const dateLink = st.date === dVal ? '<span class="date-plain">' + esc(dVal) + "</span>" : anchor(dateHref, esc(dVal), "date-text");
      const songLink = st.song === sVal && st.artist === aVal ? '<span class="song-plain">' + esc(sVal) + "</span>" : anchor(songHref, esc(sVal), "song-pc");
      const cntTd = st.mode === "best" ? tdNum("sing_count", fmt(r.sing_count)) : "";   // 曲別最高点だけ。他の数値の列(ビ回など)と同じ作り
      parts.push(
        "<tr>"
        + "<td>" + (offset + i + 1) + "</td>"
        + "<td>" + dateLink + "</td>"
        + cntTd
        + '<td class="meta-cell-pc pc-txt-cell">' + songLink + ' <span class="artist-pc">/ ' + esc(aVal) + "</span></td>"
        + '<td class="score-cell-pc" data-sid="' + esc(r.score_id) + '" style="background:' + bg + ';">' + fmt(r.total_score, 3) + "</td>"
        + tdNum("base_score", fmt(r.base_score, 3))
        + tdNum("bonus_score", fmt(r.bonus_score, 3))
        + "<td>" + esc(r.bonus_type_short) + "</td>"
        + tdNum("chart_total", fmt(r.chart_total))
        + tdNum("pitch", fmt(r.pitch))
        + tdNum("stability", fmt(r.stability))
        + tdNum("expressive", fmt(r.expressive))
        + tdNum("rhythm", fmt(r.rhythm))
        + tdNum("vibrato_longtone", fmt(r.vibrato_longtone))
        + tdNum("emphasis", fmt(r.emphasis))
        + tdNum("shakuri_count", fmt(r.shakuri_count))
        + tdNum("kobushi_count", fmt(r.kobushi_count))
        + tdNum("fall_count", fmt(r.fall_count))
        + tdNum("longtone_skill", fmt(r.longtone_skill))
        + tdNum("vibrato_skill", fmt(r.vibrato_skill))
        + tdNum("vibrato_seconds", fmt(r.vibrato_seconds, 1))
        + tdNum("vibrato_count", fmt(r.vibrato_count))
        + "<td>" + esc(r.vibrato_type_label) + "</td>"
        + "</tr>"
      );
    });
  }
  parts.push("</tbody></table>");
  return parts.join("");
}

// ---------- ページ送り(「<< < 3 4 5 6 7 > >>」。数字は最大5つの窓) ----------
function renderPager(page, totalPages, st) {
  if (totalPages <= 1) return '<div class="pager-space"></div>';          // ページ送りが出ないときも、表の下に、少し余白を置く
  const base = {};
  for (const [k, v] of [["mode", st.mode], ["sort_col", st.sortCol], ["sort_dir", st.sortDir], ["date", st.date], ["song", st.song], ["artist", st.artist], ["search", st.search]]) if (v) base[k] = v;
  const href = (n) => { const p = { ...base }; if (n > 1) p.page = n; return "?" + urlencode(p); };
  const items = [];
  if (page > 1) items.push(anchor(href(1), "&lt;&lt;"), anchor(href(page - 1), "&lt;"));
  let first, last;
  if (totalPages <= 5) { first = 1; last = totalPages; }
  else { first = Math.min(Math.max(1, page - 2), totalPages - 4); last = first + 4; }
  for (let n = first; n <= last; n++) items.push(n === page ? "<strong>" + n + "</strong>" : anchor(href(n), String(n)));
  if (page < totalPages) items.push(anchor(href(page + 1), "&gt;"), anchor(href(totalPages), "&gt;&gt;"));
  return '<div class="pager">' + items.join("") + "</div>";
}

// ---------- 上のナビ(タイトル・検索・タブ) ----------
const SEARCH_SRCDOC = `
<!DOCTYPE html>
<html><head><style>
  body { margin: 0; padding: 0; background: transparent; font-family: sans-serif; }
  form { margin: 0; display: flex; }
  input {
    width: 100%; height: 32px;
    padding: 7px 12px 6px 30px;
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
<\/script>
</head>
<body>
  <form onsubmit='submitSearch(event, this)'>
    <input type='text' name='search' value='__KW__' placeholder='曲名 or 歌手名'>
  </form>
</body></html>
`;

const SEARCH_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>';
const MENU_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>';

function renderNav(st) {
  const srcdoc = escHtml(SEARCH_SRCDOC.replace("__KW__", escHtml(st.search)));
  const act = (m) => (st.mode === m ? "active" : "");
  const tabHist = anchor("./", "歌唱履歴", act("history"));          // 歌唱履歴は、既定の画面(アドレスの条件なし)
  const tabBest = anchor("?best", "曲別最高点", act("best"));
  const tabOther = anchor("?stats", "その他集計", act("stats"));
  const showSearch = st.mode !== "stats";        // 「その他集計」には、検索する対象が無いので、検索欄(PC・スマホとも)を出さない
  const searchChecked = st.search ? 'checked="checked"' : "";
  return (
    '<div class="custom-nav">'
    + '<div class="nav-brand">精密集計DX-G</div>'
    + '<div class="nav-tabs">'
    + (showSearch ? '<div class="pc-search-form"><iframe srcdoc="' + srcdoc + '" style="width: 220px; height: 32px; border: none; overflow: hidden;" scrolling="no" frameborder="0"></iframe></div>' : "")
    + tabHist + tabBest + tabOther
    + "</div>"
    + '<div class="nav-sp-icons">'
    + (showSearch ? '<label for="search-toggle" class="icon-label" style="display:flex; align-items:center; padding: 6px 8px;">' + SEARCH_SVG + "</label>" : "")
    + '<label for="menu-toggle" class="icon-label" style="display:flex; align-items:center; padding: 6px 8px;">' + MENU_SVG + "</label>"
    + "</div>"
    + "</div>"
    + '<input type="checkbox" id="search-toggle" class="hidden-toggle" ' + searchChecked + ">"
    + (showSearch ? '<div class="sp-search-bar"><div class="sp-panel"><div class="sp-panel-inner"><iframe srcdoc="' + srcdoc + '" style="width: 100%; height: 32px; border: none; overflow: hidden; display: block;" scrolling="no" frameborder="0"></iframe></div></div></div>' : "")
    + '<input type="checkbox" id="menu-toggle" class="hidden-toggle">'
    + '<div class="sp-dropdown"><div class="sp-panel"><div class="sp-panel-inner">'
    + tabHist + tabBest + tabOther
    + "</div></div></div>"
  );
}

// ---------- 1ページ分の組み立て ----------
function buildTables(allRows, st) {
  let view = st.mode === "best" ? bestRows(allRows) : allRows;
  if (st.date) view = view.filter((r) => r.play_date === st.date);
  if (st.song && st.artist) view = view.filter((r) => r.song_name === st.song && r.artist_name === st.artist);
  if (st.search) {
    const kw = st.search.toLowerCase();
    view = view.filter((r) => r.song_name.toLowerCase().includes(kw) || r.artist_name.toLowerCase().includes(kw));
  }
  view = sortRows(view, st.sortCol, st.sortDir);

  const totalRows = view.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / PAGE_SIZE));
  const page = Math.min(Math.max(st.page, 1), totalPages);
  const offset = (page - 1) * PAGE_SIZE;
  const pageView = view.slice(offset, offset + PAGE_SIZE);

  if (!view.length) {
    const empty = '<div class="empty-state">該当する曲はありません</div>';
    return '<div class="dxg-scroll-wrapper"><div class="view-pc">' + empty + '</div><div class="view-sp">' + empty + "</div></div>";
  }
  return (
    '<div class="dxg-scroll-wrapper">'
    + '<div class="view-pc"><div class="pc-table-wrapper">' + renderPcHeader(st) + renderPcBody(pageView, st, offset) + "</div></div>"
    + '<div class="view-sp">' + renderSpHeader(st) + renderSpBody(pageView, st, offset) + "</div>"
    + "</div>"
    + renderPager(page, totalPages, st)
  );
}

// ---------- 起動 ----------
// 版: index.html が、version.json から読んだ版を付けて、この viewer.js を読み込む(viewer.js?v=...)。その版を、読み込む先(detail.js など)のアドレスにも、そのまま付ける。
// ファイルのアドレスに版を付けると、10分のキャッシュで、古いものが残らない。版が無いとき(ローカル・Streamlit版の試験)は、空のまま
const V = new URL(import.meta.url).search;

async function loadText(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(url + ": " + r.status);
  return r.text();
}

async function main() {
  const app = document.getElementById("app");
  const st = readState();

  // CSS は <style> として差し込む(表の画像保存 tablesave.js が、画面の <style> から、表の見た目を読み取るため)
  const style = document.createElement("style");
  style.textContent = await loadText("viewer.css");
  document.head.appendChild(style);
  const detailCss = document.createElement("link");
  detailCss.rel = "stylesheet"; detailCss.href = "detail.css" + V;
  document.head.appendChild(detailCss);

  const text = await loadText("dataset/history.jsonl");
  const records = text.split("\n").filter(Boolean).map((l) => JSON.parse(l));

  if (st.mode === "stats") {
    const { renderOthers, initOthers } = await import("./charts.js" + V);
    app.innerHTML = renderNav(st) + renderOthers(toRows(records));
    initOthers();
  } else {
    app.innerHTML = renderNav(st) + buildTables(toRows(records), st);
  }
  document.title = "DX-G Viewer";

  // 表の画像保存(右クリック・長押し)
  import("./tablesave.js" + V).then((m) => m.initTableSave()).catch((e) => console.error("tablesave", e));

  // 点数をクリックすると、採点結果画面が開く
  let detail = null;
  document.addEventListener("click", async (e) => {
    const td = e.target.closest && e.target.closest("td[data-sid]");
    if (!td || !td.dataset.sid) return;
    detail = detail || (await import("./detail.js" + V));
    const rec = records.find((r) => r.scoringDxgId === td.dataset.sid);
    if (rec) detail.openDetail(rec, records);
  });
}

main().catch((e) => {
  console.error(e);
  document.getElementById("app").textContent = "読み込みに失敗しました: " + e.message;
});
