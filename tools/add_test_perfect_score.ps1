# 試験用: 満点(100.000)の見本の記録を、1件、試験用のコピー(static/pagestest/dataset/history.jsonl)にだけ、足す。
# 本物の dataset/history.jsonl は、変えない。 手元のデータに、100.000の記録が無いので、表(7桁の点数)と採点結果画面の、見え方を確かめるための道具。
# 使い方: .\tools\copy_static_for_test.ps1 を実行したあとに、これを実行する(copy は、試験用のコピーを、本物のデータで、上書きする)。
# 見本は、一番新しい記録の写し。 点数・素点・ボーナス点・日時・曲名・歌手名だけを、変える(曲名に「確認用」と入れて、本物と区別する)。
Set-Location (Split-Path $PSScriptRoot -Parent)
$src = "dataset\history.jsonl"
$dst = "static\pagestest\dataset\history.jsonl"
if (-not (Test-Path $dst)) { "試験用のコピーがありません。先に tools\copy_static_for_test.ps1 を実行してください。"; return }
$lines = [System.IO.File]::ReadAllLines((Resolve-Path $src), [System.Text.Encoding]::UTF8)
$latest = $null; $latestKey = ""
foreach ($l in $lines) { if (-not $l.Trim()) { continue }; $o = $l | ConvertFrom-Json; if ($o.scoringDateTime -gt $latestKey) { $latestKey = $o.scoringDateTime; $latest = $l } }
$o = $latest | ConvertFrom-Json
$o.totalPoint = "100.000"; $o.rawPoint = "98.500"; $o.bonusPoint = "1.500"
$o.scoringDateTime = "2099/01/01 00:00:00"; $o.scoringDxgId = "TEST-100000"
$o.contentsName = "【確認用】100.000の見本"; $o.artistName = "(本物ではありません)"
$json = $o | ConvertTo-Json -Compress -Depth 6
$enc = New-Object System.Text.UTF8Encoding($false)
$cur = [System.IO.File]::ReadAllText((Resolve-Path $dst), $enc)
if ($cur -match "TEST-100000") { "すでに追加済みです"; return }
if (-not $cur.EndsWith("`n")) { $cur += "`n" }
[System.IO.File]::WriteAllText((Resolve-Path $dst), $cur + $json + "`n", $enc)
"追加しました(試験用のコピーの行数: " + [System.IO.File]::ReadAllLines((Resolve-Path $dst)).Length + "。 本物の行数: " + $lines.Length + ")"
