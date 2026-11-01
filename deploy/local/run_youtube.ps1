# Run the partner YouTube collector from this PC and push the result.
# Same job as the server's hourly timer, from a home connection YouTube does not
# block. Both share backend/youtube_candidates.json, so a video one of them read
# is skipped by the other.
#
# Usage (PowerShell, from anywhere):
#   powershell -ExecutionPolicy Bypass -File C:\Users\SEDAT\Desktop\saha-disi\deploy\local\run_youtube.ps1
#   ... -Budget 60    allow more YouTube requests this run (default 30)

param([int]$Budget = 30)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$env:PYTHONIOENCODING = 'utf-8'

git pull -q --rebase --autostash origin main
if ($LASTEXITCODE -ne 0) { throw 'git pull başarısız; önce yerel değişiklikleri kontrol et.' }

# The server's "rest after a block" note is about its own IP, not this connection.
python backend/youtube_partner.py --ignore-rest --budget $Budget
if ($LASTEXITCODE -ne 0) { throw 'Toplayıcı hata verdi.' }

git add backend/youtube_candidates.json
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Host 'Yeni video sözü yok.'; exit 0 }

git -c user.name="saha-disi-youtube" -c user.email="saha-disi-youtube@users.noreply.github.com" commit -q -m "data: partner YouTube statements (local)"
foreach ($attempt in 1..3) {
    git push -q origin main
    if ($LASTEXITCODE -eq 0) { Write-Host 'Gönderildi. Feed en geç bir saat içinde güncellenir.'; exit 0 }
    git pull -q --rebase -X theirs origin main
}
throw 'Push başarısız.'
