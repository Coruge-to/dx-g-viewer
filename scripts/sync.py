"""PCのタスクスケジューラから定期実行する: 更新 -> 変化があれば commit -> push。

流れ:
  1. update.py を実行 (公式APIから新しい採点IDだけ取得して dataset/ に追記)
  2. dataset/ に変化があれば commit (名義はこのリポジトリの git 設定 = Coruge-to)
  3. 未pushのコミットがあれば push (失敗したら pull --rebase して再試行。次回の実行でも再試行される)

ログ: logs/sync.log (Git管理外)。二重起動はロックで防ぐ。
使い方: python scripts/sync.py [--no-push]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGDIR = ROOT / "logs"
LOG = LOGDIR / "sync.log"
LOCK = LOGDIR / ".sync.lock"
LOCK_STALE_SEC = 60 * 60


def log(msg: str) -> None:
    LOGDIR.mkdir(exist_ok=True)
    if LOG.exists() and LOG.stat().st_size > 512 * 1024:  # 肥大化防止
        LOG.replace(LOGDIR / "sync.old.log")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1", GIT_TERMINAL_PROMPT="0")
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)


def main() -> int:
    no_push = "--no-push" in sys.argv
    LOGDIR.mkdir(exist_ok=True)
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < LOCK_STALE_SEC:
        return 0  # 別のプロセスが実行中
    LOCK.write_text(str(os.getpid()))
    try:
        r = run([sys.executable, str(ROOT / "scripts" / "update.py")])
        out = (r.stdout or "").strip().splitlines()
        err = (r.stderr or "").strip().splitlines()
        if r.returncode == 2:
            log("ERROR: DAM_CARD が未設定 (.env を確認)")
            return 2
        if r.returncode != 0:
            log(f"update.py exit={r.returncode}: " + " | ".join((err[-1:] or out[-1:])))
        added = 0
        m = re.search(r"done: added (\d+)", "\n".join(out))
        if m:
            added = int(m.group(1))
        if added:
            log(f"update: 新規 {added} 件を追加")

        status = run(["git", "status", "--porcelain", "--", "dataset"])
        if status.stdout.strip():
            run(["git", "add", "dataset"])
            msg = f"data: 新規{added}件を追加" if added else "data: 更新"
            c = run(["git", "commit", "-q", "-m", msg])
            if c.returncode != 0:
                log(f"ERROR commit: {(c.stderr or c.stdout).strip()[:200]}")
                return 1
            log(f"commit: {msg}")

        if no_push:
            return 0
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip() or "main"
        ahead = run(["git", "rev-list", "--count", f"origin/{branch}..HEAD"]).stdout.strip()
        if ahead and int(ahead) > 0:
            p = run(["git", "push", "origin", branch])
            if p.returncode != 0:
                run(["git", "pull", "--rebase", "--autostash", "origin", branch])
                p = run(["git", "push", "origin", branch])
            if p.returncode == 0:
                log(f"push: {ahead} コミットを反映")
            else:
                log(f"ERROR push: {(p.stderr or p.stdout).strip()[-200:]}")
                return 1
        return 0
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
