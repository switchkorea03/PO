$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'service-functions.ps1')
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$poPython = Join-Path $poRoot '.venv\Scripts\python.exe'
$poServer = Join-Path $poRoot 'server'
& $poPython (Join-Path $PSScriptRoot 'runtime.py')
if ($LASTEXITCODE -ne 0) { throw '로컬 실행 환경 실패' }
if ((Get-PoWorker $poRoot 'run_intake_worker').Count -eq 0) {
    $poIntake = Start-Process -FilePath $poPython -ArgumentList @('manage.py','run_intake_worker') -WorkingDirectory $poServer -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $poRoot '.runtime\intake-worker.log') -RedirectStandardError (Join-Path $poRoot '.runtime\intake-worker-error.log')
    Write-Output "Intake worker started: PID $($poIntake.Id)"
} else { Write-Output 'Intake worker is already running.' }
$poSmsReady = & $poPython -c "import sys;sys.path.insert(0,r'$poServer');from dotenv import dotenv_values;v=dotenv_values(r'$poServer\.env');print('yes' if v.get('SMS_PROVIDER') in ('solapi','fake') else 'no')"
if ($poSmsReady -eq 'yes' -and (Get-PoWorker $poRoot 'run_notice_worker').Count -eq 0) {
    $poNotice = Start-Process -FilePath $poPython -ArgumentList @('manage.py','run_notice_worker') -WorkingDirectory $poServer -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $poRoot '.runtime\notice-worker.log') -RedirectStandardError (Join-Path $poRoot '.runtime\notice-worker-error.log')
    Write-Output "문자 worker 시작: PID $($poNotice.Id)"
} elseif ($poSmsReady -eq 'yes') { Write-Output 'Notice worker is already running.' }
else { Write-Output 'SMS is not configured. Only file extraction is running.' }
