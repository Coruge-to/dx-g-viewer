"""「その他集計」の2つの区画(最高点別の曲数・ビブラートタイプ)を、SVGの文字列として作る。

各区画は、見出し・グラフ・説明文を、1枚のSVGにまとめている。
 - 画面では、そのまま表示する(棒が下から伸びる/円の扇が広がる動きは、app.py のCSSで付ける)
 - 動きが終わったら、ページ側のスクリプトが、同じSVGから、PNG画像(<img>)を作って差し替える
   → 右クリックの「画像を保存」・スマホの長押しで、区画ごとに保存できる
スクリプトを使わない純粋なSVGなので、Streamlitの st.markdown(unsafe_allow_html=True) にそのまま入る。
"""
from __future__ import annotations

import math
from html import escape

STACK_COLORS = ["#7cb5ec", "#434348", "#90ed7d", "#f7a35c", "#8085e9"]
STACK_LABELS = [".0～.2", ".2～.4", ".4～.6", ".6～.8", ".8～"]
PIE_COLORS = ["#7cb5ec", "#434348", "#90ed7d", "#f7a35c", "#8085e9", "#f15c80", "#e4d354", "#2b908f", "#f45b5b", "#91e8e1"]
FONT = "Arial, 'Yu Gothic', sans-serif"          # 表と同じフォント
TITLE_H = 40                                      # 見出しの高さ
LABEL_GAP = 24                                    # PC用の円グラフ: ラベルの右端と、円の左端の間(線を通す幅)
EDGE = 3                                          # PC用の円グラフ: 区画の左端・円の右端の、余白(狭くてよい)
BAR_T, BAR_B = 26, 68                             # 棒グラフの、グラフ本体の上の余白(=一番上の目盛り線の位置)と、下の余白
AXIS_LABEL_DROP = 18                              # 棒グラフのx軸の文字の下端は、グラフの底(0の線)より、約18px下
NOTE_LH = 19                                      # 説明文の行の高さ


def _f(v: float) -> str:
    return ("%.2f" % v).rstrip("0").rstrip(".")


def _section(W: int, title: str, body: str, body_h: float, notes: list[str], body_top: float = 0.0, center_notes: bool = False) -> str:
    """見出し + グラフ(body) + 説明文 を、1枚のSVGにまとめる。body_top は、グラフ内の座標の最小の y(負なら、その分を上に足す)"""
    shift = TITLE_H - body_top
    notes_y = TITLE_H + (body_h - body_top) + 14
    H = notes_y + NOTE_LH * len(notes) + 6
    o = [f'<svg class="others-chart" viewBox="0 0 {W} {_f(H)}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}" font-weight="bold" role="img" aria-label="{escape(title)}">',
         f'<rect width="{W}" height="{_f(H)}" fill="#fff"/>',
         '<rect x="0" y="6" width="4" height="26" fill="#6f6fd8"/>',
         f'<text x="14" y="25" font-size="16" fill="#333">{escape(title)}</text>',
         f'<line x1="0" y1="{TITLE_H - 2}" x2="{W}" y2="{TITLE_H - 2}" stroke="#ccc"/>',
         f'<g transform="translate(0 {_f(shift)})">{body}</g>']
    texts = [f"・{n}" for n in notes]
    # 説明文は、全体を「ひとかたまり」として、区画の左右中央に置く(各行は、左揃えのまま)。center_notes=False のときは、左端
    nx = (W - max(_text_w(t, 13, 1.0) for t in texts)) / 2 if center_notes and texts else 4
    for i, t in enumerate(texts):
        o.append(f'<text x="{_f(nx)}" y="{_f(notes_y + NOTE_LH * i + 13)}" font-size="13" font-weight="normal" fill="#333">{escape(t)}</text>')
    o.append("</svg>")
    return "".join(o)


