"""公式DAM★ともAPIから新しい採点を取得し、dataset/history.jsonl に追記する。

- 認証: 環境変数 DAM_CARD (cdmCardNo) のみ。cdmToken は不要 (検証されない)
- まず一覧の1ページ目(5件)だけを見て、保管庫に無いIDがあれば続きのページ・詳細へ進む
- 新しいIDが無ければ1リクエストで終了
- 詳細は1件ごとに待機(6〜10秒)を入れてサーバー負荷を抑える

使い方:
  python scripts/update.py              # 通常
  python scripts/update.py --dry-run    # 一覧確認のみ (書き込み・詳細取得なし)
  python scripts/update.py --heartbeat  # checked_at を更新 (定期実行の休止防止用)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import dxg_lib
from dxg_lib import DATASET_DIR, NS

API = "https://www.clubdam.com/app/damtomo/scoring/GetScoringDxgListXML.do"
UA = "Mozilla/5.0 (personal archive of own scoring data)"
MAX_PAGES = 40
MAX_NEW = 200  # 一覧が最大200件なので、それ以上は一度に取らない


def read_env_file() -> dict[str, str]:
    """リポジトリ直下の .env (Git管理外) から KEY=VALUE を読む。"""
    p = dxg_lib.ROOT / ".env"
    out: dict[str, str] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def call(card: str, **params) -> bytes:
    q = {"cdmCardNo": card, "enc": "sjis", **params}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"request failed: {last}")


def list_page(card: str, page: int) -> tuple[list[tuple[str, str]], bool]:
    body = call(card, pageNo=page, detailFlg=0, dxgType=1, UTCserial=int(time.time() * 1000))
    root = ET.fromstring(body)
    code = root.findtext(f"{NS}result/{NS}statusCode")
    if code != "0000":
        raise RuntimeError(f"list statusCode={code}")
    items = [(e.get("scoringDxgId"), e.get("scoringDateTime")) for e in root.iter(f"{NS}scoring")]
    has_next = root.find(f"{NS}data/{NS}page").get("hasNext") == "1"
    return items, has_next


def load_dataset() -> list[dict]:
    p = DATASET_DIR / "history.jsonl"
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig") as f:  # BOM付きでも読めるように
        return [json.loads(l) for l in f if l.strip()]


def save_dataset(records: list[dict], heartbeat: bool) -> None:
    records.sort(key=lambda r: r["scoringDateTime"], reverse=True)
    with open(DATASET_DIR / "history.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    mp = DATASET_DIR / "meta.json"
    meta = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    meta.update(count=len(records), newest=records[0]["scoringDateTime"], oldest=records[-1]["scoringDateTime"])
    if heartbeat:
        meta["checked_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def set_output(changed: bool) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--heartbeat", action="store_true")
    args = ap.parse_args()

    card = os.environ.get("DAM_CARD", "").strip() or read_env_file().get("DAM_CARD", "").strip()
    if not card:
        print("DAM_CARD is not set", file=sys.stderr)
        return 2

    records = load_dataset()
    known = {r["scoringDxgId"] for r in records}

    new_ids: list[str] = []
    for page in range(1, MAX_PAGES + 1):
        items, has_next = list_page(card, page)
        hit_known = False
        for sid, _dt in items:
            if sid in known:
                hit_known = True
            elif sid not in new_ids:
                new_ids.append(sid)
        if page == 1:
            print(f"list page1: {len(items)} items, newest={items[0][1] if items else '-'}")
        if hit_known or not has_next or len(new_ids) >= MAX_NEW:
            break
        time.sleep(2)

    print(f"known={len(known)} new={len(new_ids)}")
    if args.dry_run:
        print("dry-run: no detail fetch, no write")
        set_output(False)
        return 0
    if not new_ids:
        if args.heartbeat and records:
            save_dataset(records, heartbeat=True)
            set_output(True)
        else:
            set_output(False)
        return 0

    comments = dxg_lib.load_comments()
    added = 0
    for sid in new_ids:
        try:
            body = call(card, scoringDxgId=sid, detailFlg=1)
            rec = dxg_lib.to_public(dxg_lib.from_official(body, comments))
        except Exception as e:  # noqa: BLE001
            print(f"skip {sid}: {e}", file=sys.stderr)
            continue
        records.append(rec)
        added += 1
        print(f"added {rec['scoringDateTime']} {sid} {rec['contentsName']} {rec['totalPoint']}")
        time.sleep(random.uniform(6, 10))

    if added:
        save_dataset(records, heartbeat=args.heartbeat)
    set_output(added > 0)
    print(f"done: added {added} / {len(new_ids)}")
    return 0 if added == len(new_ids) else 1


if __name__ == "__main__":
    sys.exit(main())
