# 切り抜きm4aの作成日時=歌唱時刻に設定（日付順ソートでsetlist順に並ぶ）
# usage: pwsh -File set_dates.ps1 <out_dir> <YYYY-MM-DD>
# ファイル名末尾の _HH-MM.m4a から時刻を取り、CreationTime/LastWriteTime を <日付> HH:MM:00 に設定。
param(
  [Parameter(Mandatory=$true)][string]$OutDir,
  [Parameter(Mandatory=$true)][string]$Date   # 例: 2026-07-17
)
$y,$mo,$d = $Date -split '-'
$n=0; $fail=0
Get-ChildItem $OutDir -File -Filter *.m4a | ForEach-Object {
  if ($_.Name -match '_(\d{2})-(\d{2})\.m4a$') {
    $dt = Get-Date -Year ([int]$y) -Month ([int]$mo) -Day ([int]$d) -Hour ([int]$Matches[1]) -Minute ([int]$Matches[2]) -Second 0
    $_.CreationTime  = $dt
    $_.LastWriteTime = $dt
    $_.LastAccessTime= $dt
    $n++
  } else { Write-Output ("NO_MATCH: " + $_.Name); $fail++ }
}
Write-Output "設定完了 $n 件 / 失敗 $fail 件"
