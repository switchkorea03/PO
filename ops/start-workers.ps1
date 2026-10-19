$ErrorActionPreference = 'Stop'
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$poPython = Join-Path $poRoot '.venv\Scripts\python.exe'
$poServer = Join-Path $poRoot 'server'
& $poPython (Join-Path $PSScriptRoot 'runtime.py')
if ($LASTEXITCODE -ne 0) { throw '로컬 실행 환경 실패' }
$poIntake = Start-Process -FilePath $poPython -ArgumentList @('manage.py','run_intake_worker') -WorkingDirectory $poServer -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $poRoot '.runtime\intake-worker.log') -RedirectStandardError (Join-Path $poRoot '.runtime\intake-worker-error.log')
Write-Output "파일 인식 worker 시작: PID $($poIntake.Id)"
$poSmsReady = & $poPython -c "import sys;sys.path.insert(0,r'$poServer');from dotenv import dotenv_values;v=dotenv_values(r'$poServer\.env');print('yes' if v.get('SMS_PROVIDER') in ('solapi','fake') else 'no')"
if ($poSmsReady -eq 'yes') {
    $poNotice = Start-Process -FilePath $poPython -ArgumentList @('manage.py','run_notice_worker') -WorkingDirectory $poServer -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $poRoot '.runtime\notice-worker.log') -RedirectStandardError (Join-Path $poRoot '.runtime\notice-worker-error.log')
    Write-Output "문자 worker 시작: PID $($poNotice.Id)"
} else { Write-Output '문자 공급자 미설정: 파일 인식만 실행하며 실제 문자는 보내지 않습니다.' }
