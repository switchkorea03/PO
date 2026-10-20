$ErrorActionPreference = 'Stop'
$poRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$poRuntime = Join-Path $poRoot '.runtime'
New-Item -ItemType Directory -Path $poRuntime -Force | Out-Null
$poMutex = New-Object System.Threading.Mutex($false, 'Local\PODeskLocalServersStartup')
$poLocked = $false
try {
    $poLocked = $poMutex.WaitOne(0)
    if (-not $poLocked) { exit 0 }
    $poLog = Join-Path $poRuntime 'autostart.log'
    Add-Content -LiteralPath $poLog -Encoding UTF8 -Value "$(Get-Date -Format o) Starting local PO services."
    & (Join-Path $PSScriptRoot 'start-local.ps1') 2>&1 | Out-File -LiteralPath $poLog -Encoding UTF8 -Append
    & (Join-Path $PSScriptRoot 'start-ui-preview.ps1') 2>&1 | Out-File -LiteralPath $poLog -Encoding UTF8 -Append
    Add-Content -LiteralPath $poLog -Encoding UTF8 -Value "$(Get-Date -Format o) Both sites are ready."
} catch {
    Add-Content -LiteralPath (Join-Path $poRuntime 'autostart.log') -Encoding UTF8 -Value "$(Get-Date -Format o) ERROR: $($_.Exception.Message)"
    exit 1
} finally {
    if ($poLocked) { $poMutex.ReleaseMutex() }
    $poMutex.Dispose()
}
