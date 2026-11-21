"""公開用の保管庫 dataset/history.jsonl を、app.py の表が読む列(日本語の列名)の DataFrame にする。

app.py の normalize() は、もともと merged.csv(33列)の列名を読む作りなので、同じ列名に揃える。
新しい歌唱は dxg-sync が history.jsonl に追記するので、表は、CSVを作り直さなくても、自動で最新になる。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

VIB_TYPE = {"N": 0, "A-1": 1, "B-1": 2, "C-1": 3, "A-2": 4, "B-2": 5, "C-2": 6, "A-3": 7,
            "B-3": 8, "C-3": 9, "D": 10, "E": 11, "F": 12, "G": 13, "H": 14}
BONUS_TYPE = {"1": "音程ボーナス", "2": "ビブラートボーナス", "3": "表現力ボーナス"}

COLUMNS = [
    "採点ID", "曲名", "アーティスト", "演奏日時", "総合点", "音程", "安定性", "表現力", "リズム",
    "ビブラート/ロングトーン", "ビブラート回数", "ビブラート上手さ", "ビブラート秒数", "ビブラートタイプ",
    "こぶし", "しゃくり", "フォール", "抑揚", "ボーナスタイプ", "ボーナスポイント",
    "ロングトーンスキル", "リズムタイミング", "キー設定",
    "全国平均総合点", "全国平均音程", "全国平均安定性", "全国平均表現力", "全国平均リズム", "requestNo",
]


def _key(s: str) -> str:
    """'±0' / '＋4' / '－6' -> '0' / '4' / '-6'"""
    s = str(s or "").strip().replace("±", "0").replace("＋", "+").replace("－", "-").replace("−", "-")
    try:
        return str(int(s))
    except ValueError:
        return ""


def load_table_df(path: str | Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            rows.append({
                "採点ID": d["scoringDxgId"],
                "曲名": d.get("contentsName", ""),
                "アーティスト": d.get("artistName", ""),
                "演奏日時": d.get("scoringDateTime", ""),
                "総合点": d.get("totalPoint", ""),
                "音程": d.get("radarChartPitch", ""),
                "安定性": d.get("radarChartStability", ""),
                "表現力": d.get("radarChartExpressive", ""),
                "リズム": d.get("radarChartRhythm", ""),
                "ビブラート/ロングトーン": d.get("radarChartVibratoLongtone", ""),
                "ビブラート回数": d.get("vibratoCount", ""),
                "ビブラート上手さ": d.get("vibratoSkill", ""),
                "ビブラート秒数": d.get("vibratoTotalSecond", ""),
                "ビブラートタイプ": VIB_TYPE.get(d.get("vibratoType", "N"), 0),
                "こぶし": d.get("kobushiCount", ""),
                "しゃくり": d.get("shakuriCount", ""),
                "フォール": d.get("fallCount", ""),
                "抑揚": d.get("intonation", ""),
                "ボーナスタイプ": BONUS_TYPE.get(str(d.get("bonusType", "")), d.get("bonusTypeText", "")),
                "ボーナスポイント": d.get("bonusPoint", ""),
                "ロングトーンスキル": d.get("longtoneSkill", ""),
                "リズムタイミング": d.get("timing", ""),
                "キー設定": _key(d.get("lastPerformKey", "")),
                "全国平均総合点": d.get("nationalAverageTotalPoints", ""),
                "全国平均音程": d.get("nationalAveragePitch", ""),
                "全国平均安定性": d.get("nationalAverageStability", ""),
                "全国平均表現力": d.get("nationalAverageExpression", ""),
                "全国平均リズム": d.get("nationalAverageRhythm", ""),
                "requestNo": d.get("requestNo", ""),
            })
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.sort_values("演奏日時", ascending=False, kind="stable").reset_index(drop=True)
