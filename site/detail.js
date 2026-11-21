// 採点詳細パネル。保管庫(dataset/history.jsonl)の1件分のデータだけで、1枚のSVGを組み立て、PNG画像にして表示する。
//   - API呼び出しなし / 外部ライブラリなし / 外部フォントなし(SVGを画像化するとき、外部フォントは使えないため)
//   - 画像(<img>)として表示するので、右クリックの「画像をコピー/保存」、スマホの長押しの保存がそのまま使える
//   - 点数の数字・ビブラートの波形は、公式DAM★ともの画像の字形を、ベクトル(SVGパス)に変換した assets.js から描く
// ?v=__VER__ は、公開(GitHub Actions)のとき、commitの識別子に置き換わる(古いキャッシュが残らないように)。Streamlit版・ローカルでは、そのままで動く
import { ASSETS } from "./assets.js?v=__VER__";
import { VIBG } from "./vib_gif.js?v=__VER__";

const FONT = `Arial, 'Yu Gothic', sans-serif`;   // 自前の表(app.py)と同じ
const YEL = "#ffee33", WHITE = "#ffffff", BG = "#222222";

let uid = 0;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v, d = 0) => { const n = parseFloat(v); return Number.isFinite(n) ? n : d; };
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const f = (n) => (Math.round(n * 10) / 10).toString();

function T(x, y, txt, { size = 12, fill = WHITE, anchor = "start", stroke = "" } = {}) {
  const st = stroke ? ` stroke="${stroke}" stroke-width="3" paint-order="stroke" stroke-linejoin="round"` : "";
  return `<text x="${f(x)}" y="${f(y)}" font-size="${size}" fill="${fill}" text-anchor="${anchor}"${st}>${esc(txt)}</text>`;
}

// ---------- 文字幅の計測 (コメントの折り返し用) ----------
let _ctx = null;
function measure(txt, size) {
  _ctx ??= document.createElement("canvas").getContext("2d");
  _ctx.font = `bold ${size}px ${FONT}`;
  return _ctx.measureText(txt).width;
}
const NO_HEAD = "、。，．）」』】！？ー・ぁぃぅぇぉっゃゅょ)>＞〉》]"; // 行頭に来ないようにする文字 (簡易の禁則処理)
// 分析レポートの折り返し(ルール):
//   1) 文(。！？)の途中では改行しない。1文が1行に収まらないときだけ、文字単位で折り返す
//   2) 行数が最少になる割り振りを選ぶ
//   3) 行数が同じなら、各行の余り幅の2乗和が最小(=行の長さが最も均等)になる割り振りを選ぶ。最後の行も含めるので、短い文が先で長い方が後に来やすい
export function wrapJa(txt, size, maxW) {
  const sentences = String(txt ?? "").match(/[^。！？!?]+[。！？!?]*/g) ?? [];
  const units = [];
  for (const s of sentences) {
    if (measure(s, size) <= maxW) { units.push(s); continue; }
    let cur = "";
    for (const ch of s) {
      if (cur && measure(cur + ch, size) > maxW && !NO_HEAD.includes(ch)) { units.push(cur); cur = ch; } else cur += ch;
    }
    if (cur) units.push(cur);
  }
  const n = units.length, best = Array(n + 1).fill(null);
  best[0] = { lines: 0, cost: 0, from: -1 };
  for (let i = 1; i <= n; i++) {
    for (let j = i - 1; j >= 0; j--) {
      if (!best[j]) continue;
      const w = measure(units.slice(j, i).join(""), size);
      if (w > maxW) { if (j < i - 1) break; continue; }
      const cand = { lines: best[j].lines + 1, cost: best[j].cost + (maxW - w) ** 2, from: j };
      if (!best[i] || cand.lines < best[i].lines || (cand.lines === best[i].lines && cand.cost < best[i].cost)) best[i] = cand;
    }
  }
  const out = [];
  for (let i = n; i > 0; i = best[i].from) out.unshift(units.slice(best[i].from, i).join(""));
  return out;
}

