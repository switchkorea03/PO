$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'service-functions.ps1')
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$poPython = Join-Path $poRoot '.venv/Scripts/python.exe'
if (Test-PoHttp 'http://127.0.0.1:4174/') {
    Write-Output 'UI mockup is already running: http://127.0.0.1:4174/'
    return
}
if (Test-PoPort 4174) { throw 'Port 4174 is occupied by an unavailable or different server.' }
$poPreview = Start-Process -FilePath $poPython -ArgumentList @('-m','http.server','4174','--bind','127.0.0.1','--directory','dist') -WorkingDirectory (Join-Path $poRoot 'ui-prototype') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $poRoot '.runtime/ui-preview.log') -RedirectStandardError (Join-Path $poRoot '.runtime/ui-preview-error.log')
Wait-PoHttp 'http://127.0.0.1:4174/'
Write-Output "UI mockup: http://127.0.0.1:4174/ (PID $($poPreview.Id))"
