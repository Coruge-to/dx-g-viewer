"""精密採点DX-G: 公式APIのXML(detailFlg=1)を、保管庫(dataset/history.jsonl)のレコード形式へ変換する。

保管庫のレコードは、旧非公式サイト(dx-g.clubdam.info)が各行に埋め込んでいたJSONと同じ形。
サイトが公式の数値から作っていた「導出項目」は、ここで同じルールで再計算する。
個人・端末を特定できる項目 (カード番号・端末シリアル等) は PUBLIC_DROP で除外する。
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{https://www.clubdam.com/app/damtomo/scoring/GetScoringDxgListXML}"
ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "dataset"

# 公開しない項目 (カード番号、端末シリアル、決済ID、管理用の空項目)
PUBLIC_DROP = {
    "clubDamCardNo", "damserial", "edyId", "dataKind", "dataSize",
    "scoringEngineVersionNumber", "topRecordNumber", "_row_no", "_page",
}

VIBRATO_TEXT = {
    "A-1": "ボックス型", "B-1": "ボックス型", "C-1": "ボックス型",
    "A-2": "ボックス型", "B-2": "ボックス型", "C-2": "ボックス型",
    "A-3": "ボックス型", "B-3": "ボックス型", "C-3": "ボックス型",
    "D": "上昇形", "E": "下降形", "F": "縮小形", "G": "拡張形", "H": "ひし形", "N": "ノンビブ形",
}
VIBRATO_LABEL = ["N", "A-1", "B-1", "C-1", "A-2", "B-2", "C-2", "A-3", "B-3", "C-3",
                 "D", "E", "F", "G", "H"]  # 公式の数値コード 0..14 -> ラベル
BONUS_TEXT = {"1": "音程", "2": "ビブラート", "3": "表現力"}

_SEMI = ["A♭", "A", "B♭", "B", "C", "D♭", "D", "E♭", "E", "F", "G♭", "G"]
_OCT = {-1: "low", 0: "m1", 1: "m2", 2: "hi", 3: "hihi"}


def note_name(code: str) -> str:
    """公式の声域コード(例 76) -> 表示名(例 hiE)。44(m1A♭)から12半音ごとに区切る。"""
    n = int(code)
    if n >= 83:  # 最上段の表記
        return "hihiB～"
    o, i = divmod(n - 44, 12)
    return _OCT.get(o, "?") + _SEMI[i]


def key_text(code: str) -> str:
    k = int(code)
    if k == 0:
        return "±0"
    return ("＋" if k > 0 else "－") + str(abs(k))


def _trim(x: float) -> str:
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return s or "0"


def load_comments() -> dict[int, str]:
    p = DATASET_DIR / "comment_master.json"
    return {int(k): v for k, v in json.loads(p.read_text(encoding="utf-8")).items()}


def from_official(xml_bytes: bytes, comments: dict[int, str], template_keys: list[str] | None = None) -> dict:
    """公式XML(1件分, detailFlg=1) -> 保管庫レコード。失敗時は ValueError。"""
    root = ET.fromstring(xml_bytes)
    code = root.findtext(f"{NS}result/{NS}statusCode")
    if code != "0000":
        raise ValueError(f"statusCode={code}")
    el = root.find(f".//{NS}scoring")
    if el is None:
        raise ValueError("no <scoring>")
    a = dict(el.attrib)
    total = int(el.text) / 1000
    bonus = int(a["bonusPoint"]) / 1000
    d = a["scoringDateTime"]
    vt = VIBRATO_LABEL[int(a["vibratoType"])]
    radar = [int(a[k]) for k in ("radarChartPitch", "radarChartStability", "radarChartExpressive",
                                 "radarChartVibratoLongtone", "radarChartRhythm")]

    rec: dict = {
        "totalPoint": _trim(total),
        "bonusType": a["bonusType"],
        "bonusPoint": _trim(bonus),
        "rawPoint": f"{total - bonus:.3f}",
        "requestNo": a["requestNo"],
        "contentsName": a["contentsName"],
        "artistName": a["artistName"],
        "scoringDateTime": f"{d[:4]}/{d[4:6]}/{d[6:8]} {d[8:10]}:{d[10:12]}:{d[12:14]}",
        "entryCount": a["entryCount"],
        "analysisReportCommentNo": a["analysisReportCommentNo"],
        "radarChartTotal": str(sum(radar)),
    }
    for k in ("radarChartPitch", "radarChartStability", "radarChartExpressive", "radarChartVibratoLongtone",
              "radarChartRhythm", "intonation", "kobushiCount", "shakuriCount", "fallCount", "vibratoCount",
              "timing", "longtoneSkill", "vibratoSkill"):
        rec[k] = a[k]
    rec["vibratoType"] = vt
    rec["vibratoTotalSecond"] = f"{int(a['vibratoTotalSecond']) / 10:.1f}"
    rec["singingRangeHighest"] = note_name(a["singingRangeHighest"])
    rec["singingRangeLowest"] = note_name(a["singingRangeLowest"])
    rec["vocalRangeHighest"] = a["vocalRangeHighest"]
    rec["vocalRangeLowest"] = a["vocalRangeLowest"]
    rec["nationalAverageTotalPoints"] = f"{int(a['nationalAverageTotalPoints']) / 1000:.3f}"
    for k in ("nationalAveragePitch", "nationalAverageStability", "nationalAverageExpression",
              "nationalAverageVibratoAndLongtone", "nationalAverageRhythm"):
        rec[k] = a[k]
    rec["is_include"] = "1"
    rec["scoringDxgId"] = a["scoringDxgId"]
    rec["dContentsName"] = a["dContentsName"]
    rec["dArtistName"] = a["dArtistName"]
    rec["lastPerformKey"] = key_text(a["lastPerformKey"])
    rec["requestNoChapter"] = str(int(a["requestNoChapter"]))  # 公式は '09'、サイトは '9'
    rec["requestNoTray"] = str(int(a["requestNoTray"]))
    rec["lastTotalPoints"] = _trim(int(a["lastTotalPoints"]) / 1000) if a.get("lastTotalPoints") else ""
    for sec in range(1, 25):
        rec[f"intervalGraphPointsSection{sec:02d}"] = a[f"intervalGraphPointsSection{sec:02d}"]
    for sec in range(1, 25):
        rec[f"intervalGraphIndexSection{sec:02d}"] = a[f"intervalGraphIndexSection{sec:02d}"]
    for sec in range(1, 25):
        rec[f"expressionGraphPointsSection{sec:02d}"] = a[f"expressionGraphPointsSection{sec:02d}"]
    for sec in range(1, 25):
        rec[f"expressionGraphIndexSection{sec:02d}"] = a[f"expressionGraphIndexSection{sec:02d}"]
    rec["comment"] = comments.get(int(a["analysisReportCommentNo"]), "")
    rec["bonusTypeText"] = BONUS_TEXT[a["bonusType"]]
    rec["p_int"] = int(total)
    rec["p_deci"] = round((total - int(total)) * 1000)
    rec["sta_10"] = int(a["radarChartStability"]) // 10 + 1
    rec["int_10"] = int(a["intonation"]) // 10 + 1
    rec["vibratoTypeText"] = VIBRATO_TEXT[vt]
    return rec


def to_public(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k not in PUBLIC_DROP}