// 曲名・アーティスト名の折り返し: 英単語は途中で切らず、日本語は1文字ずつ。長くても省略せず、全部表示する
export function wrapTitle(txt, size, maxW) { return wrapMixed(txt, size, maxW); }
function wrapMixed(txt, size, maxW) {
  const tokens = String(txt ?? "").match(/[A-Za-z0-9'’.,!?&:;\-_()\[\]\/+~]+|\s+|[\s\S]/gu) ?? [];
  const lines = []; let cur = "";
  const push = () => { if (cur.trim()) lines.push(cur.trimEnd()); cur = ""; };
  for (const tk of tokens) {
    if (measure(cur + tk, size) <= maxW) { cur += tk; continue; }
    if (/^\s+$/.test(tk)) { push(); continue; }
    // 行頭に来てはいけない文字(閉じ括弧「>」「)」や句読点)は、1文字だけ次の行に落とさず、直前の1文字といっしょに次の行へ送る
    if (NO_HEAD.includes(tk[0]) && cur.length > 1) {
      let moved = tk;                                    // 行頭に来てよい文字に当たるまで、前の文字を、いっしょに次の行へ送る
      while (cur.length > 1 && NO_HEAD.includes(moved[0])) { moved = cur.slice(-1) + moved; cur = cur.slice(0, -1); }
      push(); cur = moved; continue;
    }
    push();
    if (measure(tk, size) <= maxW) { cur = tk; continue; }
    for (const ch of tk) { if (cur && measure(cur + ch, size) > maxW) push(); cur += ch; }
  }
  push();
  return lines.length ? lines : [""];
}

// ---------- 共通の定義 (グラデーション・ぼかし) ----------
function defs(p) {
  const rb = [[0.08, "#ff5300"], [0.16, "#f9fa01"], [0.24, "#93ed0e"], [0.32, "#11b82f"], [0.4, "#00c069"], [0.48, "#00e3c1"], [0.56, "#00d5fc"], [0.64, "#0045b2"], [0.72, "#110190"], [0.8, "#af00be"], [0.88, "#ff0044"]];
  return `<defs>
    <linearGradient id="${p}go" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="100"><stop offset="0" stop-color="#d746fe"/><stop offset=".45" stop-color="#d746fe"/><stop offset=".6" stop-color="#b646f9"/><stop offset=".75" stop-color="#8d46f3"/><stop offset=".9" stop-color="#6545ee"/><stop offset="1" stop-color="#5d3eed"/></linearGradient>
    <linearGradient id="${p}gi" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="100"><stop offset="0" stop-color="#fef9ff"/><stop offset=".45" stop-color="#fdfbff"/><stop offset="1" stop-color="#ebdffe"/></linearGradient>
    <linearGradient id="${p}gt" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="100"><stop offset="0" stop-color="#f9e2a2"/><stop offset="1" stop-color="#f0c56f"/></linearGradient>
    <linearGradient id="${p}gr" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="100">${rb.map(([o, c]) => `<stop offset="${o}" stop-color="${c}"/>`).join("")}</linearGradient>
    <linearGradient id="${p}lit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4faff"/><stop offset="1" stop-color="#9fcdf0"/></linearGradient>
    <linearGradient id="${p}sep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#112277"/><stop offset=".1" stop-color="#2255cc"/><stop offset=".3" stop-color="#66ccff"/><stop offset=".5" stop-color="#99ddff"/><stop offset=".7" stop-color="#66ccff"/><stop offset=".9" stop-color="#2255cc"/><stop offset="1" stop-color="#112277"/></linearGradient>
    <radialGradient id="${p}rad" cx="50%" cy="50%" r="60%"><stop offset="0" stop-color="#8cc6ee" stop-opacity=".6"/><stop offset="1" stop-color="#3a9bd8" stop-opacity=".92"/></radialGradient>
    <filter id="${p}glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.6"/></filter>
    <filter id="${p}halo" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.6"/></filter>
    <filter id="${p}blur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="1.6"/></filter>
  </defs>`;
}
const sep = (p, x, y, w) => `<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="2" fill="url(#${p}sep)"/>`;

// ---------- 点数の大きな数字 (公式画像の字形をベクトル化したもの) ----------
function glyph(g, x, y, scale, kind, p) {
  const outFill = kind === "h100" ? `url(#${p}gr)` : `url(#${p}go)`;
  const inFill = kind === "ten" ? `url(#${p}gt)` : kind === "h100" ? "#ffffff" : `url(#${p}gi)`;
  const glow = kind === "h100" ? `url(#${p}gr)` : kind === "ten" ? "#d070e8" : "#e070ff";
  return `<g transform="translate(${f(x)} ${f(y)}) scale(${scale})"><path d="${g.out}" fill="${glow}" opacity="1" filter="url(#${p}glow)"/><path d="${g.out}" fill="${kind === "digit" ? "#ff9cf8" : glow}" opacity=".75" filter="url(#${p}halo)"/><path d="${g.out}" fill="${outFill}"/><path d="${g.inn}" fill="${inFill}"/></g>`;
}
function scoreSVG(r, p, xRight, yTop) {
  const A = ASSETS, S = 0.6, KERN = -2;
  const parts = [];
  if (num(r.totalPoint) >= 100) {
    parts.push([A.h100, "h100"], [A.ten, "ten"]);
  } else {
    const [ip, dp = "000"] = String(r.totalPoint).split(".");
    for (const c of ip) parts.push([A.digits[c], "digit"]);
    parts.push([A.dot, "digit"]);
    for (const c of dp.padEnd(3, "0").slice(0, 3)) parts.push([A.sdigits[c], "digit"]);
    parts.push([A.ten, "ten"]);
  }
  const total = parts.reduce((s, [g]) => s + g.w * S + KERN, -KERN);
  let x = xRight - total, out = "";
  for (const [g, kind] of parts) { out += glyph(g, x, yTop, S, kind, p); x += g.w * S + KERN; }
  return out;
}

// ---------- レーダーチャート ----------
function radarSVG(r, p, cx, cy, R) {
  const axes = [
    { name: "音程", v: num(r.radarChartPitch) }, { name: "安定性", v: num(r.radarChartStability) },
    { name: "表現力", v: num(r.radarChartExpressive) }, { name: "リズム", v: num(r.radarChartRhythm) },
    { name: "V&L", v: num(r.radarChartVibratoLongtone) },
  ];
  const ang = (k) => ((-90 + 72 * k) * Math.PI) / 180;
  const pt = (k, q) => [cx + R * q * Math.cos(ang(k)), cy + R * q * Math.sin(ang(k))];
  const poly = (qs) => qs.map((q, k) => pt(k, q).map(f).join(",")).join(" ");
  let s = "";
  for (const q of [0.2, 0.4, 0.6, 0.8]) s += `<polygon points="${poly([q, q, q, q, q])}" fill="none" stroke="rgba(150,200,240,.25)" stroke-width=".7"/>`;
  s += `<polygon points="${poly([1, 1, 1, 1, 1])}" fill="rgba(70,120,170,.14)" stroke="rgba(210,225,240,.75)" stroke-width="1"/>`;
  for (let k = 0; k < 5; k++) { const [x, y] = pt(k, 1); s += `<line x1="${cx}" y1="${cy}" x2="${f(x)}" y2="${f(y)}" stroke="rgba(150,200,240,.25)" stroke-width=".7"/>`; }
  s += `<g id="${p}rpoly" data-a="1"><polygon points="${poly(axes.map((a) => clamp(a.v, 0, 100) / 100))}" fill="url(#${p}rad)" stroke="#9fe3ff" stroke-width="1.4" stroke-linejoin="round"/></g>`;
  // 項目名(黄)と値(白)の置き場所。どちらも「軸の頂点」からの相対位置
  const base = [[0, -R], [R * 0.95, -R * 0.31], [R * 0.59, R * 0.81], [-R * 0.59, R * 0.81], [-R * 0.95, -R * 0.31]];
  const place = [
    { n: [0, -10], na: "middle", v: [0, 7] },
    { n: [12, -8], na: "start", v: [-5, 6] },
    { n: [12, 14], na: "start", v: [-1, 4] },
    { n: [-12, 14], na: "end", v: [1, 4] },
    { n: [-12, -8], na: "end", v: [5, 6] },
  ];
  let nums = "";
  axes.forEach((a, k) => {
    const [bx, by] = base[k], pl = place[k];
    s += T(cx + bx + pl.n[0], cy + by + pl.n[1], a.name, { size: 12, fill: YEL, anchor: pl.na, stroke: BG });
    nums += T(cx + bx + pl.v[0], cy + by + pl.v[1] + 5, String(a.v), { size: 17, fill: WHITE, anchor: "middle", stroke: BG });
  });
  return s + `<g id="${p}rnum" data-a="1">${nums}</g>`;
}

// ---------- 24区間の折れ線 (音程=緑 / 表現力=紫) ----------
function sectionSVG(r, x0, y0, W = 420, H = 71, p = "") {
  const L = 38, T0 = 3, Rm = 6, B0 = 3, pw = W - L - Rm, ph = H - T0 - B0;
  const X = (i) => L + ((i + 0.5) / 24) * pw;
  const Y = (v) => T0 + (1 - (clamp(v, 40, 100) - 40) / 60) * ph;
  const series = (kind) => Array.from({ length: 24 }, (_, i) => num(r[`${kind}GraphPointsSection${String(i + 1).padStart(2, "0")}`]));
  let s = `<g transform="translate(${x0} ${y0})">`;
  for (const v of [100, 80, 60, 40]) {
    s += `<line x1="${L}" y1="${f(Y(v))}" x2="${W - Rm}" y2="${f(Y(v))}" stroke="#d6d6d6" stroke-width="1" opacity=".9"/>`;
    s += T(L - 12, Y(v) + 4, String(v), { size: 12, anchor: "end" });
  }
  for (let g = 0; g <= 6; g++) { const x = L + (g / 6) * pw; s += `<line x1="${f(x)}" y1="${T0}" x2="${f(x)}" y2="${T0 + ph}" stroke="#d6d6d6" stroke-width="1" opacity=".9"/>`; }
  const draw = (vals, color, shape) => {
    let seg = [];
    const flush = () => { if (seg.length > 1) s += `<polyline points="${seg.join(" ")}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linejoin="round"/>`; seg = []; };
    vals.forEach((v, i) => { if (v > 0) seg.push(`${f(X(i))},${f(Y(v))}`); else flush(); });
    flush();
    vals.forEach((v, i) => {
      if (v <= 0) return;
      const x = X(i), y = Y(v);
      s += shape === "circle" ? `<circle cx="${f(x)}" cy="${f(y)}" r="3.6" fill="${color}"/>`
        : `<polygon points="${f(x)},${f(y - 4)} ${f(x + 4)},${f(y)} ${f(x)},${f(y + 4)} ${f(x - 4)},${f(y)}" fill="${color}"/>`;
    });
  };
  s += `<clipPath id="${p}scc"><rect id="${p}scr" x="${L - 6}" y="0" width="${pw + 12}" height="${H}"/></clipPath><g clip-path="url(#${p}scc)" data-a="1">`;   // 開く動きで、窓を左から右へ広げる
  draw(series("expression"), "#8e86ff", "diamond");
  draw(series("interval"), "#7dec7d", "circle");
  return s + `</g></g>`;
}

// ---------- メーター (ダイヤ・安定性・リズム) : 青い光彩つき ----------
const GLOW = "#3f8fd8", EDGE = "#7dbdf0";
function diamondsSVG(level10, p, x0, y0) {
  const lv = clamp(num(level10), 0, 10) / 2, pitch = 13, w = 11, h = 11;   // ダイヤは正方形のまま。隣と重ならないよう、大きさとピッチで隙間をあける
  let s = `<g transform="translate(${f(x0)} ${f(y0)})">`;
  for (let i = 0; i < 5; i++) {
    const fill = clamp(lv - i, 0, 1), x = i * pitch + (pitch - w) / 2;
    const pts = `${f(x + w / 2)},0 ${f(x + w)},${f(h / 2)} ${f(x + w / 2)},${h} ${f(x)},${f(h / 2)}`;
    const id = `${p}dm${i}`;
    s += `<polygon points="${pts}" fill="none" stroke="${GLOW}" stroke-width="3" filter="url(#${p}blur)"/>`;
    s += `<clipPath id="${id}"><rect x="${f(x)}" y="0" width="${f(w * fill)}" height="${h}"/></clipPath>`;
    s += `<polygon points="${pts}" fill="#101010" stroke="${EDGE}" stroke-width="1"/>`;
    if (fill > 0) s += `<polygon points="${pts}" fill="url(#${p}lit)" clip-path="url(#${id})"/>`;
    s += `<polygon points="${pts}" fill="none" stroke="${EDGE}" stroke-width="1"/>`;
  }
  return s + `</g>`;
}
// 台形(左が細く右が太い)を10段に分けたバー。value 段だけ左から点灯
function stabilitySVG(level, p, x0, y0) {
  const n = clamp(Math.round(num(level)), 0, 10), W = 58, H = 19, cy = H / 2;
  const half = (x) => (4 + (x / W) * 5.5) * 0.72;   // 縦だけ押しつぶした形
  let s = `<g transform="translate(${f(x0)} ${f(y0)})">`;
  const outline = `${0},${f(cy - half(0))} ${W},${f(cy - half(W))} ${W},${f(cy + half(W))} ${0},${f(cy + half(0))}`;
  s += `<polygon points="${outline}" fill="none" stroke="${GLOW}" stroke-width="3" filter="url(#${p}blur)"/>`;
  s += `<polygon points="${outline}" fill="#0d0d0d" stroke="${EDGE}" stroke-width="1.1" stroke-linejoin="round"/>`;
  for (let i = 0; i < 10; i++) {
    // 10段を、枠の左端〜右端いっぱいに並べる。右端(まっすぐ側)の黒い余白が出ないよう、最後の段は、枠の右端まで広げる
    const segW = (W - 0.8) / 10, a = 0.4 + i * segW, b = i === 9 ? W - 0.4 : a + segW - 0.5;
    const seg = `${f(a)},${f(cy - half(a) + 0.5)} ${f(b)},${f(cy - half(b) + 0.5)} ${f(b)},${f(cy + half(b) - 0.5)} ${f(a)},${f(cy + half(a) - 0.5)}`;
    s += `<polygon points="${seg}" fill="${i < n ? `url(#${p}lit)` : "#0a0a0a"}" stroke="${EDGE}" stroke-opacity="${i < n ? 0.25 : 0.55}" stroke-width=".6"/>`;
  }
  return s + `</g>`;
}
// 7段のレンズ形。中央は常に点灯し、タイミングが5より小さいと右へ、大きいと左へ、差の数(最大3)だけ点灯が広がる
function rhythmSVG(timing, p, x0, y0) {
  const t = clamp(Math.round(num(timing, 5)), 1, 10), W = 50, H = 19, cy = H / 2;
  const lit = new Set([3]);
  if (t < 5) for (let k = 1; k <= Math.min(3, 5 - t); k++) lit.add(3 + k);
  if (t > 5) for (let k = 1; k <= Math.min(3, t - 5); k++) lit.add(3 - k);
  const hh = [3.5, 5.5, 7.5, 9.5, 9.5, 7.5, 5.5, 3.5].map((v) => v * 0.72); // 8つの境界の半分の高さ (縦だけ押しつぶした形)
  const bx = (k) => (k * W) / 7;
  let s = `<g transform="translate(${f(x0)} ${f(y0)})">`;
  const top = hh.map((h, k) => `${f(bx(k))},${f(cy - h)}`), bot = hh.map((h, k) => `${f(bx(k))},${f(cy + h)}`).reverse();
  const outline = [...top, ...bot].join(" ");
  s += `<polygon points="${outline}" fill="none" stroke="${GLOW}" stroke-width="3" filter="url(#${p}blur)"/>`;
  s += `<polygon points="${outline}" fill="#0d0d0d" stroke="${EDGE}" stroke-width="1.1" stroke-linejoin="round"/>`;
  for (let i = 0; i < 7; i++) {
    const a = bx(i) + 0.5, b = bx(i + 1) - 0.5;
    const ha = hh[i] - 0.6, hb = hh[i + 1] - 0.6, on = lit.has(i);
    s += `<polygon points="${f(a)},${f(cy - ha)} ${f(b)},${f(cy - hb)} ${f(b)},${f(cy + hb)} ${f(a)},${f(cy + ha)}" fill="${on ? `url(#${p}lit)` : "#0a0a0a"}" stroke="${EDGE}" stroke-opacity="${on ? 0.25 : 0.55}" stroke-width=".6"/>`;
  }
  return s + `</g>`;
}

// ---------- ビブラートの波形 (公式の波形画像をベクトル化したもの) ----------
const VIB_CODE = { N: 0, "A-1": 1, "B-1": 2, "C-1": 3, "A-2": 4, "B-2": 5, "C-2": 6, "A-3": 7, "B-3": 8, "C-3": 9, D: 10, E: 11, F: 12, G: 13, H: 14 };
// 元サイトと同じ幅(88)の枠を自前で描き、その中に、公式の波形(assets.js。枠の縁は含まない)を入れる。
// 公式画像で波が実際に届いている範囲(横10〜105, 縦10〜45: 山と谷は枠の縁に隠れて、ここで切れている)を、自前の枠の線に合わせて拡縮する:
// 山と谷の端が、枠の線にちょうど重なり、出っ張りも二重線も出ない。
// 種類の文字(H など)は、枠の内側の右から4px・下端に、薄い暗幕つきで置く
// true: 元サイトの波形GIF(ラベルの裏でも波が最後まである。元サイトと同じ、少しざらついた線) / false: 公式画像の波形(なめらかな線。ラベルの裏の部分は波が欠ける)
const USE_SITE_WAVE = true;
const WAVE_DY = 0.3;   // 波を、枠に対して、上へずらす量(px)。上端側の隙間と下端側の隙間を揃えるため (0〜1の間で、小数も使える)
// ビブラートの波形。元サイトの波形GIF(ラベルの文字を含まない完全な波形。vib_gif.js)を使う。
// 元サイトに画像が無い A-3 だけは、公式画像の波形(assets.js。枠の縁とラベルの下の部分を除いたもの)で代用する。
// いずれも、波の上端・下端が、自前の枠の線にちょうど重なるように拡縮する。
// ラベル(H など)の裏の長方形は半透明なので、波がその裏でも透けて見える。
function vibratoSVG(type, p, x0, y0) {
  const BW = 88, BH = 32, label = String(type || "N"), tw = measure(label, 14);
  const g = USE_SITE_WAVE ? VIBG[label] : null;
  let wave;
  if (g) {
    const sx = (BW - 1.2) / g.w, sy = (BH - 1.2) / g.h, n2 = (v) => v.toFixed(2).replace(/\.?0+$/, "");
    const P = [];                                     // 点列を0.5px間隔に間引き、点と点の間は、なめらかな曲線(Catmull-Rom→3次ベジェ)でつなぐ
    for (let i = 0; i < g.p.length; i += 4) P.push([0.6 + g.p[i] * sx, 0.6 + g.p[i + 1] * sy - WAVE_DY]);
    if ((g.p.length / 2 - 1) % 2) P.push([0.6 + g.p[g.p.length - 2] * sx, 0.6 + g.p[g.p.length - 1] * sy - WAVE_DY]);
    let d = `M${n2(P[0][0])} ${n2(P[0][1])}`;
    for (let i = 0; i < P.length - 1; i++) {
      const a = P[Math.max(i - 1, 0)], b = P[i], c = P[i + 1], e = P[Math.min(i + 2, P.length - 1)];
      d += `C${n2(b[0] + (c[0] - a[0]) / 6)} ${n2(b[1] + (c[1] - a[1]) / 6)} ${n2(c[0] - (e[0] - b[0]) / 6)} ${n2(c[1] - (e[1] - b[1]) / 6)} ${n2(c[0])} ${n2(c[1])}`;
    }
    // 波の線は、枠の内側(角丸も同じ形)で切り抜く: 山の頂上が枠に触れても、線の端が、枠の外や、角の外へはみ出さない
    wave = `<clipPath id="${p}vc2"><rect x="1.2" y="1.2" width="${BW - 2.4}" height="${BH - 2.4}" rx="3.2"/></clipPath><path d="${d}" fill="none" stroke="#00ff00" stroke-width="2.2" stroke-linejoin="round" clip-path="url(#${p}vc2)"/>`;
  } else {
    const v = ASSETS.vib[VIB_CODE[type] ?? 0], yt = 10, yb = 44.4;                      // 公式画像で、波が届いている範囲(縦)
    const sx = (BW - 1.2) / 95, sy = (BH - 1.2) / (yb - yt);
    const lxs = 10 + (BW - 5 - tw - 3 - 0.6) / sx, lws = (tw + 10) / sx, lys = yt + (BH - 4 - 0.6) / sy;
    const strip = lys < yb ? ` M${f(lxs)} ${f(lys)}h${f(lws)}v${f(yb - lys)}h${f(-lws)}z` : "";   // 暗幕の下の細い帯の切れ端だけ除く
    wave = `<clipPath id="${p}vc"><path clip-rule="evenodd" d="M10 ${yt}h95v${f(yb - yt)}h-95z${strip}"/></clipPath>
    <g transform="translate(.6 .6) scale(${sx.toFixed(4)} ${sy.toFixed(4)}) translate(-10 ${-yt})"><g clip-path="url(#${p}vc)"><path d="${v.core}" fill="#19ff19" stroke="#19ff19" stroke-width="1.1" stroke-linejoin="round"/></g></g>`;
  }
  return `<g transform="translate(${f(x0)} ${f(y0)})">
    <rect x=".6" y=".6" width="${BW - 1.2}" height="${BH - 1.2}" rx="4" fill="none" stroke="#00ff00" stroke-width="1.2"/>
    ${wave}
    <rect x="${f(BW - 5 - tw - 2)}" y="${f(BH - 16.5)}" width="${f(tw + 4)}" height="12.5" fill="rgba(34,34,34,.5)"/>
    <text x="${BW - 5}" y="${f(BH - 5.5)}" font-size="14" text-anchor="end" fill="#ffffff">${esc(label)}</text></g>`;
}// ---------- 右: 同じ曲の推移 ----------
const SERIES = [
  { name: "総合点", color: "#ff8a8a", shape: "circle", get: (r) => num(r.totalPoint) },
  { name: "素点", color: "#a9a9a9", shape: "diamond", get: (r) => num(r.rawPoint) },
  { name: "音程", color: "#7dec7d", shape: "square", get: (r) => num(r.radarChartPitch) },
  { name: "安定性", color: "#7ff3f3", shape: "tri", get: (r) => num(r.radarChartStability) },
  { name: "表現力", color: "#8e86ff", shape: "trid", get: (r) => num(r.radarChartExpressive) },
  { name: "リズム", color: "#ffee66", shape: "circle", get: (r) => num(r.radarChartRhythm) },
  { name: "V&L", color: "#ff8cf2", shape: "diamond", get: (r) => num(r.radarChartVibratoLongtone) },
];
function marker(shape, x, y, color, r = 4.4) {
  const q = (a) => a.map(([px, py]) => `${f(px)},${f(py)}`).join(" ");
  switch (shape) {
    case "square": return `<rect x="${f(x - r)}" y="${f(y - r)}" width="${f(2 * r)}" height="${f(2 * r)}" fill="${color}"/>`;
    case "diamond": return `<polygon points="${q([[x, y - r - 1], [x + r + 1, y], [x, y + r + 1], [x - r - 1, y]])}" fill="${color}"/>`;
    case "tri": return `<polygon points="${q([[x, y - r - 1], [x + r + 1, y + r], [x - r - 1, y + r]])}" fill="${color}"/>`;
    case "trid": return `<polygon points="${q([[x, y + r + 1], [x + r + 1, y - r], [x - r - 1, y - r]])}" fill="${color}"/>`;
    default: return `<circle cx="${f(x)}" cy="${f(y)}" r="${r}" fill="${color}"/>`;
  }
}
const md = (dt) => { const m = /^(\d+)\/(\d+)\/(\d+)/.exec(dt || ""); return m ? `${+m[2]}/${+m[3]}` : ""; };

// グラフの寸法 (描画とホバー表示で共有)
function songGeom(plays, W, H) {
  const tall = H >= 350;
  const L = 53, Rm = tall ? 24 : 12, T0 = tall ? 68 : 22, axisY = H - (tall ? 101 : 84), pw = W - L - Rm, ph = axisY - T0;
  const all = plays.flatMap((r) => SERIES.map((s) => s.get(r))).filter((v) => v > 0);
  const lo = Math.max(0, Math.min(...all)), yMin = Math.min(Math.floor(lo) - 1, 94), yMax = 100;
  return { tall, L, Rm, T0, axisY, pw, ph, yMin, yMax, W, H, n: plays.length };
}

function songChartSVG(plays, currentId, x0, y0, W, H, p = "", cx = W / 2) {   // cx: 凡例を左右中央に揃える位置(このグラフの左端からの距離)
  const { tall, L, Rm, T0, axisY, pw, ph, yMin, yMax } = songGeom(plays, W, H);
  const Y = (v) => T0 + (1 - (clamp(v, yMin, yMax) - yMin) / (yMax - yMin)) * ph;
  const n = plays.length, X = (i) => L + ((i + 0.5) / n) * pw;
  let s = `<g transform="translate(${f(x0)} ${f(y0)})">`;
  for (let v = Math.ceil(yMin / 5) * 5; v <= yMax; v += 5) {
    s += `<line x1="${L}" y1="${f(Y(v))}" x2="${W - Rm}" y2="${f(Y(v))}" stroke="#d8d8d8" stroke-width="1" opacity=".9"/>`;
    s += T(L - 15, Y(v) + 4.5, String(v), { size: 13, anchor: "end" });
  }
  s += `<line x1="${L}" y1="${axisY}" x2="${W - Rm}" y2="${axisY}" stroke="#ddd" stroke-width="1.2"/>`;
  for (let i = 0; i <= n; i++) { const x = L + (i / n) * pw; s += `<line x1="${f(x)}" y1="${axisY}" x2="${f(x)}" y2="${axisY + 6}" stroke="#ddd" stroke-width="1.2"/>`; }
  plays.forEach((r, i) => { s += T(X(i), axisY + 22, md(r.scoringDateTime), { size: 13, anchor: "middle" }); });
  s += `<clipPath id="${p}sgc"><rect id="${p}sgr" x="${L - 8}" y="${T0 - 12}" width="${pw + 16}" height="${ph + 24}"/></clipPath><g clip-path="url(#${p}sgc)" data-a="1">`;   // 開く動きで、窓を左から右へ広げる
  for (const se of SERIES) {
    const vals = plays.map((r) => se.get(r));
    s += `<polyline points="${vals.map((v, i) => `${f(X(i))},${f(Y(v))}`).join(" ")}" fill="none" stroke="${se.color}" stroke-width="2" stroke-linejoin="round"/>`;
    vals.forEach((v, i) => { s += marker(se.shape, X(i), Y(v), se.color, plays[i].scoringDxgId === currentId ? 5 : 4); });
  }
  s += `</g>`;
  // 凡例: 上段(総合点・素点・音程の3つ)と下段(安定性・表現力・リズム・V&Lの4つ)を、列を揃えたまま、2行まとめた「ひとかたまり」として、cx を中心に左右中央に置く
  const legendRows = [SERIES.slice(0, 3), SERIES.slice(3)], GAP = 22;
  const colW = [0, 1, 2, 3].map((k) => Math.max(...legendRows.map((r) => (r[k] ? 25 + measure(r[k].name, 13) : 0))));   // 各列の幅 = その列の項目のうち、いちばん広いもの
  const blockW = colW.reduce((a, b) => a + b, 0) + GAP * 3, bx0 = cx - blockW / 2;
  legendRows.forEach((rowItems, row) => {
    const y = H - 42 + row * 18;
    rowItems.forEach((se, k) => {
      const x = bx0 + colW.slice(0, k).reduce((a, b) => a + b, 0) + GAP * k;
      s += `<line x1="${f(x)}" y1="${y}" x2="${f(x + 20)}" y2="${y}" stroke="${se.color}" stroke-width="2"/>${marker(se.shape, x + 10, y, se.color, 3.8)}`;
      s += T(x + 25, y + 4.5, se.name, { size: 13 });
    });
  });
  return s + `</g>`;
}

// ---------- 全体の組み立て ----------
export function buildDetailSVG(r, all, { layout = "wide" } = {}) {
  const p = `d${++uid}_`;
  const wide = layout === "wide";
  const LW = 450;                                   // 左半分の幅
  let s = "", y;

  // タイトル (長くても省略せず折り返す。2行目以降の分だけ、下の内容を下げる)
  const titleLines = wrapMixed(`${r.contentsName ?? ""} / ${r.artistName ?? ""}`, 16, (wide ? 900 : 450) - 32);
  const dy = (titleLines.length - 1) * 20;
  const titleSVG = titleLines.map((ln, i) => T(16, 27 + i * 20, ln, { size: 16 })).join("");

  // 上段: 得点 + レーダー
  const xr = 232;
  s += T(xr, 49, "", {});
  const vRaw = `${r.rawPoint}点`, vBonus = `${r.bonusPoint}点`;
  const xv = xr - Math.max(measure(vRaw, 15), measure(vBonus, 15)), xc = xv - 3; // 値の左端 / コロンの右端 (2行で共通)
  s += `<text x="${f(xc)}" y="52" font-size="12" text-anchor="end" fill="${YEL}">素点:</text><text x="${xr}" y="52" font-size="15" text-anchor="end" fill="${WHITE}">${esc(vRaw)}</text>`;
  s += `<text x="${f(xc)}" y="69" font-size="12" text-anchor="end" fill="${YEL}">${esc(r.bonusTypeText || "ボーナス")}ボーナス:</text><text x="${xr}" y="69" font-size="15" text-anchor="end" fill="${WHITE}">${esc(vBonus)}</text>`;
  s += scoreSVG(r, p, xr + 2, 74);
  if (num(r.nationalAverageTotalPoints) > 0) s += `<text x="${xr}" y="150" font-size="12" text-anchor="end" fill="${YEL}">全国平均: <tspan font-size="15" fill="${YEL}">${esc(r.nationalAverageTotalPoints)}点</tspan></text>`;
  s += T(xr, 167, r.scoringDateTime ?? "", { size: 14, anchor: "end" });
  s += radarSVG(r, p, 337, 112, 47);

  // 分析レポート
  s += sep(p, 10, 181, 430);
  s += T(11, 202, "分析レポート", { size: 15 });
  const lines = wrapJa(r.comment, 12, LW - 21 - 14);
  lines.forEach((ln, i) => { s += T(21, 221 + i * 17.14, ln, { size: 12 }); });
  y = 221 + (lines.length - 1) * 17.14;
  s += sep(p, 10, y + 9, 430);

  // 音程・表現力
  y += 9 + 19;
  s += `<text x="11" y="${f(y)}" font-size="15" fill="${WHITE}">音程 <tspan font-size="11" fill="${YEL}" dx="8">正確率</tspan><tspan font-size="15" fill="${WHITE}">${num(r.radarChartPitch)}</tspan><tspan font-size="11" fill="${YEL}">%</tspan></text>`;
  y += 18;
  const m = (x, label, val, unit, big) => `<text x="${x}" y="${f(y)}" font-size="11" fill="${YEL}">${label ? `<tspan font-size="${big ? 15 : 15}" fill="${WHITE}">${label}</tspan> ` : ""}<tspan font-size="15" fill="${WHITE}">${val}</tspan><tspan font-size="11" fill="${YEL}">${unit}</tspan></text>`;
  s += `<text x="11" y="${f(y)}" font-size="15" fill="${WHITE}">表現力 <tspan>${num(r.radarChartExpressive)}</tspan><tspan font-size="11" fill="${YEL}">点</tspan></text>`;
  s += `<text x="114" y="${f(y)}" font-size="11" fill="${YEL}">抑揚<tspan font-size="15" fill="${WHITE}">${num(r.intonation)}</tspan>点</text>`;
  s += `<text x="191" y="${f(y)}" font-size="11" fill="${YEL}">しゃくり<tspan font-size="15" fill="${WHITE}">${num(r.shakuriCount)}</tspan>回</text>`;
  s += `<text x="281" y="${f(y)}" font-size="11" fill="${YEL}">こぶし<tspan font-size="15" fill="${WHITE}">${num(r.kobushiCount)}</tspan>回</text>`;
  s += `<text x="358" y="${f(y)}" font-size="11" fill="${YEL}">フォール<tspan font-size="15" fill="${WHITE}">${num(r.fallCount)}</tspan>回</text>`;
  const secY = y + 8;
  s += sectionSVG(r, 11, secY, 420, 71, p);
  y += 8 + 71 + 10;
  s += sep(p, 10, y, 430);

  // 下段: 左(ロングトーン/安定性/リズム) と 右(ビブラート/音域)
  // 各領域(区切り線と区切り線の間)の、上下中央に、文字と図形を置く。S0 = 上の区切り線の位置
  const S0 = y;
  const line1 = S0 + 33, line2 = S0 + 66, bottom = S0 + 95;   // bottom = 最下段の領域の下端 (行の位置の基準)       // 左列の区切り線(右列は line2 だけ) / 画像の下端(= 左列の下端)
  const c1 = (S0 + 2 + line1) / 2, c2 = (line1 + 1 + line2) / 2, c3 = (line2 + 1 + bottom) / 2;   // 各行の領域の中心
  const base = (c, size) => c + (size >= 14 ? 5 : 4);              // 文字の見た目の中心を c に合わせるための、ベースライン(文字の下端)の位置
  s += T(11, base(c1, 14), "ロングトーン", { size: 14 }) + T(102, base(c1, 11), "上手さ", { size: 11, fill: YEL }) + diamondsSVG(r.longtoneSkill, p, 140, c1 - 5.5);
  s += `<rect x="10" y="${f(line1)}" width="206" height="1" fill="#2a4aa8" opacity=".75"/>`;
  s += T(11, base(c2, 14), "安定性", { size: 14 }) + T(63, base(c2, 11), "震えがち", { size: 11, fill: YEL }) + stabilitySVG(r.sta_10, p, 111, c2 - 9.5) + T(173, base(c2, 11), "まっすぐ", { size: 11, fill: YEL });
  s += `<rect x="10" y="${f(line2)}" width="206" height="1" fill="#2a4aa8" opacity=".75"/>`;
  s += T(11, base(c3, 14), "リズム", { size: 14 }) + T(76, base(c3, 11), "タメ", { size: 11, fill: YEL }) + rhythmSVG(r.timing, p, 111, c3 - 9.5) + T(167, base(c3, 11), "走り", { size: 11, fill: YEL });

  // 右: ビブラートの領域(S0+2 〜 line2)。3行(ビブラート / 上手さ+ダイヤ / 合計・タイプ)を等間隔にして、領域の上下中央に置く。波形の枠は、上の2行の中央に置く
  const cv = (S0 + 2 + line2) / 2, rv1 = cv - 20, rv2 = cv, rv3 = cv + 20;
  s += T(225, base(rv1, 14), "ビブラート", { size: 14 });
  s += T(225, base(rv2, 11), "上手さ", { size: 11, fill: YEL }) + diamondsSVG(r.vibratoSkill, p, 264, rv2 - 5.5);
  s += `<text x="225" y="${f(rv3 + 4.5)}" font-size="11" fill="${YEL}">合計<tspan font-size="13" fill="${WHITE}">${esc(r.vibratoTotalSecond)}秒</tspan> <tspan font-size="13" fill="${WHITE}">${num(r.vibratoCount)}回</tspan></text>`;
  s += `<text x="338" y="${f(rv3 + 4.5)}" font-size="11" fill="${YEL}">タイプ<tspan font-size="13" fill="${WHITE}">${esc(r.vibratoTypeText || "")}</tspan></text>`;
  s += vibratoSVG(r.vibratoType || "N", p, 338, (rv1 + rv2) / 2 - 16);
  s += `<rect x="225" y="${f(line2)}" width="215" height="1" fill="#2a4aa8" opacity=".75"/>`;
  s += `<text x="225" y="${f(c3 + 5.5)}" font-size="15" fill="${WHITE}">音域 <tspan dx="8">${esc(r.singingRangeLowest)}～${esc(r.singingRangeHighest)}</tspan><tspan font-size="11" fill="${YEL}" dx="10">キー</tspan><tspan font-size="15" fill="${WHITE}">${esc(r.lastPerformKey ?? "±0")}</tspan></text>`;
  const leftH = bottom + 7.5;                                       // 画像の下端。最下段の文字・図形の下端〜画像の下端の余白を、上端〜曲名の余白(13.5px)に揃える
  // 右(同じ曲の推移)
  const plays = all.filter((x) => x.requestNo === r.requestNo).sort((a, b) => a.scoringDateTime.localeCompare(b.scoringDateTime)).slice(-10);
  let W, H, chart = "", songPos = null;
  if (wide) {
    W = 900; H = Math.max(leftH, 40 + 400 + 8);
    songPos = { x0: 454, y0: 40 + dy, W: 440, H: 400 };
    chart = plays.length ? songChartSVG(plays, r.scoringDxgId, 454, 40, 440, 400, p, (453 + 900) / 2 - 454) : "";
    chart += `<rect x="451" y="40" width="2" height="${H - 48}" fill="#1d3ea0"/>`;
  } else {
    W = 450; H = leftH + 4 + 268 - 5;   // 下の余白(最後の凡例の文字〜下端)を、上の余白(上端〜タイトル=13.5px)に揃える
    songPos = { x0: 0, y0: leftH + 4 + dy, W: 450, H: 268 };
    chart = sep(p, 10, leftH - 2, 430) + (plays.length ? songChartSVG(plays, r.scoringDxgId, 0, leftH + 4, 450, 268, p) : "");
  }
  const body = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H + dy}" viewBox="0 0 ${W} ${H + dy}" font-family="${FONT}" font-weight="bold">${defs(p)}<rect width="${W}" height="${H + dy}" fill="${BG}"/>${titleSVG}<g transform="translate(0 ${f(dy)})">${s}${chart}</g></svg>`;
  // マウスを乗せたときの表示(ホバー)用: グラフの位置と値 (画像は動かないので、位置は画像の座標で持つ)
  const sec = (kind) => Array.from({ length: 24 }, (_, i) => num(r[`${kind}GraphPointsSection${String(i + 1).padStart(2, "0")}`]));
  const hot = {
    W, H: H + dy,
    section: { x: 11 + 38, y: secY + 3 + dy, w: 420 - 38 - 6, h: 71 - 6, interval: sec("interval"), expression: sec("expression") },
    song: plays.length && songPos ? { ...songPos, ...songGeom(plays, songPos.W, songPos.H), plays, currentId: r.scoringDxgId } : null,
  };
  // 開く動き(アニメーション)用: 動かす部品の id と、切り抜き窓の全幅(w)と、「最後の点が見え終わる」窓の幅(wEnd)。
  // 窓は、左から右へ広げ、wEnd まで広げた時点(=動きの終わり)で、最後の点が見え終わる。w まで広げる(=窓の右端がグラフの右端に届く)のを終わりにすると、
  // 最後の点が、グラフの右端より手前にあるとき(右のグラフは、点が、各枠の中央に並ぶので、特に、歌った回数が少ないとき)に、見た目は、それより先に描き終わってしまい、
  // 左のレーダー・音程/表現力のグラフより、早く終わって見える。
  const secG = { pw: 420 - 38 - 6 }, sgG = plays.length && songPos ? songGeom(plays, songPos.W, songPos.H) : null;
  const anim = {
    radar: { poly: `${p}rpoly`, nums: `${p}rnum`, cx: 337, cy: 112 },
    section: { rect: `${p}scr`, w: secG.pw + 12, wEnd: Math.min(secG.pw + 12, (23.5 / 24) * secG.pw + 10) },       // 24区間。最後の点は、枠の中央(23.5/24)。窓の左端は L-6、点の半径は約4
    song: sgG ? { rect: `${p}sgr`, w: sgG.pw + 16, wEnd: Math.min(sgG.pw + 16, ((sgG.n - 0.5) / sgG.n) * sgG.pw + 8 + 7) } : null,   // 最後の点は、枠の中央((n-0.5)/n)。窓の左端は L-8、点(印)の半径は約6
  };
  return { svg: body, width: W, height: H + dy, hot, anim };
}

// ---------- PNG化 ----------
export async function svgToPngBlob(svg, width, height, scale = 2) {
  const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml;charset=utf-8" }));
  try {
    const img = new Image();
    img.decoding = "sync";
    await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error("SVGの読み込みに失敗")); img.src = url; });
    const c = document.createElement("canvas");
    c.width = Math.round(width * scale); c.height = Math.round(height * scale);
    const ctx = c.getContext("2d");
    ctx.fillStyle = BG; ctx.fillRect(0, 0, c.width, c.height);          // 先に背景色で塗りつぶす: 保存画像は、四隅も端も、透明にならない(完全に不透明な長方形)
    ctx.drawImage(img, 0, 0, c.width, c.height);
    return await new Promise((res) => c.toBlob(res, "image/png"));
  } finally { URL.revokeObjectURL(url); }
}

