param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Run-Local {
    $env:RAIZ_DEBUG = "True"
    $env:DJANGO_SETTINGS_MODULE = "juventude_mst.settings.local"
    $env:RAIZ_SECURE_SSL_REDIRECT = "False"
    $env:RAIZ_ENABLE_REALTIME = "False"
    $env:RAIZ_CACHE_BACKEND = "django.core.cache.backends.locmem.LocMemCache"
    $env:RAIZ_CACHE_LOCATION = ""
    if (-not $env:RAIZ_ALLOWED_HOSTS) {
        $env:RAIZ_ALLOWED_HOSTS = "127.0.0.1,localhost,testserver"
    }
    py -3.14 manage.py runserver "127.0.0.1:$Port"
}

function Run-Lan {
    powershell -ExecutionPolicy Bypass -File .\start_lan.ps1 -Port $Port
}

function Run-Migrations {
    $env:DJANGO_SETTINGS_MODULE = "juventude_mst.settings.local"
    py -3.14 manage.py migrate
}

function Run-Bootstrap {
    $env:DJANGO_SETTINGS_MODULE = "juventude_mst.settings.local"
    py -3.14 manage.py bootstrap_juventude_mst
}

function Run-Tests {
    py -3.14 manage.py test --settings=juventude_mst.settings.test
}

function Run-Check {
    py -3.14 manage.py check --settings=juventude_mst.settings.local
}

function Run-Backup {
    powershell -ExecutionPolicy Bypass -File .\backup.ps1
}

function Run-Restore {
    $backupPath = Read-Host "Informe a pasta do backup"
    powershell -ExecutionPolicy Bypass -File .\restore.ps1 -BackupDir $backupPath
}

function Run-Validate {
    powershell -ExecutionPolicy Bypass -File .\validate.ps1
}

function Show-Menu {
    Clear-Host
    Write-Host "Raiz Coletiva - menu de operacao" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Iniciar local em http://127.0.0.1:$Port/"
    Write-Host "2. Compartilhar na rede local"
    Write-Host "3. Aplicar migrations"
    Write-Host "4. Recriar dados demo"
    Write-Host "5. Rodar testes"
    Write-Host "6. Rodar check do Django"
    Write-Host "7. Criar backup local"
    Write-Host "8. Restaurar backup local"
    Write-Host "9. Validar projeto completo"
    Write-Host "0. Sair"
    Write-Host ""
}

do {
    Show-Menu
    $choice = Read-Host "Escolha uma opcao"
    switch ($choice) {
        "1" { Run-Local; break }
        "2" { Run-Lan; break }
        "3" { Run-Migrations; Pause }
        "4" { Run-Bootstrap; Pause }
        "5" { Run-Tests; Pause }
        "6" { Run-Check; Pause }
        "7" { Run-Backup; Pause }
        "8" { Run-Restore; Pause }
        "9" { Run-Validate; Pause }
        "0" { return }
        default {
            Write-Host "Opcao invalida." -ForegroundColor Yellow
            Pause
        }
    }
} while ($true)
