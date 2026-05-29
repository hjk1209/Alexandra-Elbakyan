param(
    [int]$Port = 8000,
    [switch]$ShowOnly
)

$ErrorActionPreference = "Stop"

function Get-ProjectPython {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & $pyLauncher.Source -3.14 --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return @($pyLauncher.Source, "-3.14")
        }
    }

    $candidatePaths = @()
    if ($env:LOCALAPPDATA) {
        $candidatePaths += Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"
        $candidatePaths += Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"
        $candidatePaths += Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    }
    if ($env:ProgramFiles) {
        $candidatePaths += Join-Path $env:ProgramFiles "Python314\python.exe"
        $candidatePaths += Join-Path $env:ProgramFiles "Python313\python.exe"
        $candidatePaths += Join-Path $env:ProgramFiles "Python312\python.exe"
    }

    foreach ($candidate in $candidatePaths) {
        if (Test-Path $candidate) {
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return @($candidate)
            }
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source -notlike "*WindowsApps*") {
        & $pythonCommand.Source --version *> $null
        if ($LASTEXITCODE -eq 0) {
            return @($pythonCommand.Source)
        }
    }

    throw "Python 3.14 nao encontrado. Instale o Python 3.14 ou o Python Launcher (py) e tente novamente."
}

function Invoke-ProjectPython {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$PythonArgs
    )

    $commandParts = @(Get-ProjectPython)
    $pythonExe = $commandParts[0]
    $resolvedArgs = @()
    if ($commandParts.Count -gt 1) {
        $resolvedArgs += $commandParts[1..($commandParts.Count - 1)]
    }
    $resolvedArgs += $PythonArgs
    & $pythonExe @resolvedArgs
}

$hostName = $env:COMPUTERNAME
$ipv4List = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
    Where-Object {
        $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
        -not $_.IPAddressToString.StartsWith("127.")
    } |
    Select-Object -ExpandProperty IPAddressToString -Unique

if (-not $ipv4List) {
    throw "Nao foi possivel detectar um IPv4 local para compartilhar na rede."
}

$primaryIp = $ipv4List | Select-Object -First 1
$allowedHosts = @("127.0.0.1", "localhost", "testserver", $hostName) + $ipv4List
$allowedHostsValue = ($allowedHosts | Select-Object -Unique) -join ","

$trustedOrigins = @(
    "http://127.0.0.1:$Port",
    "http://localhost:$Port",
    "http://$hostName`:$Port"
) + ($ipv4List | ForEach-Object { "http://$_`:$Port" })
$trustedOriginsValue = ($trustedOrigins | Select-Object -Unique) -join ","

$env:RAIZ_DEBUG = "True"
$env:DJANGO_SETTINGS_MODULE = "juventude_mst.settings.local"
$env:RAIZ_SECURE_SSL_REDIRECT = "False"
$env:RAIZ_ENABLE_REALTIME = "False"
$env:RAIZ_CACHE_BACKEND = "django.core.cache.backends.locmem.LocMemCache"
$env:RAIZ_CACHE_LOCATION = ""
$env:RAIZ_ALLOWED_HOSTS = $allowedHostsValue
$env:RAIZ_CSRF_TRUSTED_ORIGINS = $trustedOriginsValue

Write-Host ""
Write-Host "Rede Raizes Socialista na rede local" -ForegroundColor Green
Write-Host "Hostname: $hostName"
Write-Host "IP principal: $primaryIp"
Write-Host "URL local: http://127.0.0.1:$Port/"
Write-Host "URL na rede: http://$primaryIp`:$Port/"
Write-Host ""

if ($ShowOnly) {
    Write-Host "Modo ShowOnly ativo. Servidor nao iniciado."
    return
}

Invoke-ProjectPython manage.py runserver 0.0.0.0:$Port
