# 自動更新(sync.py)のタスクスケジューラ登録を管理する。何度実行しても同じ結果になる(再登録で上書き)。
#
#   .\scripts\task.ps1                 # 10分おきで登録 (既定)
#   .\scripts\task.ps1 -Minutes 5      # 5分おきに変更 (再登録で上書き)
#   .\scripts\task.ps1 -Status         # 登録状況・次回実行・直近のログを表示
#   .\scripts\task.ps1 -Remove         # 登録を削除
#
# 間隔を変えたいときは -Minutes を変えて再実行するだけ。リポジトリの場所はこのスクリプトから自動で決まる。
# 注意: 公式APIへの負荷を考え、1分未満の間隔は受け付けない (推奨は5分以上)。
param(
    [int]$Minutes = 10,
    [switch]$Status,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$TaskName = "dxg-sync"
$Root = Split-Path -Parent $PSScriptRoot
$Sync = Join-Path $Root "scripts\sync.py"

if ($Status) {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $t) { Write-Host "未登録: $TaskName"; exit 0 }
    $i = Get-ScheduledTaskInfo -TaskName $TaskName
    $rep = $t.Triggers[0].Repetition.Interval
    Write-Host "状態: $($t.State) / 間隔: $rep / 前回: $($i.LastRunTime) (結果 $($i.LastTaskResult)) / 次回: $($i.NextRunTime)"
    $log = Join-Path $Root "logs\sync.log"
    if (Test-Path $log) { Write-Host "--- logs/sync.log (末尾) ---"; Get-Content $log -Tail 10 -Encoding UTF8 }
    exit 0
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "削除しました: $TaskName"
    exit 0
}

if ($Minutes -lt 1) { throw "-Minutes は1以上を指定してください" }

# ウィンドウを出さない pythonw があればそれを使う
$py = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python).Source }

$action = New-ScheduledTaskAction -Execute $py -Argument "`"$Sync`"" -WorkingDirectory $Root
# 開始は1分後。以降 $Minutes 分おきに無期限で繰り返す
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $Minutes)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "DX-G採点記録を公式APIから取得して dataset/ を更新し push する (scripts/sync.py)" -Force | Out-Null
Write-Host "登録しました: $TaskName / $Minutes 分おき / $py $Sync"
Write-Host "変更: .\scripts\task.ps1 -Minutes <分> / 確認: -Status / 削除: -Remove"