def best_scores_section(best_scores: list[tuple[float, float]], lo: int = 90, W: int = 440, fs: int = 11, body_h: int | None = None, center_notes: bool = False) -> str:
    """最高点別の曲数(積み上げ棒グラフ)。best_scores: 曲ごとの (最高点, その記録のボーナス点)。
    列は、lo〜99, 100, 100+ の12列を固定で出す(該当する曲が0でも、列は残して「0」と出す)"""
    cats = [str(n) for n in range(lo, 100)] + ["100", "100+"]
    counts = {c: [0] * 5 for c in cats}
    for score, bonus in best_scores:
        if score < lo:
            continue
        if score >= 100:
            counts["100+" if abs(bonus) < 0.0005 else "100"][0] += 1
            continue
        ip = int(math.floor(score + 1e-9))
        counts[str(ip)][min(int((score - ip) * 5 + 1e-9), 4)] += 1
    totals = [sum(counts[c]) for c in cats]
    ymax = max(150, int(math.ceil(max(totals + [1]) / 25.0) * 25))

    wide = W >= 450
    H = body_h or (214 if wide else 280)
    L, R, T, B = (52 if wide else 54), 8, BAR_T, BAR_B
    pw, ph = W - L - R, H - T - B
    Y = lambda v: T + ph - v / ymax * ph
    n = len(cats)
    slot = pw / n
    bw = slot * (0.52 if wide else 0.6)
    o = []
    for v in range(0, ymax + 1, 25):
        o.append(f'<line x1="{L}" y1="{_f(Y(v))}" x2="{W - R}" y2="{_f(Y(v))}" stroke="#e6e6e6"/>')
        o.append(f'<text x="{L - 8}" y="{_f(Y(v) + 4)}" text-anchor="end" font-size="{fs}" fill="#666">{v}</text>')
    o.append(f'<line x1="{L}" y1="{_f(Y(0))}" x2="{W - R}" y2="{_f(Y(0))}" stroke="#ccd6eb" stroke-width="1"/>')
    o.append(f'<text x="10" y="{_f(T + ph / 2)}" font-size="{fs}" fill="#666" text-anchor="middle" transform="rotate(-90 10 {_f(T + ph / 2)})">曲数</text>')
    for i, c in enumerate(cats):
        x = L + slot * i + (slot - bw) / 2
        acc = 0
        o.append(f'<g class="ob" style="transform-origin:{_f(x + bw / 2)}px {_f(Y(0))}px">')
        for k in range(5):
            cnt = counts[c][k]
            if not cnt:
                continue
            y1, y0 = Y(acc + cnt), Y(acc)
            o.append(f'<rect x="{_f(x)}" y="{_f(y1)}" width="{_f(bw)}" height="{_f(y0 - y1)}" fill="{STACK_COLORS[k]}"><title>{escape(c)}点 {STACK_LABELS[k]}: {cnt}曲</title></rect>')
            acc += cnt
        o.append("</g>")
        o.append(f'<text class="ob-num" x="{_f(L + slot * i + slot / 2)}" y="{_f(Y(acc) - 6)}" text-anchor="middle" font-size="{fs + 1}" fill="#555">{acc}</text>')   # 件数: 定位置で、ふわっと出る(棒が、ほぼ伸び切るころから)
        o.append(f'<text x="{_f(L + slot * i + slot / 2)}" y="{_f(Y(0) + 15)}" text-anchor="middle" font-size="{fs}" fill="#666">{escape(c)}</text>')
    o.append(f'<text x="{_f(L + pw / 2)}" y="{_f(Y(0) + 31)}" text-anchor="middle" font-size="{fs}" fill="#666">点数</text>')
    # 凡例 (枠つき)
    lw = [len(l) * (fs - 4) + 22 for l in STACK_LABELS]
    total_w = sum(lw) + 14 * 4 + 24
    x = W / 2 - total_w / 2
    yb = H - 14
    o.append(f'<rect x="{_f(x)}" y="{yb - 13}" width="{_f(total_w)}" height="24" fill="#fff" stroke="#ccc"/>')
    x += 12
    for k, lab in enumerate(STACK_LABELS):
        o.append(f'<rect x="{_f(x)}" y="{_f(yb - 6.5)}" width="11" height="11" fill="{STACK_COLORS[k]}"/>')   # 枠(高さ24)の上下中央(yb-1)に、■と文字を置く
        o.append(f'<text x="{_f(x + 15)}" y="{_f(yb - 1 + fs * 0.36)}" font-size="{fs}" fill="#333">{escape(lab)}</text>')
        x += lw[k] + 14
    return _section(W, "最高点別の曲数", "".join(o), H, ["最高点が何点の曲が何曲あるかを表しています", "ボーナス点が0点の100点を「100+」と表します"], center_notes=center_notes)


def _text_w(s: str, fs: int, margin: float = 1.04) -> float:
    """太字の文字列の、おおよその幅(単位は、描画の座標)。半角は文字ごとの係数、全角は fs"""
    w = 0.0
    for ch in s:
        if ch.isdigit():
            w += 0.57 * fs
        elif ch in " .:":
            w += 0.32 * fs
        elif ch == "-":
            w += 0.36 * fs
        elif ch == "%":
            w += 0.92 * fs
        elif ch.isascii():
            w += (0.74 if ch.isupper() else 0.62) * fs
        else:
            w += fs
    return w * margin                                 # 見積もりの誤差の分の、余裕(既定は4%)


