# Contributing to Rede Raizes Socialista

Obrigado por contribuir! Este guia explica como participar do projeto.

## Código de Conduta

Nós somos comprometidos com um ambiente acolhedor para todos. Leia nosso [Code of Conduct](CODE_OF_CONDUCT.md).

## Como Contribuir

### Reportar Bugs

1. Verifique se o bug já foi reportado em Issues
2. Descreva com clareza o problema
3. Forneça passos para reproduzir
4. Indique a versão do Django e Python
5. Inclua screenshots se relevante

**Template**:
```
**Descrição do bug**:
[Descrição clara]

**Passos para reproduzir**:
1. ...
2. ...

**Comportamento esperado**:
[O que deveria acontecer]

**Comportamento atual**:
[O que realmente acontece]

**Ambiente**:
- Python: [versão]
- Django: [versão]
- Browser: [se relevante]
```

### Sugerir Features

1. Verifique se já existe uma discussion
2. Descreva o caso de uso
3. Explique o benefício
4. Se possível, forneça um mockup

### Pull Requests

1. **Fork** o repositório
2. **Clone** seu fork
3. **Crie uma branch** para sua feature
   ```bash
   git checkout -b feature/sua-feature
   ```
4. **Commit** suas mudanças (veja [Commit Messages](#commit-messages))
5. **Push** para seu fork
6. **Abra uma PR** com descrição clara

#### Requisitos para PR

- [ ] Segue o estilo de código do projeto
- [ ] Inclui testes para novas funcionalidades
- [ ] Passa em `python manage.py test`
- [ ] Sem erros em `flake8` ou `bandit`
- [ ] Mensagens de commit claras
- [ ] Atualiza documentação se necessário

#### Processo de Review

1. Mínimo 1 review aprovado
2. Testes passando em CI/CD
3. Sem conflitos com `main`
4. Depois: merge automático

## Commit Messages

Siga o padrão:

```
[type]: [descrição breve]

[descrição longa opcional]

[footer opcional]
```

**Types**:
- `feat:` Nova funcionalidade
- `fix:` Corrige um bug
- `docs:` Muda documentação
- `style:` Formatação, sem lógica
- `refactor:` Refatoração
- `perf:` Melhoria de performance
- `test:` Adiciona/modifica testes
- `chore:` Atualizações, deps

**Exemplos**:
```
feat: adicionar soft delete em posts

docs: melhorar README com Docker setup

fix: corrigir rate limiting em login
```

## Estilo de Código

### Python (Django)

```python
# Use type hints
def get_user_by_id(user_id: int) -> User:
    return User.objects.get(id=user_id)

# Imports agrupados
from django.db import models
from django.utils import timezone

from core.security import get_client_ip  # Local imports por último

# Formatação
class MyModel(models.Model):
    field = models.CharField(max_length=100)
    
    def __str__(self) -> str:
        return self.name
    
    class Meta:
        ordering = ['-created_at']
```

### HTML/Templates

```html
<!-- Use double quotes -->
<div class="container">
    <form method="post" action="{% url 'view-name' %}">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Submit</button>
    </form>
</div>
```

### CSS/SCSS

```css
/* Use classes, não IDs -->
.post-container {
    display: flex;
    gap: 1rem;
}

.post-container__title {
    font-weight: 700;
}
```

### JavaScript

```javascript
// Use modern ES6+
const fetchUser = async (userId) => {
    try {
        const response = await fetch(`/api/users/${userId}/`);
        return response.json();
    } catch (error) {
        console.error('Error:', error);
    }
};
```

## Testes

### Adicionar testes

```python
from django.test import TestCase
from django.urls import reverse

class MyFeatureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test',
            password='testpass123'
        )
    
    def test_feature_works(self):
        response = self.client.get(reverse('my-view'))
        self.assertEqual(response.status_code, 200)
```

### Rodar testes

```bash
# Todos
python manage.py test

# Específico
python manage.py test social.tests.FeedTests

# Com cobertura
coverage run --source='.' manage.py test
coverage report
```

## Setup para Contribuidores

```bash
# Clone
git clone https://github.com/seu-username/rede-raizes-socialista.git
cd rede-raizes-socialista

# Venv
python -m venv venv
source venv/bin/activate

# Deps
pip install -r requirements.txt
pip install -r requirements-prod.txt

# Pre-commit hooks (recomendado)
pip install pre-commit
pre-commit install

# Migrate e rodar
python manage.py migrate
python manage.py runserver
```

## Documentação

- Docstrings em classes e funções importantes
- README para features principais
- Inline comments apenas para lógica complexa

## Licença

Ao contribuir, você concorda que suas contribuições serão sob a mesma licença do projeto.

## Questões?

- Abra uma Discussion no GitHub
- Envie um email para `dev@example.com`
- Participe do chat da comunidade

Obrigado por contribuir! 🙏
