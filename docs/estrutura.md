# Estrutura do Sistema

Nome publico: `Rede Raizes Socialista`.

O projeto continua organizado como um monolito Django modular. Cada pasta de app tem responsabilidade clara e nao deve misturar telas, modelos ou regras de outro setor.

## Pastas Principais

```text
accounts/       cadastro, login, perfil, permissoes e recuperacao
core/           home, seguranca, auditoria, uploads, midia protegida e comandos
health/         setor de saude
messaging/      conversas diretas
social/         feed, comunidades, stories, relatoria e relacoes sociais
warehouse/      almoxarifado, acervo de quadros, movimentacoes, atividades e estoque
juventude_mst/  settings, urls, ASGI e WSGI
templates/      templates separados por app
static/         CSS e JS compartilhados
media/          arquivos enviados localmente
logs/           logs locais
docs/           documentacao tecnica
```

## Regra de Nomenclatura

- Pastas e arquivos tecnicos: minusculo, sem acento, sem espaco.
- Templates por modulo: `templates/<app>/<pagina>.html`.
- Apps Django: nomes curtos em ingles tecnico quando ja existem (`accounts`, `social`, `warehouse`).
- Texto exibido ao usuario: portugues simples e padronizado.
- Nome publico do produto: `Rede Raizes Socialista`.

## Cadastros Especiais

As areas sensiveis entram por permissao no perfil:

- `is_rapporteur`: relatoria
- `is_health_operator`: saude
- `is_warehouse_operator`: almoxarifado

Essas permissoes aparecem no centro de gestao e tambem no admin Django.
