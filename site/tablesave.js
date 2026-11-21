// 表(その1ページ分)を、画像(PNG)にして、表の真上に、ほぼ透明で重ねる。
// 右クリックの「画像を保存」・スマホの長押しの「写真に保存」は、重ねた画像(見えている部分全体 = 見出し + そのページの行)が保存される。
//
// ふだんは、重ねた画像は、クリックを通す(点数のクリック・見出しの並べ替え・日付や曲名のリンク・ホバーは、今までどおり動く)。
// 右クリックを押した瞬間、または、スマホで指を約0.2秒置いた瞬間だけ、重ねた画像が、クリックを受ける状態に切り替わり、
// ブラウザのメニュー(画像を保存)は、この画像に対して出る。
//
// 画像の作り方: 表の見た目(HTML+CSS)を、そのまま SVG の foreignObject に入れて、画像として読み込み、canvas に描いて PNG にする。
//   - 画面の拡大(zoom)は、画像では、外す(レイアウトの幅のまま作り、解像度で、拡大の分をまかなう)。
//   - 固定表示(sticky)の見出しは、画像では、通常の位置に置く。
//   - SVGの画像の中では、画面の幅(vw)の基準が、画像の幅になるので、vw を使う余白(--pc-td-pad-txt)は、画面で実際に使われている値(px)に、固定する。
const SELECTORS = [".view-pc .pc-table-wrapper", ".view-sp"];     // 画面に見えているほうだけを、画像にする(PC用・スマホ用)
const MAX_PIXELS = 15e6;                                          // iPhone の canvas は、約1677万画素まで。余裕を見て、1500万画素以下にする
const PAD_X = 16, PAD_Y = 16;                                     // 保存する画像の、周りの白い余白(上下左右とも16px)。左右は、スマホの画面の左右の余白(16px)を超えないようにする(超えると、横にスクロールできてしまう)ので、上下も、16pxにそろえる。画面の表示では、この余白の分を、はみ出させて、表の大きさと位置を変えない
// 画像の長い辺(px)の上限。既定では、実質、設けない(面積の上限 MAX_PIXELS だけが効く)。実機で、画像が大きすぎて保存できない場合に備えて、
// ページのアドレスの末尾に「&tsmax=8192」のように付けると、その数字(px)に抑えられる。(実機の試験で、既定の大きさ(スマホ版は約1150x11450px)でも、長押しで保存できることを確認した)
const MAX_SIDE = Number(new URLSearchParams(location.search).get("tsmax")) || 1e9;
// 表の高さは、画面の表から決めると、iPhone の実機で、画像の中の表が、少し高く描かれたとき、下の行が、切れてしまう。
// そこで、高さに、この倍率の余裕を足して描き、実際に描かれた中身の下端を、画素から測って、その高さで切り出す。
const SLACK = 1.3;
const TEST_LH = new URLSearchParams(location.search).get("tslh");    // 試験用: 行の高さの倍率を、わざと変えて、切れないことを確かめる(例: &tslh=1.9)
// 実機での確認用: ページのアドレスの末尾に「&tsdebug=1」を付けると、画面の左下に、表の画像の作成の状況(時間・大きさ・エラー)を出す
const DEBUG = new URLSearchParams(location.search).get("tsdebug");
function status(msg) {
  if (!DEBUG) return;
  let d = document.getElementById("tablesave-status");
  if (!d) {
    d = document.createElement("div"); d.id = "tablesave-status";
    d.style.cssText = "position:fixed;left:4px;bottom:4px;z-index:99999;background:rgba(0,0,0,.78);color:#fff;font:11px/1.4 monospace;padding:4px 6px;border-radius:4px;max-width:92vw;pointer-events:none;white-space:pre-wrap";
    document.body.appendChild(d);
  }
  d.textContent = msg;
}
const HOLD_MS = 180;                                            // スマホで、この時間(ミリ秒)、指を置き続けたら、長押しの準備をする
const MOVE_PX = 8;                                                // 指がこれ以上動いたら、スクロールと見なして、長押しの準備をやめる

const isVisible = (el) => !!el && el.getBoundingClientRect().width > 0;

function injectStyle() {
  if (document.getElementById("tablesave-style")) return;
  const st = document.createElement("style");
  st.id = "tablesave-style";
  st.textContent = ".tbl-ovl{position:absolute;left:0;top:0;width:100%;height:100%;z-index:6;pointer-events:none}"
    + ".tbl-ovl img{display:block;width:100%;height:100%;opacity:.01;pointer-events:none;-webkit-touch-callout:default}"
    + ".tbl-ovl.on img{pointer-events:auto}";
  document.head.appendChild(st);
}

