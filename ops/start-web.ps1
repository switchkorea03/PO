param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$poPython = Join-Path $poRoot '.venv\Scripts\python.exe'
& $poPython (Join-Path $PSScriptRoot 'runtime.py') --bootstrap-user
if ($LASTEXITCODE -ne 0) { throw '로컬 실행 환경을 준비하지 못했습니다.' }
Push-Location (Join-Path $poRoot 'server')
try {
    & $poPython manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'DB migration 실패' }
    & $poPython -m waitress --listen="127.0.0.1:$Port" config.wsgi:application
} finally { Pop-Location }
