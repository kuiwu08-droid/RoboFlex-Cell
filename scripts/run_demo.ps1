param([int]$Port = 8080)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$projectPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw '请先按 README 安装 Python 并创建 .venv，再运行此脚本。'
}
& $projectPython -m roboflex.cli serve --port $Port
