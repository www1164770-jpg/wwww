[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$serviceName = 'MySQL97'
$mysqlHost = '127.0.0.1'
$mysqlPort = 3306
$deadline = [DateTime]::UtcNow.AddSeconds(30)
$projectRoot = $PSScriptRoot

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

try {
    Write-Host "[数据库] 检查 $serviceName..."
    $service = Get-Service -Name $serviceName -ErrorAction Stop
    if ($service.Status -ne 'Running') {
        Write-Host "[数据库] $serviceName 未运行，正在启动..."
        if (-not (Test-IsAdministrator)) {
            Write-Host "[数据库启动失败] $serviceName 当前未运行，并且当前 PowerShell 没有管理员权限。请以管理员身份运行此脚本，或将 $serviceName 设置为自动启动。" -ForegroundColor Red
            exit 1
        }
        Start-Service -Name $serviceName -ErrorAction Stop
        $remaining = [Math]::Max(1, [int]($deadline - [DateTime]::UtcNow).TotalSeconds)
        $service.WaitForStatus('Running', [TimeSpan]::FromSeconds($remaining))
        Write-Host "[数据库] $serviceName 已启动"
    }
    else {
        Write-Host "[数据库] $serviceName 已运行"
    }
}
catch {
    Write-Error "[数据库启动失败] 无法准备 $serviceName。请确认服务已安装并以管理员身份重试。"
    exit 1
}

Write-Host "[数据库] 等待 ${mysqlHost}:${mysqlPort}..."
$portReady = $false
while ([DateTime]::UtcNow -lt $deadline) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync($mysqlHost, $mysqlPort)
        if ($task.Wait(500) -and $client.Connected) {
            $portReady = $true
            break
        }
    }
    catch {
        # MySQL may still be initializing.
    }
    finally {
        $client.Dispose()
    }
    Start-Sleep -Milliseconds 500
}

if (-not $portReady) {
    Write-Error "[数据库启动失败] 等待 ${mysqlHost}:${mysqlPort} 超时，Flask 未启动。"
    exit 1
}
Write-Host '[数据库] MySQL 端口已就绪'

$pythonCandidates = @(
    (Join-Path $projectRoot '.venv\Scripts\python.exe'),
    (Join-Path $projectRoot 'venv\Scripts\python.exe')
)
$python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $python) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        Write-Error '[后端启动失败] 未找到项目虚拟环境或可用的 python 命令。'
        exit 1
    }
    $python = $pythonCommand.Source
}

Write-Host '[后端] 交由 Flask 启动检查执行 SELECT 1...'
& $python (Join-Path $projectRoot 'backend\app.py')
exit $LASTEXITCODE
