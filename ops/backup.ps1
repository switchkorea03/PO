param([Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = 'Stop'
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $poRoot '.venv\Scripts\python.exe') (Join-Path $poRoot 'server\manage.py') create_backup --destination $Destination
if ($LASTEXITCODE -ne 0) { throw '백업 실패: 기존 데이터를 삭제하지 않았습니다.' }
