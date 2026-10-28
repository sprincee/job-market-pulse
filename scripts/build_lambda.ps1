# Builds build\lambda\ (our code + Linux deps) for Terraform to zip.
# Deps are downloaded as Linux wheels because we build on Windows but the
# Lambda runs on Amazon Linux (decision F). Run before `terraform plan`.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root "build\lambda"

if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory $out | Out-Null

& "$root\.venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check `
    -r "$root\requirements.txt" --target $out `
    --platform manylinux2014_x86_64 --implementation cp --python-version 3.13 --only-binary=:all:
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Copy-Item "$root\ingest" $out -Recurse
Copy-Item "$root\config" $out -Recurse
Get-ChildItem $out -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

$mb = (Get-ChildItem $out -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("built {0} ({1:N1} MB unzipped)" -f $out, $mb)