def _pie_r(body_h: float) -> float:
    """PC用の円の半径: 円の全体が、棒グラフの「150の線〜0の線」の高さ(グラフ領域)に収まる大きさ"""
    return (body_h - BAR_T - BAR_B) / 2


def pie_min_width(items: list[tuple[str, int]], fs: int = 13, body_h: float = 300) -> int:
    """PC用の円グラフ(ラベルを左の1列に並べる)の区画の幅を、ラベルの長さにぴったり合わせた値にする(円の左に、余白を残さない)"""
    total = sum(c for _, c in items) or 1
    label_w = max(_text_w(f"{name}: {cnt / total * 100:.1f} %", fs) for name, cnt in items) if items else 0
    r = _pie_r(body_h)
    return int(math.ceil(2 * r + LABEL_GAP + 2 * EDGE + label_w))


def _left_labels(pts: list[dict], cx: float, cy: float, r: float, fs: int, bottom_y: float, x_lab: float) -> list[str]:
    """PC用: ラベルを、すべて、円の左の1列(右揃え)に並べる。線は、各扇の左側の弧につなぐ。
    扇が左半分(180〜360度)にかかるなら、その部分の真ん中、右半分だけなら、180度に近い端につなぐ。
    上下の順に並べ、重なるときは、間隔(fs+6)を空けて、下へずらす"""
    out = []
    for p in pts:
        lo, hi = max(p["a0"], 180.0), min(p["a1"], 360.0)
        a = (lo + hi) / 2 if lo < hi else p["a1"] - min(4.0, (p["a1"] - p["a0"]) / 2)
        s, c_ = math.sin(math.radians(a)), math.cos(math.radians(a))
        p["ex"], p["ey"] = cx + r * s, cy - r * c_
        p["kx"], p["ky"] = cx + (r + 9) * s, cy - (r + 9) * c_
        p["ly"] = p["ky"]
    order = sorted(pts, key=lambda p: p["ly"])
    pitch = fs + 6
    order[0]["ly"] = max(order[0]["ly"], fs * 0.8 + 14)
    for k in range(1, len(order)):
        order[k]["ly"] = max(order[k]["ly"], order[k - 1]["ly"] + pitch)
    over = order[-1]["ly"] - (bottom_y - fs * 0.4)         # 最下段のラベルの下端が、円の下端(bottom_y)を越えないようにする
    if over > 0:
        for p in order:
            p["ly"] -= over
    for p in order:
        out.append(f'<path d="M{_f(p["ex"])} {_f(p["ey"])}L{_f(p["kx"])} {_f(p["ky"])}L{_f(x_lab + 6)} {_f(p["ly"])}" stroke="{p["col"]}" fill="none"/>')
        out.append(f'<text x="{_f(x_lab)}" y="{_f(p["ly"] + fs * 0.36)}" text-anchor="end" font-size="{fs}" fill="#555">{escape(p["name"])}: {p["pct"]:.1f} %</text>')
    return out