// 保存用など、縦横のpxを指定してPNGを作る。opts: { layout, width | height (どちらか。省略時は標準の2倍) }
export async function renderDetailPNG(record, all, opts = {}) {
  const { svg, width, height } = buildDetailSVG(record, all, { layout: opts.layout ?? "wide" });
  const scale = opts.width ? opts.width / width : opts.height ? opts.height / height : 2;
  return svgToPngBlob(svg, width, height, scale);
}

// ---------- 開く / 閉じる ----------
let overlay = null, objUrl = null, staticUrl = null, openToken = 0;
export function closeDetail() {
  openToken++;                                    // 動きの途中で閉じられたとき、続きの処理を止める
  overlay?.remove(); overlay = null;
  if (objUrl) { URL.revokeObjectURL(objUrl); objUrl = null; }
  if (staticUrl) { URL.revokeObjectURL(staticUrl); staticUrl = null; }
  document.removeEventListener("keydown", onKey);
  document.body.style.overflow = "";
  document.body.style.paddingRight = "";
}
function onKey(e) { if (e.key === "Escape") closeDetail(); }

// 表示倍率: PCの広い画面は元サイトのブラウザ150%相当に近い大きさで表示 (画像は高解像度で作る)
function displayZoom(layout) {
  const vw = window.innerWidth;
  if (layout === "narrow") return Math.min(1, (vw - 16) / 450);
  if (vw >= 1450) return 1.5;
  if (vw >= 1250) return 1.3;
  return Math.min(1, (vw - 16) / 900);
}

