# Rede Raizes Socialista

Sistema Django para rede social comunitaria com cadastro basico, feed, comunidades, relatoria, saude, almoxarifado, mensagens e seguranca operacional.

## Inicio Rapido

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 manage.py migrate --settings=juventude_mst.settings.local
py -3.14 manage.py bootstrap_juventude_mst --settings=juventude_mst.settings.local
py -3.14 manage.py runserver 127.0.0.1:8000 --settings=juventude_mst.settings.local
```

Abra:

```text
http://127.0.0.1:8000/
```

No Windows, o menu operacional tambem faz esse fluxo:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

## Cadastro Basico

O cadastro publico fica em:

```text
http://127.0.0.1:8000/conta/cadastro/
```

Campos principais:

- nome
- nome de perfil
- usuario interno
- email
- tipo de perfil
- senha

Perfis especiais, como Relatoria, Saude e Almoxarifado, sao liberados pela gestao em `Protecao/Gestao`.

## Perfis Demo

Todos usam a senha:

```text
MstJuventude!2026
```

- `coord.juventude` - fundador/gestao
- `brigada.campo` - comunidade/coletivo
- `comunica.mst` - moderacao e relatoria
- `maria.raiz` - membro comum
- `saude.unidade` - operador de saude
- `almox.enff` - operador de almoxarifado

## Dependencias

Ambiente local minimo:

```powershell
py -3.14 -m pip install -r requirements.txt
```

Producao/Docker:

```powershell
py -3.14 -m pip install -r requirements-prod.txt
```

Detalhes ficam em [docs/dependencias.md](docs/dependencias.md).

## Validacao

```powershell
py -3.14 manage.py check --settings=juventude_mst.settings.local
py -3.14 manage.py makemigrations --check --dry-run --settings=juventude_mst.settings.local
py -3.14 manage.py test --settings=juventude_mst.settings.test
```

Ou:

```powershell
powershell -ExecutionPolicy Bypass -File .\validate.ps1
```

## Estrutura

```text
accounts/       usuarios, login, cadastro e permissoes
core/           home, seguranca, auditoria, midia protegida e comandos
health/         modulo de saude
messaging/      mensagens diretas
social/         feed, comunidades, stories e relatoria
warehouse/      almoxarifado, acervo, movimentacoes e estoque
juventude_mst/  configuracao Django e rotas principais
templates/      HTML por modulo
static/         CSS e JavaScript
media/          arquivos enviados em ambiente local
logs/           logs locais
docs/           documentacao tecnica padronizada
```

Detalhes ficam em [docs/estrutura.md](docs/estrutura.md).

## Documentos Padronizados

- [docs/estrutura.md](docs/estrutura.md)
- [docs/dependencias.md](docs/dependencias.md)
- [docs/cadastro-basico.md](docs/cadastro-basico.md)

Os nomes foram mantidos em minusculo, sem espacos e em ASCII para evitar problemas no Windows, Docker e Git.

## Docker

```powershell
Copy-Item .env.prod.example .env
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py bootstrap_juventude_mst
```

## Rede Local

```powershell
powershell -ExecutionPolicy Bypass -File .\start_lan.ps1
```

## Backup Local

```powershell
powershell -ExecutionPolicy Bypass -File .\backup.ps1
```

Restaurar:

```powershell
powershell -ExecutionPolicy Bypass -File .\restore.ps1 -BackupDir .\backups\20260518-120000
```

## Variaveis Principais

O prefixo `RAIZ_` foi mantido por compatibilidade com scripts e ambientes antigos. O nome publico padrao agora e `Rede Raizes Socialista`.

- `RAIZ_SITE_NAME`
- `RAIZ_SITE_DESCRIPTION`
- `RAIZ_SECRET_KEY`
- `RAIZ_DEBUG`
- `RAIZ_ALLOWED_HOSTS`
- `RAIZ_CSRF_TRUSTED_ORIGINS`
- `RAIZ_ENABLE_REALTIME`
- `RAIZ_DB_ENGINE`
- `RAIZ_CACHE_BACKEND`
- `RAIZ_CACHE_LOCATION`
- `RAIZ_DEFAULT_FROM_EMAIL`
