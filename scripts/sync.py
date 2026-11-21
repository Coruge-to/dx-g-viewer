"""PCのタスクスケジューラから定期実行する: 更新 -> 変化があれば commit -> push。

流れ:
  1. update.py を実行 (公式APIから新しい採点IDだけ取得して dataset/ に追記)
  2. dataset/ に変化があれば commit (名義はこのリポジトリの git 設定 = Coruge-to)
  3. 未pushのコミットのうち、「先頭から続く、dataset/ だけを変えたコミット」までを push する。
     手元の開発コミット(site/ や app.py など)は、push しない。開発コミットの上に乗ったデータのコミットも、
     その開発コミットが push されるまで保留する(失われない。push したあとの次の実行で送られる)。
     失敗したら pull --rebase して再試行。次回の実行でも再試行される。

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


def is_data_only(sha: str) -> bool:
    """そのコミットが変えたファイルが、すべて dataset/ の中か(メッセージではなく、中身で判定する)。"""
    r = run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", "--root", sha])
    files = [f for f in r.stdout.split("\0") if f]
    return r.returncode == 0 and bool(files) and all(f.startswith("dataset/") for f in files)


def pushable(branch: str) -> tuple[str | None, int, int]:
    """(push してよい先頭からの最後のコミット, その数, 保留する数)。
    GitHub(origin/branch)より先にあるコミットを、古い順に見て、dataset/ だけのコミットが続くあいだを、push の対象にする。"""
    r = run(["git", "rev-list", "--reverse", f"origin/{branch}..HEAD"])
    shas = r.stdout.split() if r.returncode == 0 else []
    n = 0
    for s in shas:
        if not is_data_only(s):
            break
        n += 1
    return (shas[n - 1] if n else None), n, len(shas) - n


def note_held(held: int) -> None:
    """保留があることを、ログに残す。10分ごとに同じ行が並ばないように、保留の状態が変わったときだけ書く。"""
    mark = LOGDIR / ".sync.held"
    head = run(["git", "rev-parse", "HEAD"]).stdout.strip() if held else ""
    last = mark.read_text() if mark.exists() else ""
    if head != last:
        if held:
            log(f"保留: 手元の開発コミットなど {held} 件は、push しない(確認してから、手で push する)")
        mark.write_text(head)


def push_data_commits(branch: str) -> int:
    tip, n, held = pushable(branch)
    note_held(held)
    if not n:
        return 0
    p = run(["git", "push", "origin", f"{tip}:refs/heads/{branch}"])
    if p.returncode != 0:
        pr = run(["git", "pull", "--rebase", "--autostash", "origin", branch])
        if pr.returncode != 0:
            run(["git", "rebase", "--abort"])
        tip, n, held = pushable(branch)      # 取り込み直しで、コミットの識別子が変わるので、もう一度、数える
        if not n:
            log(f"ERROR push: {(p.stderr or p.stdout).strip()[-200:]}")
            return 1
        p = run(["git", "push", "origin", f"{tip}:refs/heads/{branch}"])
    if p.returncode == 0:
        log(f"push: {n} コミットを反映")
        return 0
    log(f"ERROR push: {(p.stderr or p.stdout).strip()[-200:]}")
    return 1


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
            c = run(["git", "commit", "-q", "-m", msg, "--", "dataset"])   # dataset だけをcommitする(ステージ済みの他のファイルを、巻き込まない)
            if c.returncode != 0:
                log(f"ERROR commit: {(c.stderr or c.stdout).strip()[:200]}")
                return 1
            log(f"commit: {msg}")

        if no_push:
            return 0
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip() or "main"
        return push_data_commits(branch)
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