def pie_section(items: list[tuple[str, int]], W: int = 420, fs: int = 12, r: int | None = None, labels_left: bool = False, body_h: float | None = None, center_notes: bool = False) -> str:
    """ビブラートタイプの割合(円グラフ)。items: [(表示名, 件数), ...] (多い順)。割合の表示は小数1桁"""
    total = sum(c for _, c in items) or 1
    wide = W >= 450
    if labels_left:                                       # PC用: 円を右に寄せ、ラベルを左の1列に並べる
        H = body_h or 300
        r = r or _pie_r(H)                                   # 棒グラフの「150の線〜0の線」の高さに、円の全体が収まる大きさ
        label_w = max(_text_w(f"{n}: {c_ / total * 100:.1f} %", fs) for n, c_ in items) if items else 0
        x_left = (W - (label_w + LABEL_GAP + 2 * r)) / 2     # ラベルと円を、ひとかたまりにして、区画の左右中央に置く
        x_lab = x_left + label_w                             # ラベルの右端
        # 縦の位置: 見出しの灰色の線(区画の座標で y=-2)と、説明文の先頭行の上端(y=body_h+17)の、ちょうど真ん中に、円の中心を置く
        cx, cy = x_lab + LABEL_GAP + r, (H + 15) / 2
    else:
        r = r or (90 if wide else 70)
        cx, cy = W / 2, (110 if wide else r + 28)
        H = cy + r + 8
    o = []
    C = math.pi * r                                       # マスクの円(半径 r/2)の円周
    mid_id = f"pm{W}"
    o.append(f'<defs><mask id="{mid_id}"><circle class="sweep" style="--c:{_f(C)}px" cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r / 2)}" fill="none" stroke="#fff" stroke-width="{_f(r)}" stroke-dasharray="{_f(C)}" stroke-dashoffset="0" transform="rotate(-90 {_f(cx)} {_f(cy)})"/></mask></defs><g mask="url(#{mid_id})">')
    ang = 0.0                                             # 0 = 真上。時計回り
    pts = []
    for i, (name, cnt) in enumerate(items):
        span = cnt / total * 360.0
        a0, a1 = ang, ang + span
        mid = math.radians((a0 + a1) / 2)
        col = PIE_COLORS[i % len(PIE_COLORS)]
        x0, y0 = cx + r * math.sin(math.radians(a0)), cy - r * math.cos(math.radians(a0))
        x1, y1 = cx + r * math.sin(math.radians(a1)), cy - r * math.cos(math.radians(a1))
        tip = f"<title>{escape(name)}: {cnt}曲 ({cnt / total * 100:.1f}%)</title>"
        if span >= 359.99:
            o.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{r}" fill="{col}">{tip}</circle>')
        else:
            o.append(f'<path d="M{_f(cx)} {_f(cy)}L{_f(x0)} {_f(y0)}A{r} {r} 0 {1 if span > 180 else 0} 1 {_f(x1)} {_f(y1)}Z" fill="{col}" stroke="#fff" stroke-width="1">{tip}</path>')
        pts.append({"name": name, "pct": cnt / total * 100, "col": col, "sin": math.sin(mid), "cos": math.cos(mid), "a0": a0, "a1": a1})
        ang = a1
    o.append("</g>")
    o.append('<g class="fadein">')                       # ラベルと線は、扇が広がり終わるころに、ふわっと出す
    if labels_left:
        o.extend(_left_labels(pts, cx, cy, r, fs, cy + r, x_lab))
        o.append("</g>")
        return _section(W, "ビブラートタイプ", "".join(o), H, ["上位5つとその他の割合を表しています"], center_notes=center_notes)
    # ラベルの置き方: 円の右側(時計回りで下半分に入る扇)は、扇の外側にそのまま置く。
    # 円の上端に集まる小さい扇(左上〜真上)のラベルは、円の左側に、縦に並べる(上へ積み上げると、円の上に空白ができて、高さが増えるため)。
    pitch = fs + 5
    right = [p for p in pts if p["sin"] >= 0]
    left = [p for p in pts if p["sin"] < 0]
    for p in right:
        p["ly"] = cy - (r + 18) * p["cos"]
    right.sort(key=lambda p: p["ly"])
    for k in range(1, len(right)):
        if right[k]["ly"] - right[k - 1]["ly"] < pitch:
            right[k]["ly"] = right[k - 1]["ly"] + pitch
    # 左側は、扇の中心の高さを基準にして、近いものを避けて並べる(下から上へ)
    for p in left:
        p["ly"] = cy - (r + 8) * p["cos"]
    left.sort(key=lambda p: -p["ly"])
    for k in range(1, len(left)):
        if left[k - 1]["ly"] - left[k]["ly"] < pitch:
            left[k]["ly"] = left[k - 1]["ly"] - pitch
    # 左側の最上段が、円の上端(cy - r)より上へ出る分だけ、左側の全体を下へ寄せる(上へ出さない)
    over = (cy - r - 4) - min([p["ly"] for p in left] + [cy])
    if over < 0:
        for p in left:
            p["ly"] -= over
    pad = 26 if wide else 20
    for side, group in ((1, right), (-1, left)):
        for p in group:
            ex, ey = cx + r * p["sin"], cy - r * p["cos"]
            kx, ky = cx + (r + 10) * p["sin"], cy - (r + 10) * p["cos"]
            lx = cx + side * (r + pad)
            o.append(f'<path d="M{_f(ex)} {_f(ey)}L{_f(kx)} {_f(ky)}L{_f(lx - side * 5)} {_f(p["ly"])}" stroke="{p["col"]}" fill="none"/>')
            o.append(f'<text x="{_f(lx)}" y="{_f(p["ly"] + fs * 0.36)}" text-anchor="{"start" if side == 1 else "end"}" font-size="{fs}" fill="#555">{escape(p["name"])}: {p["pct"]:.1f} %</text>')
    o.append("</g>")
    ys = [p["ly"] for p in pts]
    top = min([cy - r] + [y - fs for y in ys])             # ラベルが、円の上へはみ出した分だけ、領域を広げる(通常は、ほぼ0)
    bottom = max([cy + r] + [y + fs for y in ys])
    H = bottom + 8
    return _section(W, "ビブラートタイプ", "".join(o), H, ["上位5つとその他の割合を表しています"], body_top=min(top, 0.0))
