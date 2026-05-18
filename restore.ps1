param(
    [Parameter(Mandatory=$true)]
    [string]$BackupDir
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
    throw "Backup nao encontrado: $BackupDir"
}

$resolvedBackup = (Resolve-Path $BackupDir).Path
$workspace = (Resolve-Path ".").Path

Write-Host "Backup selecionado: $resolvedBackup" -ForegroundColor Yellow
Write-Host "Projeto atual: $workspace" -ForegroundColor Yellow
Write-Host ""
Write-Host "Esta operacao pode substituir db.sqlite3 e a pasta media." -ForegroundColor Red
$confirmation = Read-Host "Digite RESTAURAR para continuar"

if ($confirmation -ne "RESTAURAR") {
    Write-Host "Restauracao cancelada."
    return
}

$dbBackup = Join-Path $resolvedBackup "db.sqlite3"
if (Test-Path $dbBackup) {
    Copy-Item -Path $dbBackup -Destination (Join-Path $workspace "db.sqlite3") -Force
    Write-Host "Banco restaurado." -ForegroundColor Green
}

$mediaBackup = Join-Path $resolvedBackup "media.zip"
if (Test-Path $mediaBackup) {
    $mediaDir = Join-Path $workspace "media"
    if (Test-Path $mediaDir) {
        Rename-Item -Path $mediaDir -NewName ("media.before-restore-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    }
    New-Item -ItemType Directory -Force -Path $mediaDir | Out-Null
    Expand-Archive -Path $mediaBackup -DestinationPath $mediaDir -Force
    Write-Host "Midias restauradas." -ForegroundColor Green
}

Write-Host "Restauracao concluida." -ForegroundColor Green
