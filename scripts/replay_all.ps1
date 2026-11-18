# scripts/replay_all.ps1 - replay 24 thang (1997-01 .. 1998-12): cham diem tung thang, ghi 1 dong JSON/thang
# Dung (tu thu muc goc repo): .\scripts\replay_all.ps1 [-Out reports\replay_log_rerun.jsonl] [-Dry]
# Mac dinh ghi ra file MOI, khong de len reports\replay_log.jsonl. Thang 1997-01 se dung o kiem tra chat luong du lieu (dq_ok = false) - day la ket qua dung.
param([string]$Out = "reports\replay_log_rerun.jsonl", [switch]$Dry)
$outPath = Join-Path (Get-Location).Path $Out
if (Test-Path $outPath) { Remove-Item $outPath }
$utf8 = New-Object System.Text.UTF8Encoding($false)
foreach ($y in 1997, 1998) {
    foreach ($m in 1..12) {
        $mo = "{0}-{1:00}" -f $y, $m
        $a = @("src\score_month.py", "--month", $mo)
        if ($Dry) { $a += "--dry" }
        $line = (& python @a | Select-Object -Last 1)
        [IO.File]::AppendAllText($outPath, $line + "`n", $utf8)
        Write-Host $line
    }
}
