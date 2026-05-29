# Dependencias

O projeto tem dois conjuntos de dependencias.

## Local Minimo

Arquivo: `requirements.txt`

Usado para rodar SQLite, cadastro, feed, comunidades, relatoria, saude, almoxarifado e testes locais.

```text
Django
bcrypt
```

## Producao

Arquivo: `requirements-prod.txt`

Inclui o local minimo com `-r requirements.txt` e adiciona somente o que o codigo usa em producao:

```text
psycopg2-binary
django-redis
redis
channels
channels-redis
daphne
gunicorn
whitenoise
```

## Removido da Lista de Producao

Foram retirados pacotes que nao tinham uso atual no codigo:

- Elasticsearch
- Django REST Framework
- Spectacular/OpenAPI
- Celery
- Sentry
- django-admin-interface
- django-cors-headers
- django-csp
- django-ratelimit
- factory-boy
- Faker
- python-decouple

Se algum desses recursos voltar a ser implementado no codigo, a dependencia deve ser recolocada junto com teste e documentacao.
