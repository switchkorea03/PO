param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$poScript = Join-Path $PSScriptRoot 'start-on-login.ps1'
$poStartup = [Environment]::GetFolderPath('Startup')
$poLinkPath = Join-Path $poStartup 'PODesk-LocalServers.lnk'
$poShell = New-Object -ComObject WScript.Shell
try {
    if (Test-Path -LiteralPath $poLinkPath) {
        $poPrevious = $poShell.CreateShortcut($poLinkPath)
        if ($poPrevious.Arguments -notlike "*$poScript*") { throw 'An unrelated startup shortcut already uses this name.' }
    }
    if ($Remove) {
        if (Test-Path -LiteralPath $poLinkPath) { Remove-Item -LiteralPath $poLinkPath }
        Write-Output 'PO Desk automatic startup removed. Stored data is unchanged.'
        return
    }
    $poLink = $poShell.CreateShortcut($poLinkPath)
    $poLink.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $poLink.Arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy RemoteSigned -File "' + $poScript + '"'
    $poLink.WorkingDirectory = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
    $poLink.WindowStyle = 7
    $poLink.Description = 'Start PO Desk local web, database, intake worker and UI preview at Windows sign-in.'
    $poLink.Save()
    Write-Output "Automatic startup installed for current user: $poLinkPath"
} finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($poShell) }
