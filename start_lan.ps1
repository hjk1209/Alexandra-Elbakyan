param(
    [int]$Port = 8000,
    [switch]$ShowOnly
)

$ErrorActionPreference = "Stop"

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
Write-Host "Raiz Coletiva na rede local" -ForegroundColor Green
Write-Host "Hostname: $hostName"
Write-Host "IP principal: $primaryIp"
Write-Host "URL local: http://127.0.0.1:$Port/"
Write-Host "URL na rede: http://$primaryIp`:$Port/"
Write-Host ""

if ($ShowOnly) {
    Write-Host "Modo ShowOnly ativo. Servidor nao iniciado."
    return
}

& py -3.14 manage.py runserver 0.0.0.0:$Port