// ---------- クリック(タップ)したときの吹き出し ----------
// 画像(<img>)そのものの上のクリック・タップを拾って、黒い吹き出しと強調の丸を重ねる。
// 画像の上に透明な層を置かないので、右クリックの「画像をコピー/保存」・スマホの長押しは、そのまま使える。
const SEC_SERIES = [
  { key: "interval", name: "音程", color: "#7dec7d", shape: "circle" },
  { key: "expression", name: "表現力", color: "#8e86ff", shape: "diamond" },
];
function attachHover(wrap, img, hot, zoom) {
  wrap.style.setProperty("--z", String(zoom));
  // 吹き出し(と、強調の丸)は、グラフごとに1つずつ持つ: 音程・表現力のグラフ(sec)と、点数推移のグラフ(song)は、同時に出たままにできる。
  // 前の吹き出しを消すのは、同じグラフの中で、別の点をクリックしたとき(入れ替わる)と、どのグラフの範囲外もクリックしたとき(両方消える)。
  const mkPanel = () => {
    const tip = document.createElement("div"); tip.className = "dd-tip"; wrap.appendChild(tip);
    const hl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    hl.setAttribute("viewBox", `0 0 ${hot.W} ${hot.H}`); hl.setAttribute("class", "dd-hl"); wrap.appendChild(hl);
    return { tip, hl, hide: () => { tip.style.display = "none"; hl.innerHTML = ""; } };
  };
  const panels = { sec: mkPanel(), song: mkPanel() };
  const hideAll = () => { panels.sec.hide(); panels.song.hide(); };
  const halo = (shape, x, y, color) => `<circle cx="${f(x)}" cy="${f(y)}" r="9" fill="${color}" opacity=".85"/>` + marker(shape, x, y, "#fff", 5).replace('fill="#fff"', 'fill="none" stroke="#fff" stroke-width="1.3"');
  const row = (name, color, v) => `<div><span style="color:${color}">${esc(name)}:</span> ${esc(v)}</div>`;
  const show = (panel, html, border, px, py) => {
    const { tip } = panel;
    const r = img.getBoundingClientRect(), k = r.width / hot.W;
    tip.innerHTML = html; tip.style.borderColor = border; tip.style.display = "block";
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    let left = px * k + 16;
    if (left + tw > r.width) left = px * k - 16 - tw;
    tip.style.left = `${Math.max(0, left)}px`;
    tip.style.top = `${clamp(py * k - th / 2, 0, r.height - th)}px`;
  };
  const onMove = (e) => {
    const r = img.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * hot.W, y = ((e.clientY - r.top) / r.height) * hot.H;
    const s = hot.section;
    if (x >= s.x && x <= s.x + s.w && y >= s.y - 3 && y <= s.y + s.h + 3) {            // 区間ごとの音程・表現力
      const i = clamp(Math.floor(((x - s.x) / s.w) * 24), 0, 23);
      const vals = SEC_SERIES.map((se) => ({ ...se, v: s[se.key][i] })).filter((o) => o.v > 0);
      if (!vals.length) return panels.sec.hide();                                        // この区間に値が無いとき: このグラフの吹き出しだけ消す(点数推移の吹き出しは、そのまま)
      const px = s.x + ((i + 0.5) / 24) * s.w, Yf = (v) => s.y + (1 - (clamp(v, 40, 100) - 40) / 60) * s.h;
      panels.sec.hl.innerHTML = vals.map((o) => halo(o.shape, px, Yf(o.v), o.color)).join("");
      return show(panels.sec, `<div class="t">${i + 1}</div>` + vals.map((o) => row(o.name, o.color, o.v)).join(""), vals[0].color, px, s.y + s.h / 2);
    }
    const g = hot.song;
    if (g && x >= g.x0 + g.L && x <= g.x0 + g.W - g.Rm && y >= g.y0 + g.T0 && y <= g.y0 + g.axisY) {   // 同じ曲の推移
      const i = clamp(Math.floor(((x - (g.x0 + g.L)) / g.pw) * g.n), 0, g.n - 1), play = g.plays[i];
      const px = g.x0 + g.L + ((i + 0.5) / g.n) * g.pw;
      const Yf = (v) => g.y0 + g.T0 + (1 - (clamp(v, g.yMin, g.yMax) - g.yMin) / (g.yMax - g.yMin)) * g.ph;
      panels.song.hl.innerHTML = SERIES.map((se) => halo(se.shape, px, Yf(se.get(play)), se.color)).join("");
      // 総合点・素点は、小数第3位まで出す(保管庫は、末尾の0を省いた形(95.2 など)なので、95.200 にそろえる)
      const p3 = (v) => (Number.isFinite(Number(v)) && String(v).trim() !== "" ? Number(v).toFixed(3) : String(v));
      const val = (se) => (se.name === "総合点" ? p3(play.totalPoint) : se.name === "素点" ? p3(play.rawPoint) : se.get(play));
      return show(panels.song, `<div class="t">${esc(md(play.scoringDateTime))}</div>` + SERIES.map((se) => row(se.name, se.color, val(se))).join(""), SERIES[0].color, px, g.y0 + g.T0 + g.ph * 0.45);
    }
    hideAll();                                                                           // どのグラフの範囲外でもない: 両方の吹き出しを消す
  };
  // PC(マウス)もスマホ(指)も、同じ操作にそろえる: クリック(タップ)で表示して、そのまま残す。グラフの外(表示範囲外)をクリック(タップ)したら消える。
  //   スマホには、ホバー(乗せる)が無いので、マウスだけ「乗せている間だけ表示」にすると、操作が食い違う。
  //   同じグラフの中で、別の点をクリックすると、その点の表示に切り替わる。別のグラフの吹き出しは、そのまま(2つのグラフの吹き出しは、共存する)。
  //   画像の外(暗い背景)をクリックすると、採点結果画面そのものが閉じる。
  //   マウスの右ボタン(右クリックの「画像を保存」など)では、表示を変えない。
  img.addEventListener("pointerdown", (e) => { if (e.pointerType === "mouse" && e.button !== 0) return; onMove(e); });
}

