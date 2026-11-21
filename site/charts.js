// 「その他集計」(?mode=others): 最高点別の曲数(積み上げ棒グラフ)と、ビブラートタイプの割合(円グラフ)。
// Streamlit 版の scripts/others_charts.py と app.py の render_others の移植。各区画は、見出し・グラフ・説明文を、1枚のSVGにまとめる。
//  - 画面では、そのまま表示する(棒が下から伸びる/円の扇が広がる動きは、viewer.css のCSSで付ける)
//  - グラフが現れたら、同じSVGから、PNG画像を作り、ほぼ透明にして、真上に重ねる(右クリック・長押しで、区画ごとに保存できる)

const STACK_COLORS = ["#7cb5ec", "#434348", "#90ed7d", "#f7a35c", "#8085e9"];
const STACK_LABELS = [".0～.2", ".2～.4", ".4～.6", ".6～.8", ".8～"];
const PIE_COLORS = ["#7cb5ec", "#434348", "#90ed7d", "#f7a35c", "#8085e9", "#f15c80", "#e4d354", "#2b908f", "#f45b5b", "#91e8e1"];
const FONT = "Arial, 'Yu Gothic', sans-serif";          // 表と同じフォント
const TITLE_H = 40;                                      // 見出しの高さ
const LABEL_GAP = 24;                                    // PC用の円グラフ: ラベルの右端と、円の左端の間(線を通す幅)
const EDGE = 8;                                          // PC用の円グラフ: 区画の左端〜ラベル、円の右端〜区画の右端、の余白(棒グラフの右の余白 R=8 と同じ)
const HALF = 0.56;                                       // ラベルの文字の、上下の広がり(文字の中心から、上端・下端まで = 文字サイズ × 0.56)
const FIT = 0.975;                                       // ラベルの幅の見積もりの余裕
const BAR_T = 26, BAR_B = 68;                            // 棒グラフの、グラフ本体の上の余白(=一番上の目盛り線の位置)と、下の余白
const NOTE_LH = 19;                                      // 説明文の行の高さ
const FAN_ATTACH = 200.0;                                // 「下広がり」: 円の下端に近い扇(C-2)のひげが、扇から出る位置の角度
const AXIS_TICK_DY = 15;                                 // 棒グラフのx軸の数字の文字の下の線は、0の線より 15 下
const FAN_MIN_DEPTH = 0.6;                               // 「下広がり」にする扇の、深さの下限

const isNa = (v) => v === null || v === undefined || (typeof v === "number" && Number.isNaN(v));

/** Python の html.escape と同じ */
const escape = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");

