$ErrorActionPreference = 'Stop'
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$poPython = Join-Path $poRoot '.venv\Scripts\python.exe'
& $poPython (Join-Path $PSScriptRoot 'runtime.py') --bootstrap-user
if ($LASTEXITCODE -ne 0) { throw '실행 환경 준비 실패' }
& (Join-Path $PSScriptRoot 'start-workers.ps1')
$poWeb = Start-Process -FilePath $poPython -ArgumentList @('-m','waitress','--listen=127.0.0.1:8000','config.wsgi:application') -WorkingDirectory (Join-Path $poRoot 'server') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $poRoot '.runtime\web.log') -RedirectStandardError (Join-Path $poRoot '.runtime\web-error.log')
Write-Output "PO 웹 실행: http://127.0.0.1:8000/ (PID $($poWeb.Id))"