// 表の見た目を、画像にする
async function tableToBlob(live) {
  const r = live.getBoundingClientRect();
  const cs = getComputedStyle(live);
  const W = Math.round(parseFloat(cs.width));                   // レイアウトの幅(拡大前)
  const z = r.width / parseFloat(cs.width) || 1;                // 画面の拡大率
  const H = Math.ceil(r.height / z);
  const css = [...document.querySelectorAll("style")].map((s) => s.textContent).filter((t) => t.includes(".dxg-table")).join("\n")
    .replace(/zoom:\s*var\(--tbl-zoom\)/g, "zoom:1");
  const clone = live.cloneNode(true);
  clone.style.zoom = "1";
  clone.style.position = "static";
  // 固定表示(sticky)を、通常の位置に直す: 生の要素と、写しの要素は、同じ順番で並んでいる
  const liveEls = [live, ...live.querySelectorAll("*")], cloneEls = [clone, ...clone.querySelectorAll("*")];
  liveEls.forEach((le, i) => {
    if (getComputedStyle(le).position === "sticky") { cloneEls[i].style.position = "static"; cloneEls[i].style.top = "auto"; }
  });
  // vw を使う余白を、画面で実際に使われている値に固定する
  const txt = live.querySelector(".pc-txt-cell");
  const padFix = txt ? ":root{--pc-td-pad-txt:" + getComputedStyle(txt).paddingLeft + "}" : "";
  const holder = document.createElement("div");
  holder.setAttribute("xmlns", "http://www.w3.org/1999/xhtml");
  // 文字の基本設定(行の高さ・文字の大きさ・字体・色など)は、ページ全体から引き継がれる値なので、画像の中では、既定値に戻ってしまう(行の高さが、変わる)。
  // 画面で実際に使われている値を、そのまま固定する
  const ps = getComputedStyle(live.parentElement || live);
  holder.style.cssText = "width:" + W + "px;background:#fff;";
  // 行の高さは、px換算の値ではなく、文字の大きさに対する「倍率」で固定する(表の中は、文字の大きさがそれぞれ違うので、倍率のまま引き継がれて効いている)
  const lh = ps.lineHeight === "normal" ? "normal" : String(parseFloat(ps.lineHeight) / parseFloat(ps.fontSize));
  holder.style.fontFamily = ps.fontFamily; holder.style.fontSize = ps.fontSize; holder.style.lineHeight = TEST_LH || lh;
  holder.style.color = ps.color; holder.style.fontWeight = ps.fontWeight; holder.style.letterSpacing = ps.letterSpacing;
  const st = document.createElement("style");
  st.textContent = css + padFix;
  holder.append(st, clone);
  const xml = new XMLSerializer().serializeToString(holder);
  const Hs = Math.ceil(H * SLACK);                              // 余裕を足した高さ
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + Hs + '"><foreignObject x="0" y="0" width="' + W + '" height="' + Hs + '">' + xml + "</foreignObject></svg>";
  // 注意: blob: のアドレスだと、canvas から画像を取り出せなくなる(汚染される)ので、data: のアドレスにする
  const img = new Image();
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  await img.decode();
  const ideal = Math.max(2, Math.ceil(z * (window.devicePixelRatio || 1)));
  // 実際に描かれた表の下端を測る: 小さい倍率(1/4)で描いて、白でない最後の行を、下から探す(重い描画を増やさないため、小さく描く)
  const measure = () => {
    const k = 0.25, c = document.createElement("canvas");
    c.width = Math.max(1, Math.round(W * k)); c.height = Math.max(1, Math.round(Hs * k));
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(img, 0, 0, c.width, c.height);
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    for (let y = c.height - 1; y >= 0; y--) {
      for (let x = 0; x < c.width; x++) {
        const i = (y * c.width + x) * 4;
        if (d[i] < 250 || d[i + 1] < 250 || d[i + 2] < 250) return (y + 1) / k;
      }
    }
    return 0;
  };
  let measured = 0;
  for (let attempt = 0; attempt < 3 && !(measured > H * 0.5); attempt++) {
    if (attempt) await new Promise((res) => setTimeout(res, 200));                     // 空に描かれたときは、少し待って、描き直す
    try { measure(); measured = measure(); } catch (e) { status("測定に失敗: " + e); break; }   // 1回目は、WebKit で、空に描かれることがあるので、空打ち。失敗しても、続ける
  }
  // 下端の近くだけ、細かく測り直す(上の測定は、4px刻みなので、余白が、ずれる): 下端の前後の細い帯を、2倍の大きさで描いて、白でない最後の行を探す
  let exact = 0;
  if (measured > H * 0.5) {
    try {
      const y0 = Math.max(0, Math.floor(measured) - 20), hs = Math.min(Hs - y0, 48), k2 = 2;
      const c2 = document.createElement("canvas"); c2.width = Math.round(W * k2); c2.height = Math.round(hs * k2);
      const x2 = c2.getContext("2d", { willReadFrequently: true });
      x2.fillStyle = "#fff"; x2.fillRect(0, 0, c2.width, c2.height);
      x2.drawImage(img, 0, y0, W, hs, 0, 0, c2.width, c2.height);
      const d2 = x2.getImageData(0, 0, c2.width, c2.height).data;
      scan: for (let y = c2.height - 1; y >= 0; y--) {
        for (let x = 0; x < c2.width; x++) { const i = (y * c2.width + x) * 4; if (d2[i] < 250 || d2[i + 1] < 250 || d2[i + 2] < 250) { exact = y0 + (y + 1) / k2; break scan; } }
      }
    } catch (e) { status("下端の細かい測定に失敗: " + e); }
  }
  // 測れなかったときは、荒い測定の値に4pxの余裕、それも無理なら、画面の表の高さに4%の余裕(画像の中の表は、画面の表より、1〜2%高く描かれるため)を足す
  const Hc = exact ? Math.min(Hs, Math.ceil(exact)) : (measured > H * 0.5 ? Math.min(Hs, Math.ceil(measured) + 4) : Math.min(Hs, Math.ceil(H * 1.04)));
  const TW = W + 2 * PAD_X, TH = Hc + 2 * PAD_Y;                // 余白を含めた、画像の大きさ(レイアウトのpx)
  const scale = Math.min(ideal, Math.sqrt(MAX_PIXELS / (TW * TH)), MAX_SIDE / Math.max(TW, TH));
  const draw = () => {
    const c = document.createElement("canvas");
    c.width = Math.round(TW * scale); c.height = Math.round(TH * scale);
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(img, 0, 0, W, Hc, PAD_X * scale, PAD_Y * scale, W * scale, Hc * scale);   // 元の画像の、上から Hc までを、切り出して描く
    return c;
  };
  const c = draw();                                             // 本番の描画は、1回だけ(重いので)
  status("高さ 画面の表 " + H + " / 画像の表 " + Hc + " / 倍率 " + scale.toFixed(2) + " / " + c.width + "x" + c.height);
  console.log("tablesave: 高さ 画面の表 " + H + " / 実際に描かれた表 " + Hc + " (差 " + (Hc - H) + "px)");
  return await new Promise((res) => c.toBlob(res, "image/png"));
}

