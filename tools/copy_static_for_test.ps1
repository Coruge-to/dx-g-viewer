# 試験用: site/ と dataset/ を、Streamlit の静的配信フォルダ(static/pagestest。Git管理外)へ、コピーする。
# そのあと、tools/compare_static.html を開くと、Streamlit 版と静的版を、同じ幅で並べて、全要素の位置・大きさ・CSSを突き合わせられる。
Set-Location (Split-Path $PSScriptRoot -Parent)
$dst = "static\pagestest"
New-Item -ItemType Directory -Force $dst, "$dst\dataset", "$dst\fonts" | Out-Null
Get-ChildItem site -File | Where-Object { $_.Name -ne "demo.html" } | Copy-Item -Destination $dst -Force
Copy-Item site\fonts\* "$dst\fonts" -Force
Copy-Item dataset\history.jsonl, dataset\meta.json, dataset\comment_master.json "$dst\dataset" -Force
Copy-Item tools\compare_static.html "$dst\cmp.html" -Force
"copied to $dst"
