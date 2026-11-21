"""公式DAM★ともの採点結果の画像(数字・ビブラート波形)を、拡大・平滑化してSVGパスに変換し site/assets.js の元データを作る。

事前に、公式の画像 (https://www.clubdam.com/images/damtomo/streaming/seimitsu/ の number/・vibratoType/) を
tools/dam_img/ に number__0.png, vibratoType__1.png ... の名前で保存しておく (画像そのものはリポジトリに含めない)。
使い方: python tools/build_assets.py 出力先.js  (potracer, numpy, scipy, pillow が必要)

メーター(ダイヤ・安定性・リズム)の点灯パターンも画像から読み取って出力する。
"""
import json
import sys
from pathlib import Path

import numpy as np
import potrace
from PIL import Image

D = Path(__file__).parent / "dam_img"
OUT = Path(sys.argv[1])
U = 8  # 拡大率 (拡大→二値化→ベクトル化で、ドット絵のギザギザを滑らかにする)


def load(name):
    return Image.open(D / name).convert("RGBA")


def upsample(im):
    a = np.asarray(im).astype(np.float32)
    A = a[..., 3:4] / 255.0
    pm = np.concatenate([a[..., :3] * A, a[..., 3:4]], axis=2)           # 乗算済みαで補間 (縁の色にじみ防止)
    big = [np.asarray(Image.fromarray(pm[..., c]).resize((im.width * U, im.height * U), Image.BICUBIC)) for c in range(4)]
    big = np.stack(big, axis=2).astype(np.float32)
    alpha = np.clip(big[..., 3], 0, 255)
    rgb = big[..., :3] / np.maximum(alpha[..., None] / 255.0, 1e-3)
    return np.clip(rgb, 0, 255), alpha


def trace(mask, turd=40, alphamax=1.0, opttol=0.4):
    bm = potrace.Bitmap(~mask)  # potracer は「暗い画素=前景」なので反転して渡す
    plist = bm.trace(turdsize=turd, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY, alphamax=alphamax, opticurve=True, opttolerance=opttol)
    f = lambda v: ("%.1f" % (v / U)).rstrip("0").rstrip(".")
    d = []
    for curve in plist:
        s = curve.start_point
        d.append(f"M{f(s.x)} {f(s.y)}")
        for seg in curve.segments:
            if seg.is_corner:
                d.append(f"L{f(seg.c.x)} {f(seg.c.y)}L{f(seg.end_point.x)} {f(seg.end_point.y)}")
            else:
                d.append(f"C{f(seg.c1.x)} {f(seg.c1.y)} {f(seg.c2.x)} {f(seg.c2.y)} {f(seg.end_point.x)} {f(seg.end_point.y)}")
        d.append("Z")
    return "".join(d)


def glyph(name, kind="digit", out_thr=190, inn_min=150):
    im = load(name)
    rgb, alpha = upsample(im)
    out = alpha > out_thr                                          # ふちの外形 (高いほどふちが細くなる)
    if kind == "digit":
        inn = (alpha > 200) & (rgb.min(axis=2) > inn_min)         # 白〜薄紫の内側
    elif kind == "ten":
        inn = (alpha > 200) & (rgb[..., 0] > 200) & (rgb[..., 1] > 170)  # 点の黄色い内側
    elif kind == "dot":
        inn = (alpha > 200) & (rgb.min(axis=2) > 170)
    else:
        raise ValueError(kind)
    return {"w": im.width, "h": im.height, "out": trace(out), "inn": trace(inn)}


assets = {"digits": {}, "sdigits": {}}
for i in range(10):
    assets["digits"][str(i)] = glyph(f"number__{i}.png")
    assets["sdigits"][str(i)] = glyph(f"number__s_{i}.png")
assets["dot"] = glyph("number__dot.png", "dot")
assets["ten"] = glyph("number__ten.png", "ten")
assets["h100"] = glyph("number__100.png", out_thr=110, inn_min=170)

# --- ビブラートの波形: 枠+波形 を緑のコア/グローの2層に。右下のラベル(白文字+黒ふち)は除外して、文字は別に描く ---
vib = []
for i in range(15):
    im = load(f"vibratoType__{i}.png")
    rgb, alpha = upsample(im)
    H, W = alpha.shape
    yy, xx = np.mgrid[0:H, 0:W]
    white = (rgb.min(axis=2) > 190) & (alpha > 160)
    black = (rgb.max(axis=2) < 70) & (alpha > 160)
    label_zone = (xx > 66 * U) & (yy > 24 * U)
    label = (white | black) & label_zone
    # ラベルの輪郭の滲み(緑との混色)も落とすため少し膨らませる
    from scipy.ndimage import binary_dilation  # noqa: E402
    label = binary_dilation(label, iterations=int(1.2 * U))
    glow = (alpha > 90) & ~label
    # 波形の線は鮮やかな黄緑(G>=229)、枠の縁は暗い緑(G<=225)なので、色で分けて、枠の縁を含めずに波形だけを取り出す (山と谷は欠けない)
    core = (alpha > 200) & (rgb[..., 1] >= 229) & (rgb[..., 0] >= 125) & ~label
    # ラベル: 白い文字の形(lab)と、その黒いふち(labo)。波形の切り抜きと同じ画像から取るので、位置は必ず一致する
    lab_white = white & label_zone
    lab_outline = (white | black) & label_zone
    vib.append({"w": im.width, "h": im.height, "core": trace(core, turd=30), "lab": trace(lab_white, turd=4), "labo": trace(lab_outline, turd=4)})
assets["vib"] = vib

# --- メーターの点灯パターン (画像から読み取る) ---
def lum_profile(name, y):
    a = np.asarray(load(name)).astype(float)
    return (a[y, :, :3].mean(axis=1) * (a[y, :, 3] / 255.0))

# リズム: 7つのスロットの明暗を、スロット中心の明るさから判定
def slots(name, n, x0, x1, yrange):
    a = np.asarray(load(name)).astype(float)
    res = []
    w = (x1 - x0) / n
    for k in range(n):
        cx = int(x0 + (k + 0.5) * w)
        seg = a[yrange[0]:yrange[1], max(cx - 1, 0):cx + 2, :3].mean(axis=(0, 1))
        res.append(round(float(seg.mean())))
    return res

rhythm = {}
for t in range(1, 11):
    # スロット範囲は 5.png の明暗から決めた概算 (レンズの内側)。まず明るさ列を出して後で確認する
    rhythm[t] = slots(f"rhythm__{t}.png", 7, 13, 97, (14, 22))
assets["_rhythm_lum"] = rhythm

stab = {}
for n in range(0, 11):
    stab[n] = slots(f"stability__{n}.png", 10, 6, 106, (14, 20))
assets["_stab_lum"] = stab

Path(OUT).write_text("export const ASSETS = " + json.dumps(assets, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
sizes = {k: (len(json.dumps(v)) if not isinstance(v, dict) or "out" in v else sum(len(json.dumps(x)) for x in v.values())) for k, v in assets.items()}
print("written", OUT, Path(OUT).stat().st_size, "bytes")
print({k: v for k, v in sizes.items()})
print("rhythm lum:", {t: assets["_rhythm_lum"][t] for t in (1, 3, 5, 7, 10)})
print("stab lum:", {n: assets["_stab_lum"][n] for n in (0, 1, 5, 10)})


