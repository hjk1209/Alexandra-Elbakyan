$ErrorActionPreference = "Stop"

Write-Host "Validando dependencias..." -ForegroundColor Cyan
py -3.14 -m pip check

Write-Host "Validando configuracao Django..." -ForegroundColor Cyan
py -3.14 manage.py check --settings=juventude_mst.settings.test

Write-Host "Rodando testes..." -ForegroundColor Cyan
py -3.14 manage.py test --settings=juventude_mst.settings.test

Write-Host "Validacao concluida." -ForegroundColor Green
