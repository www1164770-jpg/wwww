param([ValidateSet('start','stop','status')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$runtimeDir = Join-Path $projectRoot '.runtime/daily'
$statePath = Join-Path $runtimeDir 'processes.json'
$composeArgs = @('compose','-f','compose.yaml','-f','compose.daily.yaml')
$records = @()
if (Test-Path -LiteralPath $statePath) { $records = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json }
function Get-OwnedProcess($record) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.id)" -ErrorAction SilentlyContinue
    if ($null -eq $process) { return $null }
    if ($process.CommandLine -notlike "*$($record.marker)*" -or $process.CreationDate.ToUniversalTime().ToString('o') -ne $record.created) {
        throw "PID $($record.id) no longer belongs to this daily service; refusing to operate"
    }
    return $process
}
function Show-Status {
    & docker @composeArgs ps
    foreach ($record in $records) {
        $process = Get-OwnedProcess $record
        Write-Output ("{0}: {1} (PID {2})" -f $record.name, $(if ($process) {'running'} else {'stopped'}), $record.id)
    }
    foreach ($url in @('http://127.0.0.1:5000/api/health/db','http://127.0.0.1:5173')) {
        try { $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 4; Write-Output "$url HTTP $($response.StatusCode)" }
        catch { Write-Output "$url unavailable" }
    }
}
if ($Action -eq 'status') { Show-Status; exit 0 }
if ($Action -eq 'stop') {
    foreach ($record in $records) { if (Get-OwnedProcess $record) { Stop-Process -Id $record.id; Write-Output "Stopped $($record.name)" } }
    & docker @composeArgs stop redis meilisearch
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop daily infrastructure' }
    Write-Output 'Daily services stopped. Native MySQL and every data volume retained.'
    exit 0
}
& python backend/scripts/check_daily_ready.py
if ($LASTEXITCODE -ne 0) { throw 'Daily readiness failed; startup performs no migration' }
& docker @composeArgs up -d redis meilisearch
if ($LASTEXITCODE -ne 0) { throw 'Daily infrastructure startup failed' }
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$pythonPath = (Get-Command python).Source
$nodePath = (Get-Command node).Source
$definitions = @(
    @{name='backend'; file=$pythonPath; args=@('-u','backend/scripts/run_daily_service.py','backend'); marker='backend/scripts/run_daily_service.py backend'; cwd=$projectRoot; port=5000},
    @{name='worker'; file=$pythonPath; args=@('-u','backend/scripts/run_daily_service.py','worker'); marker='backend/scripts/run_daily_service.py worker'; cwd=$projectRoot; port=0},
    @{name='frontend'; file=$nodePath; args=@('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort'); marker='node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173'; cwd=(Join-Path $projectRoot 'backend/frontend'); port=5173}
)
$env:API_PROXY_TARGET='http://127.0.0.1:5000'
$started = @()
try {
    foreach ($definition in $definitions) {
        $previous = $records | Where-Object name -eq $definition.name | Select-Object -First 1
        if ($previous -and (Get-OwnedProcess $previous)) { continue }
        if ($definition.port -ne 0) {
            $client = New-Object System.Net.Sockets.TcpClient
            try { $client.Connect('127.0.0.1',$definition.port); throw "Port $($definition.port) is already owned by an untracked process" }
            catch [System.Net.Sockets.SocketException] { }
            finally { $client.Dispose() }
        }
        $process = Start-Process -FilePath $definition.file -ArgumentList $definition.args -WorkingDirectory $definition.cwd -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir ($definition.name+'.out.log')) -RedirectStandardError (Join-Path $runtimeDir ($definition.name+'.err.log'))
        $identity = Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)"
        $record = [pscustomobject]@{name=$definition.name;id=$process.Id;marker=$definition.marker;created=$identity.CreationDate.ToUniversalTime().ToString('o')}
        $records = @($records | Where-Object name -ne $definition.name) + @($record)
        $started += $record
        ConvertTo-Json -InputObject @($records) | Set-Content -Encoding UTF8 -LiteralPath $statePath
    }
    $deadline = (Get-Date).AddSeconds(45)
    do {
        $healthy = $true
        foreach ($url in @('http://127.0.0.1:5000/api/health/db','http://127.0.0.1:5173')) {
            try { $null = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2 } catch { $healthy=$false }
        }
        if ($healthy) { break }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    if (-not $healthy) { throw 'Daily health check failed; see .runtime/daily logs' }
    foreach ($record in $records) { if (-not (Get-OwnedProcess $record)) { throw "$($record.name) exited" } }
    Show-Status
    Write-Output 'Ready: http://127.0.0.1:5173'
} catch {
    foreach ($record in $started) { if (Get-OwnedProcess $record) { Stop-Process -Id $record.id -ErrorAction SilentlyContinue } }
    throw
}