// 重ねる画像を、表の真上に置く
async function placeOverlay(live, blob, label) {
  if (getComputedStyle(live).position === "static") live.style.position = "relative";
  const ovl = document.createElement("div");
  ovl.className = "tbl-ovl";
  // 余白の分だけ、表の外へ広げて重ねる(画像の中の表は、画面の表とぴったり重なる)
  ovl.style.left = -PAD_X + "px"; ovl.style.top = -PAD_Y + "px";
  ovl.style.width = "calc(100% + " + 2 * PAD_X + "px)"; ovl.style.height = "calc(100% + " + 2 * PAD_Y + "px)";
  const img = new Image();
  img.alt = label;
  // 画像のアドレスは、blob: にする(採点結果画面・グラフと同じ)。右クリックの「画像を保存」の初期のファイル名が、毎回、違う名前(ランダムな文字列)になり、重ならない。
  // (data: にすると、名前の元がなく、いつも「ダウンロード.png」になって、2回目からは「ダウンロード (1).png」のように重なる)
  img.src = URL.createObjectURL(blob);
  // 画像の読み込み(デコード)が終わってから、画面に置く。読み込み中の画像を置くと、iPhone は、長押しの「コピー」で、画像ではなく、代替テキスト(alt)の文字を、コピーしてしまい、「写真に保存」も出ない
  await img.decode();
  if (!img.naturalWidth) throw new Error("画像を読み込めなかった");
  ovl.appendChild(img);
  // 重ねた画像が受けたクリック(タップ)は、その位置の下にある要素(点数セル・日付や曲名のリンク・見出しの並べ替え)へ、渡す
  ovl.addEventListener("click", (e) => {
    if (!touchMode) ovl.classList.remove("on");
    const below = document.elementsFromPoint(e.clientX, e.clientY).find((n) => n !== ovl && !ovl.contains(n));
    if (below) below.click();
  });
  if (touchMode) ovl.classList.add("on");
  live.appendChild(ovl);
  return ovl;
}