// 動く部分(data-a)を含む入れ物と、定義(defs・clipPath)だけを残し、残りの要素を取り除く。
// 「全体を隠して、動く部分だけを見せる」CSSの方法は、iPhoneのブラウザ(WebKit)で動かないことがあるので、使わない
function pruneToAnimated(root) {
  for (const ch of [...root.children]) {
    const tag = ch.tagName.toLowerCase();
    if (tag === "defs" || tag === "clippath" || ch.hasAttribute("data-a")) continue;
    if (ch.querySelector("[data-a], clipPath")) { pruneToAnimated(ch); continue; }
    ch.remove();
  }
}

// ---------- 開く動き(アニメーション) ----------
// 元サイトは、点数をクリックした直後に、レーダーが中心から広がり、グラフが左から右へ描かれる。その実測(0.2秒ごとのフレーム)を元にしている。
//   動き出しの時刻は元サイトに合わせ(レーダー0.10秒・区間グラフ0.07秒・右グラフ0.24秒)、描き終わりは、すべて INTRO.end に揃える。
//   レーダーの数字(94 など)は、元サイトと同じく、描き終わった後に表示する。
const INTRO = { end: 1.0, radarStart: 0.10, sectionStart: 0.07, songStart: 0.24, numsStart: 0.80, numsFade: 0.20 };   // 数字(94 など)は、描き終わる少し前から出し始め、描き終わりと同時に出そろう
// レーダーの広がる速さ(実測): [進み具合 τ, 大きさ s]。ほぼ一定の速さで、終わり際だけ少し減速する
const RADAR_EASE = [[0, 0], [0.11, 0.09], [0.27, 0.26], [0.38, 0.40], [0.48, 0.54], [0.59, 0.68], [0.67, 0.77], [0.79, 0.89], [0.94, 0.98], [1, 1]];
function easeTable(tbl, x) {
  if (x <= 0) return 0; if (x >= 1) return 1;
  for (let i = 1; i < tbl.length; i++) if (x <= tbl[i][0]) { const [x0, y0] = tbl[i - 1], [x1, y1] = tbl[i]; return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0); }
  return 1;
}
// WebKit(iPhoneのSafari・Chrome)は、clipPath の中身を後から変えても、それを使っている要素を、再描画しないことがある。
// 切り抜きを使っている側の clip-path 属性を、付け直して、再描画させる。
function refreshClip(rect) {
  const cp = rect.parentNode, id = cp.getAttribute("id");
  const user = cp.ownerSVGElement.querySelector(`[clip-path="url(#${id})"]`);
  if (user) { user.removeAttribute("clip-path"); user.setAttribute("clip-path", `url(#${id})`); }
}
// svgEl: 画面に置いた(インライン)SVG。anim: buildDetailSVG が返す部品の id。cancelled(): 途中で閉じられたかどうか
function playIntro(svgEl, anim, cancelled) {
  const q = (id) => svgEl.querySelector(`[id="${id}"]`);
  const poly = q(anim.radar.poly), nums = q(anim.radar.nums);
  const sec = anim.section && q(anim.section.rect), song = anim.song && q(anim.song.rect);
  const { cx, cy } = anim.radar;
  const setRadar = (s) => poly.setAttribute("transform", s >= 1 ? "" : `translate(${cx} ${cy}) scale(${Math.max(s, 0.001)}) translate(${-cx} ${-cy})`);
  // 最初の状態 (完成形が一瞬見えないよう、挿入と同時に設定する)
  setRadar(0); nums.style.opacity = "0"; if (sec) sec.setAttribute("width", "0"); if (song) song.setAttribute("width", "0");
  const clamp01 = (v) => Math.min(1, Math.max(0, v));
  const total = INTRO.end;
  return new Promise((resolve) => {
    const t0 = performance.now();
    const tick = () => {
      if (cancelled()) return resolve(false);
      const t = (performance.now() - t0) / 1000;
      setRadar(easeTable(RADAR_EASE, clamp01((t - INTRO.radarStart) / (INTRO.end - INTRO.radarStart))));
      // 窓は、「最後の点が見え終わる幅(wEnd)」まで広げて、動きの終わりと、最後の点が現れるタイミングを、そろえる
      if (sec) { sec.setAttribute("width", String(anim.section.wEnd * clamp01((t - INTRO.sectionStart) / (INTRO.end - INTRO.sectionStart)))); refreshClip(sec); }
      if (song) { song.setAttribute("width", String(anim.song.wEnd * clamp01((t - INTRO.songStart) / (INTRO.end - INTRO.songStart)))); refreshClip(song); }
      nums.style.opacity = String(clamp01((t - INTRO.numsStart) / INTRO.numsFade));
      if (t >= total) {
        nums.style.opacity = "1";
        if (sec) { sec.setAttribute("width", String(anim.section.w)); refreshClip(sec); }      // 終わりは、窓を全幅に戻す(完成した絵と同じ)
        if (song) { song.setAttribute("width", String(anim.song.w)); refreshClip(song); }
        return resolve(true);
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

// opts: { layout: "wide"|"narrow" (省略時は画面幅で判定), scale: 画像の解像度の倍率, animate: false で開く動きなし }
// 構造: 下の層 = 動かさない部分(文字・点数・メーター・目盛りなど)を、最終の画像と同じ方法で作った静止画像 / 上の層 = 動く部分(レーダー・折れ線)だけを画面のSVGで重ねる。
// 動きが終わったら、完成した画像に差し替える。文字は最初から最後まで同じ静止画像なので、切り替わっても位置がずれない。
export async function openDetail(record, all, opts = {}) {
  closeDetail();
  const token = ++openToken;
  const layout = opts.layout ?? (window.innerWidth < 900 ? "narrow" : "wide");
  const { svg, width, height, hot, anim } = buildDetailSVG(record, all, { layout });
  const zoom = displayZoom(layout);
  const scale = opts.scale ?? Math.max(2, Math.ceil(zoom * (window.devicePixelRatio || 1)));
  const px = `${Math.round(width * zoom)}px`;
  overlay = document.createElement("div");
  overlay.className = "dd-overlay";
  const wrap = document.createElement("div");
  wrap.className = "dd-wrap";
  // 外枠の大きさは、画像ができる前(開いた直後)から決めておく(画像が出たときに、位置が動かないように)
  wrap.style.width = px; wrap.style.aspectRatio = `${width} / ${height}`;
  // 右上の「×」ボタン: 画面の部品として、画像の上に重ねる。画像(PNG)には含まれないので、保存した画像には写らない。Escキー、背景のクリック・タップでも閉じられる
  const btn = document.createElement("button");
  btn.className = "dd-close"; btn.type = "button"; btn.setAttribute("aria-label", "閉じる");
  btn.innerHTML = `<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" fill="none"/></svg>`;
  btn.addEventListener("click", closeDetail);
  // 暗い背景と「×」は、採点結果の画像が見えるのと同時に出す。画像の生成を待つあいだ(開いた直後)に、背景や「×」だけが先に出ないように、最初は隠しておく。
  // 背景は透明にするだけで、画面全体を覆う枠(overlay)は、開いた直後からある(待つあいだに、裏の表を、うっかり押さないように)
  btn.style.visibility = "hidden";
  overlay.style.background = "transparent";
  const showBtn = () => { btn.style.visibility = ""; overlay.style.background = ""; };
  const mkImg = (url, alt) => { const i = new Image(); i.className = "dd-img"; i.alt = alt; i.style.width = px; i.src = url; return i; };
  wrap.append(btn);
  overlay.appendChild(wrap);
  overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) closeDetail(); });
  document.addEventListener("keydown", onKey);
  document.body.appendChild(overlay);
  // 裏のページのスクロールを止める。ページ自体がスクロールする画面(静的サイト)では、スクロールバーが消えて、その幅の分(約15px)、裏の表が広がってしまう。
  // 消える幅(0のこともある: スマホの細いスクロールバー・Streamlit版のように、ページ自体はスクロールしない画面)の分だけ、右に余白を足して、表の幅を変えない。
  // 画面の幅を測るのは、スクロールを止める前(この時点では、まだ、スクロールバーがある)
  const scrollbarW = window.innerWidth - document.documentElement.clientWidth;
  document.body.style.overflow = "hidden";
  if (scrollbarW > 0) document.body.style.paddingRight = scrollbarW + "px";
  // OSの「視覚効果を減らす」の設定は、無視して、動きを出す(約1秒の短い動き)。設定を尊重したいときは、opts.respectReducedMotion = true
  const animate = opts.animate !== false && !(opts.respectReducedMotion && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  const fullPromise = svgToPngBlob(svg, width, height, scale);                       // 完成した静止画像 (保存用・最終表示)
  // 完成した画像の準備: 動きの終わりを待たずに、できしだい、ほぼ透明にして、重ねる。動きの最中に、右クリック・長押しで保存しても、完成した絵が保存される
  const alt = `${record.contentsName} ${record.totalPoint}点の採点結果`;
  const savePromise = (async () => {
    const blob = await fullPromise;
    if (token !== openToken) return null;
    objUrl = URL.createObjectURL(blob);
    const im = mkImg(objUrl, alt);
    try { await im.decode(); } catch { /* そのまま表示 */ }
    if (token !== openToken) return null;
    im.dataset.pxw = String(Math.round(width * scale)); im.dataset.pxh = String(Math.round(height * scale));
    return im;
  })();
  let stage = null;
  if (animate) {
    const staticSvg = svg.replace("</defs>", "</defs><style>[data-a]{display:none}</style>");   // 動く部分(data-a)を除いた静止画像
    const staticBlob = await svgToPngBlob(staticSvg, width, height, scale);
    if (token !== openToken) return;
    staticUrl = URL.createObjectURL(staticBlob);
    const base = mkImg(staticUrl, "");
    try { await base.decode(); } catch { /* そのまま表示 */ }
    if (token !== openToken) return;
    const holder = document.createElement("div");
    holder.className = "dd-anim";
    holder.innerHTML = svg;
    const el = holder.firstElementChild;
    pruneToAnimated(el);                                          // 動く部分(data-a)と、その入れ物・定義だけを残す: 背景や文字は、下の静止画像が担当する
    el.setAttribute("width", String(Math.round(width * zoom))); el.setAttribute("height", String(Math.round(height * zoom)));   // 大きさは、CSSの自動計算に頼らず、数値で指定する(iPhoneのブラウザ対策)
    stage = document.createElement("div");
    stage.className = "dd-stage";
    stage.append(base, holder);
    wrap.append(stage);
    showBtn();
    // 動きは、すぐ始める(完成した画像の生成を、待たない)。完成した画像(保存用)は、できしだい、ほぼ透明にして、一番上に重ねる。
    // できるまでの間(動きの最初の約0.4秒)は、下の層の静止画像を保存の対象から外してある(detail.css)ので、レーダーやグラフのない絵が、保存されることはない
    savePromise.then((im) => { if (im && token === openToken && !im.isConnected) { im.classList.add("dd-save"); stage.append(im); } });
    if (!(await playIntro(el, anim, () => token !== openToken))) return;
  }
  const img = await savePromise;
  if (!img || token !== openToken) return;
  // 動きが終わっても、下の層(静止画像)と上の層(動いたSVG)は、そのまま見せ続ける(完成した画像に差し替えると、線のにじみ方が変わって、切り替わりが見えるため)。
  // 完成した画像(保存用)は、ほぼ透明にして、真上に重ねる。右クリック・長押しの保存と、マウスを乗せたときの吹き出しは、この画像で受ける。
  if (!img.isConnected) { if (stage) { img.classList.add("dd-save"); stage.append(img); } else wrap.append(img); }
  showBtn();
  attachHover(wrap, img, hot, zoom);
}