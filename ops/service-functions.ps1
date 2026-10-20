function Test-PoPort {
    param([int]$Port)
    $poClient = New-Object System.Net.Sockets.TcpClient
    try {
        $poPending = $poClient.ConnectAsync('127.0.0.1', $Port)
        return ($poPending.Wait(1000) -and $poClient.Connected)
    } catch { return $false } finally { $poClient.Dispose() }
}

function Test-PoHttp {
    param([string]$Url)
    try {
        $poResponse = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 4
        return ($poResponse.StatusCode -eq 200 -and $poResponse.Content -match 'PO Desk')
    } catch { return $false }
}

function Wait-PoHttp {
    param([string]$Url)
    for ($poAttempt = 0; $poAttempt -lt 20; $poAttempt++) {
        if (Test-PoHttp $Url) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "Server did not become ready: $Url. Check .runtime logs."
}

function Get-PoWorker {
    param([string]$Root, [string]$Command)
    $poRootPattern = [regex]::Escape($Root)
    return @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop | Where-Object {
        $_.CommandLine -match $poRootPattern -and $_.CommandLine -match $Command
    })
}
