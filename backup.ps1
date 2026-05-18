param(
    [string]$OutputDir = "backups"
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$targetDir = Join-Path $OutputDir $timestamp

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

if (Test-Path "db.sqlite3") {
    Copy-Item -Path "db.sqlite3" -Destination (Join-Path $targetDir "db.sqlite3") -Force
}

if (Test-Path "media") {
    $mediaFiles = Get-ChildItem -Path "media" -Recurse -File
    if ($mediaFiles) {
        $mediaZip = Join-Path $targetDir "media.zip"
        Compress-Archive -Path "media\*" -DestinationPath $mediaZip -Force
    }
}

if (Test-Path "logs") {
    $logsDir = Join-Path $targetDir "logs"
    New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
    Get-ChildItem -Path "logs" -File | ForEach-Object {
        try {
            Copy-Item -Path $_.FullName -Destination (Join-Path $logsDir $_.Name) -Force -ErrorAction Stop
        }
        catch {
            Write-Host "Log em uso, ignorado: $($_.Name)" -ForegroundColor Yellow
        }
    }
}

Write-Host "Backup criado em: $targetDir" -ForegroundColor Green
