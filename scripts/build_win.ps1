Param(
  [string]$AppName = "MedicalDocAI",
  [string]$Entry = "main.py",
  [string]$SpecFile = "main.spec"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
  py -3 -m venv .venv
}
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip wheel setuptools
if (Test-Path "requirements.txt") {
  pip install -r requirements.txt
}
pip install pyinstaller

if (Test-Path "build") { Remove-Item -Recurse -Force build }
if (Test-Path "dist\$AppName") { Remove-Item -Recurse -Force "dist\$AppName" }

if (Test-Path $SpecFile) {
  pyinstaller $SpecFile
} else {
  pyinstaller --noconfirm `
    --name $AppName `
    --noconsole `
    --add-data "resources;resources" `
    --add-data "json;json" `
    --hidden-import reportlab `
    $Entry
}

Write-Host "Built at dist\$AppName"
Write-Host "To package with Inno Setup, ensure packaging\windows\innosetup.iss is configured, then run ISCC.exe on it."
