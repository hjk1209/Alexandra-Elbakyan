# Security Policy

## Reporting Security Vulnerabilities

Se você encontrou uma vulnerabilidade de segurança, **não abra uma issue pública**. 

Por favor, envie um email para `security@example.com` com:
- Descrição da vulnerabilidade
- Passos para reproduzir
- Impacto potencial
- Sugestão de fix (opcional)

Nós responderemos em até 48 horas.

## Segurança Implementada

### Autenticação & Autorização
- ✅ Password hashing com Argon2 (ou Bcrypt)
- ✅ Minimum 12 caracteres na senha
- ✅ 2FA opcional com TOTP
- ✅ Rate limiting em login (5 tentativas em 15 minutos)
- ✅ Controle de acesso por role (FOUNDER, ADMIN, MODERATOR, MEMBER, COLLECTIVE)
- ✅ Session timeout após 8 horas
- ✅ Login failure audit log

### Proteção de Dados
- ✅ HTTPS obrigatório em produção
- ✅ HSTS headers (1 year)
- ✅ CSRF protection em todos forms
- ✅ XSS protection (content-security-policy)
- ✅ SQL injection prevention (ORM Django)
- ✅ Protected media URLs com tokens assinados
- ✅ Soft delete (dados não são realmente deletados)

### API Security
- ✅ JWT tokens com TTL curto (10 minutos)
- ✅ Refresh tokens com secure cookies
- ✅ CORS configurado restritivamente
- ✅ Rate limiting por endpoint
- ✅ Input validation em todos endpoints

### Infrastructure
- ✅ Audit logs de segurança
- ✅ Logging de erros HTTP 4xx/5xx
- ✅ Health checks
- ✅ Connection pooling limitado
- ✅ Timeout em requisições (30 segundos)
- ✅ Cache headers apropriados

### Boas Práticas
- ✅ Senhas não são logadas
- ✅ Dados sensíveis não são cachados
- ✅ IPs de clientes são registrados
- ✅ User-agent é registrado
- ✅ Controle de acesso em views
- ✅ Permissions baseadas em roles

## Rate Limiting

```python
POST_RATE_LIMIT_PER_MINUTE = 8           # Posts
COMMENT_RATE_LIMIT_PER_MINUTE = 25       # Comentários
MESSAGE_RATE_LIMIT_PER_MINUTE = 40       # Mensagens
LIKE_RATE_LIMIT_PER_MINUTE = 80          # Likes
SIGNUP_RATE_LIMIT_PER_HOUR = 10          # Cadastros
LOGIN_API_RATE_LIMIT_PER_MINUTE = 12     # Login API
```

## Deployment Security

### Checklist
- [ ] `RAIZ_DEBUG = False`
- [ ] `RAIZ_SECRET_KEY` é aleatória e forte
- [ ] HTTPS/TLS configurado
- [ ] `RAIZ_ALLOWED_HOSTS` restrito
- [ ] `RAIZ_CSRF_TRUSTED_ORIGINS` configurado
- [ ] Usar PostgreSQL em produção
- [ ] Usar Redis em produção
- [ ] Backups regulares do database
- [ ] Logs monitorados
- [ ] Firewall configurado
- [ ] DDoS protection (Cloudflare, etc)

## Dependencies

Mantenha as dependências atualizadas:

```bash
pip list --outdated
pip install --upgrade -r requirements-prod.txt
```

Use `safety check` para verificar vulnerabilidades conhecidas:

```bash
pip install safety
safety check
```

## Monitoramento

Configure alertas para:
- Múltiplas falhas de login do mesmo IP
- Requisições a endpoints sensíveis
- Erros HTTP 5xx
- Consumo anormal de recursos
- Tentativas de acesso não autorizadas

Integre com:
- Sentry para error tracking
- Grafana para monitoring
- ELK stack para logging

## Compliance

Este projeto segue:
- OWASP Top 10 prevention
- Django security best practices
- GDPR data protection principles (onde aplicável)
- Regular security audits recomendadas

## Versões Afetadas

Se uma vulnerabilidade é encontrada, todas as versões são afetadas até que um patch seja lançado.

## Histórico de Segurança

| Versão | Data | Vulnerabilidade | Status |
|--------|------|-----------------|--------|
| 1.0.0  | -    | Inicial         | Stable |

---

Última atualização: 2026-05-18
