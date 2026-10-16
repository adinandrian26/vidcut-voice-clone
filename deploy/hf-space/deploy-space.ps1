# Deploy Space VidCut dalam satu perintah (Windows PowerShell).
# Syarat: akun HF email terverifikasi + umur > 30 hari (untuk hardware ZeroGPU gratis).
# Cara pakai dari folder repo:
#   .\deploy\hf-space\deploy-space.ps1 -SpaceId "username/nama-space"
param(
    [Parameter(Mandatory = $true)]
    [string]$SpaceId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "1/3 Login Hugging Face (tempel token dari https://huggingface.co/settings/tokens)..."
huggingface-cli login

Write-Host "2/3 Upload app.py + requirements.txt + README.md ke Space $SpaceId ..."
huggingface-cli upload $SpaceId deploy/hf-space . --repo-type space

Write-Host ""
Write-Host "3/3 Terakhir MANUAL di browser (tidak bisa via perintah):"
Write-Host "  - Buka https://huggingface.co/spaces/$SpaceId/settings"
Write-Host "  - Space hardware -> pilih ZeroGPU -> Save"
Write-Host "  - Tunggu build selesai, buka URL Space = website publiknya."
