$ErrorActionPreference = 'Stop'
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$poPython = Join-Path $poRoot '.venv/Scripts/python.exe'
$poPreview = Start-Process -FilePath $poPython -ArgumentList @('-m','http.server','4174','--bind','127.0.0.1','--directory','dist') -WorkingDirectory (Join-Path $poRoot 'ui-prototype') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $poRoot '.runtime/ui-preview.log') -RedirectStandardError (Join-Path $poRoot '.runtime/ui-preview-error.log')
Write-Output "UI mockup: http://127.0.0.1:4174/ (PID $($poPreview.Id))"
