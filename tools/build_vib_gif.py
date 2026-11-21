"""元サイト(非公式)のビブラート波形GIF(ラベルの文字を含まない完全な波形)から、線の中心線を取り出し、
なめらかな曲線(スプライン)に当てはめて、点列(x,y)にし、site/vib_gif.js に出力する。
元のGIFは小さなドット絵で、線が階段状になっているため、中心線をなめらかな曲線にして、ガタつきを除く。概形(山の位置・高さ・周期)は元のまま。
描画側(detail.js)では、この点列を、一定の太さの線として描く。
使い方: python tools/build_vib_gif.py <GIFのフォルダ> <出力先.js>   (numpy, scipy, scikit-image, pillow が必要)
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.interpolate import UnivariateSpline
from scipy.ndimage import gaussian_filter
from skimage.morphology import skeletonize

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
U = 8                 # 拡大率(中心線を、1px未満の精度で取るため)
SLOPE_W = 0.9        # 縦の伸び(px)1あたり、許容ずれを増やす量。大きいほど、急な斜面を軽く扱う
SIGMA = 0.28          # 当てはめの許容ずれ(元のGIFの1px = 1.0 として)。大きいほどなめらか
STEP = 0.25           # 出力する点の間隔(GIFのpx)
NAMES = ["N", "A-1", "B-1", "C-1", "A-2", "B-2", "C-2", "A-3", "B-3", "C-3", "D", "E", "F", "G", "H"]

out = {}
for n in NAMES:
    p = SRC / f"{n}.gif"
    if not p.exists(): continue                      # A-3 は元サイトに画像が無い(公式画像の波形で代用する)
    im = Image.open(p).convert("RGBA"); a = np.asarray(im).astype(np.float32)
    mask = ((a[..., 3] > 128) & (a[..., 1] > 128)).astype(np.float32)
    big = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize((im.width * U, im.height * U), Image.BICUBIC)).astype(np.float32) / 255.0
    big = gaussian_filter(big, sigma=U * 0.5) > 0.5
    sk = skeletonize(big)                            # 線の中心(骨格)
    ys, xs = np.where(sk)
    cols = {}
    for x, y in zip(xs, ys): cols.setdefault(x, []).append(y)
    X = np.array(sorted(cols)); Y = np.array([np.mean(cols[x]) for x in X])
    RUN = np.array([(max(cols[x]) - min(cols[x]) + 1) for x in X], dtype=float) / U    # その横位置で、線が縦にどれだけ伸びているか(急な斜面ほど大きい)
    X = (X + 0.5) / U; Y = (Y + 0.5) / U             # GIFのpx座標(画素の中心)
    # 急な斜面では、横位置ごとの高さの精度が低いので、軽く扱う(山と谷の頂上=精度が高い所を重く扱う)。これで、斜面のちりめん状の波打ちが消える
    sig = SIGMA + SLOPE_W * RUN
    spl = UnivariateSpline(X, Y, w=1.0 / sig, k=3, s=len(X))
    xs_out = np.arange(X.min(), X.max() + 1e-6, STEP)
    ys_out = np.clip(spl(xs_out), 0.5, im.height - 0.5)
    pts = []
    for x, y in zip(xs_out, ys_out): pts += [round(float(x), 2), round(float(y), 2)]
    out[n] = {"w": im.width, "h": im.height, "p": pts}
OUT.write_text("// 元サイトのビブラート波形GIFの中心線を、なめらかな曲線にした点列 [x0,y0,x1,y1,...]。tools/build_vib_gif.py で作る。\nexport const VIBG = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
print("written", OUT, OUT.stat().st_size, "bytes;", list(out))
