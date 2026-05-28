# Raiz Coletiva

Rede social da juventude do MST com feed visual, perfis, mensagens diretas, modulo de saude e base de seguranca reforcada.

## Recursos principais

- Cadastro com usuario customizado.
- Login por nome de usuario ou identificador numerico.
- 2FA opcional por desafio temporario.
- Feed com publicacoes, curtidas, comentarios, stories e niveis de visibilidade.
- Perfis com seguir, deixar de seguir, perfil privado e bloqueio entre usuarios.
- Mensagens diretas com controles de denuncia.
- Modulo de saude para acompanhamento interno.
- Auditoria de login, eventos de seguranca e protecao de midias.
- Rate limit para login, posts, comentarios, mensagens, uploads e recuperacao de senha.
- Bootstrap com usuarios e dados demo.

## Requisitos

- Windows com Python 3.14 disponivel via `py -3.14`.
- Para ambiente minimo local: `requirements.txt`.
- Para producao ou recursos completos: `requirements-prod.txt`.
- Docker Desktop, se for usar `docker-compose.yml`.

## Instalar dependencias

Ambiente local minimo:

```powershell
py -3.14 -m pip install -r requirements.txt
```

Ambiente completo de producao/desenvolvimento:

```powershell
py -3.14 -m pip install -r requirements-prod.txt
```

## Configurar ambiente

Para desenvolvimento local:

```powershell
Copy-Item .env.local.example .env
```

Para Docker ou producao, use o modelo de producao e ajuste senhas, dominios e HTTPS:

```powershell
Copy-Item .env.prod.example .env
```

O Django carrega automaticamente `.env` quando o arquivo existe na raiz do projeto. As variaveis ja definidas no sistema operacional continuam tendo prioridade.

## Como iniciar localmente

Use o menu operacional:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Ou rode manualmente:

```powershell
$env:RAIZ_DEBUG="True"
py -3.14 manage.py migrate
py -3.14 manage.py bootstrap_juventude_mst
py -3.14 manage.py runserver
```

Abra:

```text
http://127.0.0.1:8000/
```

## Compartilhar na rede local

Para abrir o sistema em outro computador ou celular na mesma rede:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_lan.ps1
```

Para conferir a URL sem iniciar o servidor:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_lan.ps1 -ShowOnly
```

Se outro aparelho nao conseguir acessar, confira o firewall do Windows na porta `8000`.

## Perfis demo

- `coord.juventude`
- `brigada.campo`
- `comunica.mst`
- `maria.raiz`

Senha demo:

```text
MstJuventude!2026
```

Para recriar a base inicial:

```powershell
py -3.14 manage.py bootstrap_juventude_mst
```

## Testes

```powershell
py -3.14 manage.py check
py -3.14 manage.py test --settings=juventude_mst.settings.test
```

Os testes usam cache local e sessao em banco, entao nao precisam de Redis.

Para validar dependencias, configuracao Django e testes de uma vez:

```powershell
powershell -ExecutionPolicy Bypass -File .\validate.ps1
```

## Backup local

Para salvar uma copia do banco SQLite, arquivos enviados e logs:

```powershell
powershell -ExecutionPolicy Bypass -File .\backup.ps1
```

Os backups ficam em `backups/<data-hora>/`.

Para restaurar um backup local:

```powershell
powershell -ExecutionPolicy Bypass -File .\restore.ps1 -BackupDir .\backups\20260518-120000
```

O script pede confirmacao antes de substituir dados.

## Variaveis de ambiente

Use `.env.example` como referencia. As principais variaveis sao:

- `RAIZ_SECRET_KEY`
- `RAIZ_DEBUG`
- `RAIZ_ALLOWED_HOSTS`
- `RAIZ_CSRF_TRUSTED_ORIGINS`
- `RAIZ_SECURE_SSL_REDIRECT`
- `RAIZ_TRUST_X_FORWARDED_FOR`
- `RAIZ_ENABLE_REALTIME`
- `RAIZ_DB_ENGINE`
- `RAIZ_CACHE_BACKEND`
- `RAIZ_CACHE_LOCATION`
- `RAIZ_JWT_ACCESS_TOKEN_TTL_MINUTES`
- `RAIZ_JWT_REFRESH_TOKEN_TTL_DAYS`
- `RAIZ_BLOCKED_TERMS`
- `RAIZ_SENSITIVE_TERMS`

## Docker

Configure `.env` a partir de `.env.example` e suba os servicos:

```powershell
Copy-Item .env.prod.example .env
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py bootstrap_juventude_mst
```

O Docker usa PostgreSQL, Redis e a imagem Python 3.14.

## Producao

Antes de colocar em internet aberta:

- Defina `RAIZ_DEBUG=False`.
- Troque `RAIZ_SECRET_KEY`.
- Configure `RAIZ_ALLOWED_HOSTS` com o dominio real.
- Configure `RAIZ_CSRF_TRUSTED_ORIGINS` com HTTPS.
- Use PostgreSQL.
- Use Redis para cache, sessao e canais em tempo real.
- Ative HTTPS no proxy reverso.
- Configure backups do banco e da pasta `media`.
- Monitore `logs/raiz.log` e `logs/security.log`.

Exemplo de variaveis de producao:

```text
RAIZ_DEBUG=False
RAIZ_SECRET_KEY=<gere-uma-chave-aleatoria-com-64-caracteres-ou-mais>
RAIZ_ALLOWED_HOSTS=deepenff.com,www.deepenff.com
RAIZ_CSRF_TRUSTED_ORIGINS=https://deepenff.com,https://www.deepenff.com
RAIZ_DB_ENGINE=django.db.backends.postgresql
RAIZ_DB_NAME=raiz_db
RAIZ_DB_USER=postgres
RAIZ_DB_PASSWORD=senha-forte
RAIZ_DB_HOST=db
RAIZ_DB_PORT=5432
RAIZ_CACHE_BACKEND=django.core.cache.backends.redis.RedisCache
RAIZ_CACHE_LOCATION=redis://redis:6379/0
RAIZ_SECURE_SSL_REDIRECT=True
```

## Estrutura

```text
.
|-- accounts/              Autenticacao, usuarios, perfis e login
|-- core/                  Seguranca, auditoria, uploads e home
|-- health/                Modulo de saude
|-- messaging/             Mensagens diretas
|-- social/                Feed, posts, stories e comunidade
|-- juventude_mst/         Configuracao Django
|-- juventude_mst/settings Configuracoes base, local, test e prod
|-- templates/             Templates HTML
|-- static/                CSS e JavaScript
|-- media/                 Arquivos enviados no ambiente local
|-- logs/                  Logs locais
|-- start.ps1              Menu operacional Windows
|-- start_lan.ps1          Inicializacao na rede local
|-- backup.ps1             Backup local de banco, media e logs
|-- restore.ps1            Restauracao de backup local
|-- validate.ps1           Check completo do projeto
|-- .env.local.example     Exemplo de ambiente local
|-- .env.prod.example      Exemplo de ambiente de producao
|-- .dockerignore          Exclusoes para build Docker
|-- requirements.txt       Dependencias minimas locais
|-- requirements-prod.txt  Dependencias completas
|-- docker-compose.yml     PostgreSQL, Redis e Django
|-- Dockerfile             Imagem da aplicacao
```

## Proximos pontos tecnicos

- Testar o build Docker completo.
- Criar painel administrativo para logs, denuncias e saude operacional.
