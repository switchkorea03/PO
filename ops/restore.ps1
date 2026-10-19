param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$TargetDatabase,[Parameter(Mandatory=$true)][string]$TargetMedia)
$ErrorActionPreference = 'Stop'
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $poRoot '.venv\Scripts\python.exe') (Join-Path $poRoot 'server\manage.py') restore_backup --source $Source --target-database $TargetDatabase --target-media $TargetMedia
if ($LASTEXITCODE -ne 0) { throw '복구 실패: 운영 DB는 변경하지 않았습니다.' }