/** 小数2桁(末尾の0と、小数点は、落とす) */
function f(v) {
  return Number(v).toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function section(W, title, body, bodyH, notes, bodyTop = 0.0, centerNotes = false) {
  const shift = TITLE_H - bodyTop;
  const notesY = TITLE_H + (bodyH - bodyTop) + 14;
  const H = notesY + NOTE_LH * notes.length + 6;
  const o = [
    `<svg class="others-chart" viewBox="0 0 ${W} ${f(H)}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="${FONT}" font-weight="bold" role="img" aria-label="${escape(title)}">`,
    `<rect width="${W}" height="${f(H)}" fill="#fff"/>`,
    '<rect x="0" y="6" width="4" height="26" fill="#6f6fd8"/>',
    `<text x="14" y="25" font-size="16" fill="#333">${escape(title)}</text>`,
    `<line x1="0" y1="${TITLE_H - 2}" x2="${W}" y2="${TITLE_H - 2}" stroke="#ccc"/>`,
    `<g transform="translate(0 ${f(shift)})">${body}</g>`,
  ];
  const texts = notes.map((n) => `・${n}`);
  // 説明文は、全体を「ひとかたまり」として、区画の左右中央に置く(各行は、左揃えのまま)。centerNotes=false のときは、左端
  const nx = centerNotes && texts.length ? (W - Math.max(...texts.map((t) => textW(t, 13, 1.0)))) / 2 : 4;
  texts.forEach((t, i) => {
    o.push(`<text x="${f(nx)}" y="${f(notesY + NOTE_LH * i + 13)}" font-size="13" font-weight="normal" fill="#333">${escape(t)}</text>`);
  });
  o.push("</svg>");
  return o.join("");
}

/** 最高点別の曲数(積み上げ棒グラフ)。bestScores: 曲ごとの [最高点, その記録のボーナス点]。
 *  列は、lo〜99, 100, 100+ の12列を固定で出す(該当する曲が0でも、列は残して「0」と出す) */
export function bestScoresSection(bestScores, { lo = 90, W = 440, fs = 11, bodyH = null, centerNotes = false } = {}) {
  const cats = [];
  for (let n = lo; n < 100; n++) cats.push(String(n));
  cats.push("100", "100+");
  const counts = Object.fromEntries(cats.map((c) => [c, [0, 0, 0, 0, 0]]));
  for (const [score, bonus] of bestScores) {
    if (score < lo) continue;
    if (score >= 100) { counts[Math.abs(bonus) < 0.0005 ? "100+" : "100"][0] += 1; continue; }
    const ip = Math.floor(score + 1e-9);
    counts[String(ip)][Math.min(Math.trunc((score - ip) * 5 + 1e-9), 4)] += 1;
  }
  const totals = cats.map((c) => counts[c].reduce((a, b) => a + b, 0));
  const ymax = Math.max(150, Math.ceil(Math.max(...totals, 1) / 25.0) * 25);

  const wide = W >= 450;
  const H = bodyH || (wide ? 214 : 280);
  const L = wide ? 52 : 54, R = 8, T = BAR_T, B = BAR_B;
  const pw = W - L - R, ph = H - T - B;
  const Y = (v) => T + ph - (v / ymax) * ph;
  const n = cats.length;
  const slot = pw / n;
  const bw = slot * (wide ? 0.52 : 0.6);
  const o = [];
  for (let v = 0; v <= ymax; v += 25) {
    o.push(`<line x1="${L}" y1="${f(Y(v))}" x2="${W - R}" y2="${f(Y(v))}" stroke="#e6e6e6"/>`);
    o.push(`<text x="${L - 8}" y="${f(Y(v) + 4)}" text-anchor="end" font-size="${fs}" fill="#666">${v}</text>`);
  }
  o.push(`<line x1="${L}" y1="${f(Y(0))}" x2="${W - R}" y2="${f(Y(0))}" stroke="#ccd6eb" stroke-width="1"/>`);
  o.push(`<text x="10" y="${f(T + ph / 2)}" font-size="${fs}" fill="#666" text-anchor="middle" transform="rotate(-90 10 ${f(T + ph / 2)})">曲数</text>`);
  cats.forEach((c, i) => {
    const x = L + slot * i + (slot - bw) / 2;
    let acc = 0;
    o.push(`<g class="ob" style="transform-origin:${f(x + bw / 2)}px ${f(Y(0))}px">`);
    for (let k = 0; k < 5; k++) {
      const cnt = counts[c][k];
      if (!cnt) continue;
      const y1 = Y(acc + cnt), y0 = Y(acc);
      o.push(`<rect x="${f(x)}" y="${f(y1)}" width="${f(bw)}" height="${f(y0 - y1)}" fill="${STACK_COLORS[k]}"><title>${escape(c)}点 ${STACK_LABELS[k]}: ${cnt}曲</title></rect>`);
      acc += cnt;
    }
    o.push("</g>");
    o.push(`<text class="ob-num" x="${f(L + slot * i + slot / 2)}" y="${f(Y(acc) - 6)}" text-anchor="middle" font-size="${fs + 1}" fill="#555">${acc}</text>`);   // 件数: 定位置で、ふわっと出る
    o.push(`<text x="${f(L + slot * i + slot / 2)}" y="${f(Y(0) + 15)}" text-anchor="middle" font-size="${fs}" fill="#666">${escape(c)}</text>`);
  });
  o.push(`<text x="${f(L + pw / 2)}" y="${f(Y(0) + 31)}" text-anchor="middle" font-size="${fs}" fill="#666">点数</text>`);
  // 凡例 (枠つき)
  const lw = STACK_LABELS.map((l) => l.length * (fs - 4) + 22);
  const totalW = lw.reduce((a, b) => a + b, 0) + 14 * 4 + 24;
  let x = W / 2 - totalW / 2;
  const yb = H - 14;
  o.push(`<rect x="${f(x)}" y="${yb - 13}" width="${f(totalW)}" height="24" fill="#fff" stroke="#ccc"/>`);
  x += 12;
  STACK_LABELS.forEach((lab, k) => {
    o.push(`<rect x="${f(x)}" y="${f(yb - 6.5)}" width="11" height="11" fill="${STACK_COLORS[k]}"/>`);
    o.push(`<text x="${f(x + 15)}" y="${f(yb - 1 + fs * 0.36)}" font-size="${fs}" fill="#333">${escape(lab)}</text>`);
    x += lw[k] + 14;
  });
  return section(W, "最高点別の曲数", o.join(""), H, ["最高点が何点の曲が何曲あるかを表しています", "ボーナス点が0点の100点を「100+」と表します"], 0.0, centerNotes);
}

/** 太字の文字列の、おおよその幅(単位は、描画の座標)。半角は文字ごとの係数、全角は fs */
function textW(s, fs, margin = 1.04) {
  let w = 0.0;
  for (const ch of s) {
    if (/[0-9]/.test(ch)) w += 0.57 * fs;
    else if (" .:".includes(ch)) w += 0.32 * fs;
    else if (ch === "-") w += 0.36 * fs;
    else if (ch === "%") w += 0.92 * fs;
    else if (ch.charCodeAt(0) < 128) w += (/[A-Z]/.test(ch) ? 0.74 : 0.62) * fs;
    else w += fs;
  }
  return w * margin;                                     // 見積もりの誤差の分の、余裕(既定は4%)
}

/** 各扇の、開始・終了の角度(0=真上、時計回り) */
function angles(items) {
  const total = items.reduce((a, [, c]) => a + c, 0) || 1;
  const out = [];
  let ang = 0.0;
  for (const [name, cnt] of items) {
    const span = (cnt / total) * 360.0;
    out.push({ name, pct: (cnt / total) * 100, a0: ang, a1: ang + span });
    ang += span;
  }
  return out;
}

/** PC用の円の半径。下端は、棒グラフの「0の線」に固定する。円の全体 + ひげ + ラベルが、棒グラフの「150の線」〜「0の線」の間に収まる、最大の大きさ */
function pieR(items, fs, bodyH) {
  const rMax = (bodyH - BAR_T - BAR_B) / 2;              // 円だけなら、150の線〜0の線の高さがいっぱい
  const bottom = bodyH - BAR_B;
  let r = rMax;
  while (r > 30) {
    const pts = angles(items);
    layoutLeft(pts, 0.0, bottom - r, r, fs, bottom);
    const topOk = Math.min(...pts.map((p) => p.ly)) - fs * HALF >= BAR_T;            // 一番上のラベルの文字の上端が、150の線の内側
    const bottomOk = Math.max(...pts.map((p) => p.ly)) + fs * HALF <= bottom + 0.01;   // 一番下のラベルの文字の下端が、0の線の内側
    if (topOk && bottomOk) return r;
    r -= 0.5;
  }
  return r;
}

/** PC用の円グラフ(ラベルを左の1列に並べる)の区画の幅を、ラベルの長さにぴったり合わせた値にする */
export function pieMinWidth(items, fs = 13, bodyH = 300) {
  const total = items.reduce((a, [, c]) => a + c, 0) || 1;
  const labelW = items.length ? Math.max(...items.map(([name, cnt]) => textW(`${name}: ${((cnt / total) * 100).toFixed(1)} %`, fs, FIT))) : 0;
  const r = pieR(items, fs, bodyH);
  return Math.ceil(2 * r + LABEL_GAP + 2 * EDGE + labelW);
}

/** PC用: ラベルの位置を決める(円の左の1列。線は、各扇の左側の弧につなぐ)。結果は、各 p の ex,ey,kx,ky,ly に入れる */
function layoutLeft(pts, cx, cy, r, fs, bottomY, fan = false) {
  for (const p of pts) {
    const lo = Math.max(p.a0, 180.0), hi = Math.min(p.a1, 360.0);
    const a = lo < hi ? (lo + hi) / 2 : p.a1 - Math.min(4.0, (p.a1 - p.a0) / 2);
    const s = Math.sin((a * Math.PI) / 180), c = Math.cos((a * Math.PI) / 180);
    p.ex = cx + r * s; p.ey = cy - r * c;
    p.kx = cx + (r + 9) * s; p.ky = cy - (r + 9) * c;
    p.ly = p.ky;
  }
  const order = [...pts].sort((p, q) => p.ly - q.ly);
  const pitch = fs + 6;
  order[0].ly = Math.max(order[0].ly, fs * 0.8 + 14);
  for (let k = 1; k < order.length; k++) order[k].ly = Math.max(order[k].ly, order[k - 1].ly + pitch);
  const over = order[order.length - 1].ly - (bottomY - fs * HALF);   // 最下段のラベルの文字の下端が、0の線(bottomY)を越えないようにする
  if (over > 0) for (const p of order) p.ly -= over;
  if (fan) {                                             // 「下広がり」: 円の下端に近い扇(C-2)だけ、ひげの長い線を、下がる斜めにする
    for (const p of pts) {
      const depth = (p.ky - cy) / r;                     // 0(円の中心と同じ高さ)〜1(円の下端)
      if (depth >= FAN_MIN_DEPTH) {
        const a = Math.min(Math.max(FAN_ATTACH, p.a0 + 1.0), p.a1 - 1.0);
        const s = Math.sin((a * Math.PI) / 180), c = Math.cos((a * Math.PI) / 180);
        p.ex = cx + r * s; p.ey = cy - r * c;
        p.kx = cx + (r + 9) * s; p.ky = cy - (r + 9) * c;
        p.ly = bottomY + AXIS_TICK_DY - fs * 0.36;
      } else if (depth > 0) {
        p.ly = p.ky;                                     // 円の中心より下で、浅いもの(C-3): 折れ曲がりから伸びる長い線を、水平にする
      }
    }
  }
}

function leftLabels(pts, cx, cy, r, fs, bottomY, xLab, fan = false) {
  const out = [];
  layoutLeft(pts, cx, cy, r, fs, bottomY, fan);
  for (const p of pts) {
    out.push(`<path d="M${f(p.ex)} ${f(p.ey)}L${f(p.kx)} ${f(p.ky)}L${f(xLab + 6)} ${f(p.ly)}" stroke="${p.col}" fill="none"/>`);
    out.push(`<text x="${f(xLab)}" y="${f(p.ly + fs * 0.36)}" text-anchor="end" font-size="${fs}" fill="#555">${escape(p.name)}: ${p.pct.toFixed(1)} %</text>`);
  }
  return out;
}

/** ビブラートタイプの割合(円グラフ)。items: [[表示名, 件数], ...] (多い順)。割合の表示は小数1桁 */
export function pieSection(items, { W = 420, fs = 12, r = null, labelsLeft = false, bodyH = null, centerNotes = false, fan = false } = {}) {
  const total = items.reduce((a, [, c]) => a + c, 0) || 1;
  const wide = W >= 450;
  let H, cx, cy, xLab;
  if (labelsLeft) {                                      // PC用: 円を右に寄せ、ラベルを左の1列に並べる
    H = bodyH || 300;
    r = r || pieR(items, fs, H);
    cx = W - EDGE - r;                                   // 円は、右の余白(EDGE)をあけて、右に寄せる
    xLab = cx - r - LABEL_GAP;                           // ラベルの右端
    cy = (H - BAR_B) - r;                                // 縦の位置: 円の下端が、棒グラフの「0の線」に合う
  } else {
    r = r || (wide ? 90 : 70);
    cx = W / 2; cy = wide ? 110 : r + 28;
    H = cy + r + 8;
  }
  const o = [];
  const C = Math.PI * r;                                 // マスクの円(半径 r/2)の円周
  const midId = `pm${W}`;
  o.push(`<defs><mask id="${midId}"><circle class="sweep" style="--c:${f(C)}px" cx="${f(cx)}" cy="${f(cy)}" r="${f(r / 2)}" fill="none" stroke="#fff" stroke-width="${f(r)}" stroke-dasharray="${f(C)}" stroke-dashoffset="0" transform="rotate(-90 ${f(cx)} ${f(cy)})"/></mask></defs><g mask="url(#${midId})">`);
  let ang = 0.0;                                         // 0 = 真上。時計回り
  const pts = [];
  items.forEach(([name, cnt], i) => {
    const span = (cnt / total) * 360.0;
    const a0 = ang, a1 = ang + span;
    const mid = (((a0 + a1) / 2) * Math.PI) / 180;
    const col = PIE_COLORS[i % PIE_COLORS.length];
    const x0 = cx + r * Math.sin((a0 * Math.PI) / 180), y0 = cy - r * Math.cos((a0 * Math.PI) / 180);
    const x1 = cx + r * Math.sin((a1 * Math.PI) / 180), y1 = cy - r * Math.cos((a1 * Math.PI) / 180);
    const tip = `<title>${escape(name)}: ${cnt}曲 (${((cnt / total) * 100).toFixed(1)}%)</title>`;
    if (span >= 359.99) {
      o.push(`<circle cx="${f(cx)}" cy="${f(cy)}" r="${r}" fill="${col}">${tip}</circle>`);
    } else {
      o.push(`<path d="M${f(cx)} ${f(cy)}L${f(x0)} ${f(y0)}A${r} ${r} 0 ${span > 180 ? 1 : 0} 1 ${f(x1)} ${f(y1)}Z" fill="${col}" stroke="#fff" stroke-width="1">${tip}</path>`);
    }
    pts.push({ name, pct: (cnt / total) * 100, col, sin: Math.sin(mid), cos: Math.cos(mid), a0, a1 });
    ang = a1;
  });
  o.push("</g>");
  o.push('<g class="fadein">');                          // ラベルと線は、扇が広がり終わるころに、ふわっと出す
  if (labelsLeft) {
    o.push(...leftLabels(pts, cx, cy, r, fs, cy + r, xLab, fan));
    o.push("</g>");
    return section(W, "ビブラートタイプ", o.join(""), H, ["直近200曲の上位5つとその他の割合を表しています"], 0.0, centerNotes);
  }
  // ラベルの置き方: 円の右側(時計回りで下半分に入る扇)は、扇の外側にそのまま置く。
  // 円の上端に集まる小さい扇(左上〜真上)のラベルは、円の左側に、縦に並べる。
  const pitch = fs + 5;
  const right = pts.filter((p) => p.sin >= 0);
  const left = pts.filter((p) => p.sin < 0);
  for (const p of right) p.ly = cy - (r + 18) * p.cos;
  right.sort((p, q) => p.ly - q.ly);
  for (let k = 1; k < right.length; k++) if (right[k].ly - right[k - 1].ly < pitch) right[k].ly = right[k - 1].ly + pitch;
  // 左側は、扇の中心の高さを基準にして、近いものを避けて並べる(下から上へ)
  for (const p of left) p.ly = cy - (r + 8) * p.cos;
  left.sort((p, q) => q.ly - p.ly);
  for (let k = 1; k < left.length; k++) if (left[k - 1].ly - left[k].ly < pitch) left[k].ly = left[k - 1].ly - pitch;
  // 左側の最上段が、円の上端(cy - r)より上へ出る分だけ、左側の全体を下へ寄せる(上へ出さない)
  const over = (cy - r - 4) - Math.min(...left.map((p) => p.ly), cy);
  if (over < 0) for (const p of left) p.ly -= over;
  const pad = wide ? 26 : 20;
  for (const [side, group] of [[1, right], [-1, left]]) {
    for (const p of group) {
      const ex = cx + r * p.sin, ey = cy - r * p.cos;
      const kx = cx + (r + 10) * p.sin, ky = cy - (r + 10) * p.cos;
      const lx = cx + side * (r + pad);
      o.push(`<path d="M${f(ex)} ${f(ey)}L${f(kx)} ${f(ky)}L${f(lx - side * 5)} ${f(p.ly)}" stroke="${p.col}" fill="none"/>`);
      o.push(`<text x="${f(lx)}" y="${f(p.ly + fs * 0.36)}" text-anchor="${side === 1 ? "start" : "end"}" font-size="${fs}" fill="#555">${escape(p.name)}: ${p.pct.toFixed(1)} %</text>`);
    }
  }
  o.push("</g>");
  const ys = pts.map((p) => p.ly);
  const top = Math.min(cy - r, ...ys.map((y) => y - fs));   // ラベルが、円の上へはみ出した分だけ、領域を広げる(通常は、ほぼ0)
  const bottom = Math.max(cy + r, ...ys.map((y) => y + fs));
  H = bottom + 8;
  return section(W, "ビブラートタイプ", o.join(""), H, ["直近200曲の上位5つとその他の割合を表しています"], Math.min(top, 0.0));
}

// ---------- 「その他集計」の画面(app.py の render_others) ----------
const VIBRATO_TYPE_MAP = { 0: "N", 1: "A-1", 2: "B-1", 3: "C-1", 4: "A-2", 5: "B-2", 6: "C-2", 7: "A-3", 8: "B-3", 9: "C-3", 10: "D", 11: "E", 12: "F", 13: "G", 14: "H" };
const PIE_NAMES = { 10: "上昇形", 11: "下降形", 12: "縮小形", 13: "拡張形", 14: "ひし形", 0: "ノンビブ形" };

/** rows: 表の行(viewer.js の toRows。新しい順) */
export function renderOthers(rows) {
  const d = rows.filter((r) => !isNa(r.total_score));
  // 曲ごとの最高点: 曲の識別は、曲番号(requestNo)。無ければ、曲名+歌手名。同点は、新しい1件
  const best = new Map();
  for (const r of d) {
    const key = String(r.request_no ?? "").length > 0 ? r.request_no : r.song_name + "\u0001" + r.artist_name;
    const cur = best.get(key);
    if (!cur || r.total_score > cur.total_score) best.set(key, r);
  }
  const bestScores = [...best.values()].map((r) => [r.total_score, isNa(r.bonus_score) ? 0.0 : r.bonus_score]);

  // ビブラートタイプの割合は、直近200曲から集計する
  const recent = [...d].sort((a, b) => (a.play_dt < b.play_dt ? 1 : a.play_dt > b.play_dt ? -1 : 0)).slice(0, 200);
  const counts = new Map();
  for (const r of recent) {
    const c = r.vibrato_type_code;
    const name = isNa(c) ? "不明" : (PIE_NAMES[c] ?? VIBRATO_TYPE_MAP[c] ?? String(c));
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  let items = [...counts.entries()].sort((a, b) => b[1] - a[1]);   // 多い順(同数は、先に出てきた順)
  const TOP_N = 5;                                       // 上位5つだけ出して、残りは「その他」にまとめる
  if (items.length > TOP_N + 1) items = [...items.slice(0, TOP_N), ["その他", items.slice(TOP_N).reduce((a, [, c]) => a + c, 0)]];

  const SEC_BODY_H = 340;   // PC版: 2つの区画の「グラフ本体」の高さ(同じにする→先頭の説明文の位置が、そろう)
  const BAR_W = 551;
  const PIE_W = pieMinWidth(items, 13, SEC_BODY_H);      // 円グラフの区画は、ラベルの長さにぴったり合わせた幅
  return (
    '<div class="others-wrap">'
    + '<div class="o-pc o-bar" style="flex: ' + BAR_W + ' 1 0">' + bestScoresSection(bestScores, { W: BAR_W, fs: 12, bodyH: SEC_BODY_H, centerNotes: true }) + '</div><div class="o-sp">' + bestScoresSection(bestScores, { W: 420, fs: 12 }) + "</div>"
    + '<div class="o-pc o-pie" style="flex: ' + PIE_W + ' 1 0">' + pieSection(items, { W: PIE_W, fs: 13, labelsLeft: true, bodyH: SEC_BODY_H, centerNotes: true, fan: true }) + '</div><div class="o-sp">' + pieSection(items) + "</div>"
    + "</div>"
  );
}

// ---------- 動きと、保存用の画像 ----------
// 動きが終わったら(約2秒後)、区画を、PNG画像に差し替える: 右クリックの「画像を保存」・スマホの長押しで、区画ごとに保存できる
async function toImage(svg) {
  try {
    const vb = svg.viewBox.baseVal, scale = 3;
    const clone = svg.cloneNode(true);                                  // 大きさを、数値で指定する(幅100%のままだと、画像として読み込むとき、既定の小さな大きさになる)
    clone.setAttribute("width", String(vb.width)); clone.setAttribute("height", String(vb.height));
    const xml = new XMLSerializer().serializeToString(clone);
    const url = URL.createObjectURL(new Blob([xml], { type: "image/svg+xml;charset=utf-8" }));
    const img = new Image(); img.src = url; await img.decode();
    const MX = 24, MY = 12;                                             // 保存する画像の、周囲の白い余白(左右24px・上下12px)。画面の表示では、この余白の分を、負の余白で打ち消して、見た目の大きさを変えない
    const c = document.createElement("canvas");
    c.width = Math.round((vb.width + 2 * MX) * scale); c.height = Math.round((vb.height + 2 * MY) * scale);
    const ctx = c.getContext("2d"); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, c.width, c.height); ctx.drawImage(img, MX * scale, MY * scale, vb.width * scale, vb.height * scale);
    const png = await new Promise((r) => c.toBlob(r, "image/png"));
    const out = new Image(); out.className = "others-img"; out.alt = svg.getAttribute("aria-label") || ""; out.src = URL.createObjectURL(png); await out.decode();
    // 表示の大きさは、割合(%)で指定する: 画面の拡大率(zoom)や、PC・スマホの幅の違いに、左右されない。
    // 画像の幅 = 元の幅 + 余白 2M なので、元の幅に対する割合で広げ、余白の分だけ、上下左右へ、負の余白で、はみ出させる
    // (縦の余白の割合も、親の「幅」に対する割合になる(CSSの決まり)ので、幅 vb.width を基準にそろえる)
    out.style.width = ((vb.width + 2 * MX) / vb.width * 100) + "%"; out.style.maxWidth = "none";
    out.style.marginLeft = (-MX / vb.width * 100) + "%"; out.style.marginTop = (-MY / vb.width * 100) + "%"; out.style.marginBottom = (-MY / vb.width * 100) + "%";
    // SVGは、そのまま残す(画像に差し替えると、文字や線のにじみ方が変わって、切り替わりが見えるため)。保存用の画像は、ほぼ透明にして、SVGの真上に重ねる
    const ovl = document.createElement("div"); ovl.className = "others-ovl"; ovl.appendChild(out);
    svg.parentNode.appendChild(ovl); URL.revokeObjectURL(url);
  } catch (e) { console.error("others: 画像への差し替えに失敗(SVGのまま表示を続ける)", e); }
}

/** グラフが画面に見えたら、動きを始める。保存用の画像は、動きの終わりを待たず、すぐ作って重ねる(完成形から作るので、動きの最中でも、完成した絵が保存される) */
export function initOthers() {
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("go"); io.unobserve(e.target); } }), { threshold: 0.3 });
  document.querySelectorAll(".others-chart:not([data-o])").forEach((el) => { el.dataset.o = "1"; io.observe(el); toImage(el); });
}