let building = false;
async function scan() {
  if (building) return;
  const live = SELECTORS.map((s) => document.querySelector(s)).find(isVisible);
  if (!live || live.dataset.tsave) return;
  live.dataset.tsave = "building";
  building = true;
  try {
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    const t0 = performance.now();
    status("表の画像を作成中…");
    const blob = await tableToBlob(live);
    if (!live.isConnected) return;
    await placeOverlay(live, blob, "歌唱履歴の表");
    live.dataset.tsave = "done";
    status("表の画像: 完了 " + Math.round(performance.now() - t0) + "ms, " + Math.round(blob.size / 1024) + "KB (長押しできます)");
    console.log("tablesave: 表の画像を作った", Math.round(performance.now() - t0), "ms,", Math.round(blob.size / 1024), "KB");
  } catch (e) {
    live.dataset.tsave = "error";
    status("表の画像: 失敗 " + e);
    console.error("tablesave: 表の画像を作れなかった(右クリック・長押しでの保存は、使えない)", e);
  } finally { building = false; }
}

// 右クリック・長押しの、検出
function overlayAt(target) {
  const root = target && target.closest && target.closest(".view-pc, .view-sp");
  return root ? root.querySelector(".tbl-ovl") : null;
}
let holdTimer = null, offTimer = null, down = null;
// タッチ端末(スマホ・タブレット)では、重ねた画像を、最初から、ずっと、押される状態にする。
// iPhone は、長押しの対象(画像か、リンクか)を、指が触れた瞬間に決めるので、触れた後に、切り替えたのでは、間に合わない。
// 代わりに、ふつうのタップは、重ねた画像が受けてから、下の要素へ渡す(placeOverlay の click)。
let touchMode = false;
const setTouchMode = () => { if (touchMode) return; touchMode = true; document.querySelectorAll(".tbl-ovl").forEach((o) => o.classList.add("on")); };
const turnOn = (ovl) => { clearTimeout(offTimer); ovl.classList.add("on"); };
const turnOff = (ovl, delay) => { if (touchMode) return; clearTimeout(offTimer); offTimer = setTimeout(() => ovl.classList.remove("on"), delay); };

export function initTableSave() {
  if (window.__tableSaveInit) return;
  window.__tableSaveInit = true;
  injectStyle();
  if (window.matchMedia && window.matchMedia("(pointer: coarse)").matches) touchMode = true;
  document.addEventListener("touchstart", setTouchMode, { once: true, passive: true, capture: true });   // 判定できなかったときの保険: 最初のタッチで、タッチ端末と見なす
  let timer = null;
  const later = () => { clearTimeout(timer); timer = setTimeout(scan, 400); };
  new MutationObserver(later).observe(document.body, { childList: true, subtree: true });
  window.addEventListener("resize", later);
  later();

  document.addEventListener("pointerdown", (e) => {
    const ovl = overlayAt(e.target);
    if (!ovl || touchMode) return;
    if (e.pointerType === "mouse") {
      if (e.button === 2) turnOn(ovl);                           // 右ボタン: メニューが出る前に、重ねた画像を、クリックを受ける状態にする
      else turnOff(ovl, 0);
      return;
    }
    down = { x: e.clientX, y: e.clientY, ovl };                  // タッチ: 指を置き続けたら、長押しの準備
    clearTimeout(holdTimer);
    holdTimer = setTimeout(() => { if (down) turnOn(down.ovl); }, HOLD_MS);
  }, true);
  document.addEventListener("pointermove", (e) => {
    if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) > MOVE_PX) { clearTimeout(holdTimer); turnOff(down.ovl, 0); down = null; }
  }, true);
  const end = (e) => {
    clearTimeout(holdTimer);
    if (down) { const o = down.ovl; down = null; turnOff(o, 1500); }                      // 長押しのメニューが出る間は、少し、そのままにする
    else if (e.pointerType === "mouse" && e.button === 2) { const o = overlayAt(e.target); if (o) turnOff(o, 1500); }
  };
  document.addEventListener("pointerup", end, true);
  document.addEventListener("pointercancel", end, true);
}
