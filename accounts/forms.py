from django import forms
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from django.contrib.auth.forms import UserCreationForm

from core.security import clean_plain_text
from core.uploads import validate_safe_image_upload

from .models import PasswordRequest, User


def configure_account_fields(form, allow_privileged_roles=False, can_change_roles=False):
    form.fields['username'].label = 'Usuario interno'
    form.fields['username'].help_text = 'Esse identificador interno ajuda a organizar o cadastro.'
    form.fields['username'].widget.attrs.update(
        {
            'placeholder': 'ex.: joana.base',
            'autocomplete': 'username',
        }
    )
    form.fields['username'].error_messages['required'] = 'Informe um usuario interno.'

    form.fields['display_name'].label = 'Nome'
    form.fields['display_name'].help_text = 'Esse nome aparece no seu perfil e nas publicacoes.'
    form.fields['display_name'].widget.attrs.update(
        {
            'placeholder': 'Seu nome ou nome do coletivo',
            'autocomplete': 'name',
        }
    )
    form.fields['display_name'].error_messages['required'] = 'Informe seu nome.'

    form.fields['handle'].label = 'Nome de perfil'
    form.fields['handle'].help_text = 'Vai aparecer publicamente como @nome_de_perfil.'
    form.fields['handle'].widget.attrs.update(
        {
            'placeholder': 'ex.: juventude_base',
            'autocomplete': 'nickname',
        }
    )
    form.fields['handle'].error_messages['required'] = 'Informe o nome do perfil.'

    form.fields['email'].label = 'Email'
    form.fields['email'].help_text = 'Usado para identificacao e recuperacao futura da conta.'
    form.fields['email'].widget.attrs.update(
        {
            'placeholder': 'voce@exemplo.com',
            'autocomplete': 'email',
        }
    )
    form.fields['email'].error_messages['required'] = 'Informe um email valido.'

    form.fields['birth_date'].label = 'Data de nascimento'
    form.fields['birth_date'].help_text = 'Necessaria para filtrar conteudos adequados por idade.'
    form.fields['birth_date'].widget.attrs.update({'type': 'date'})

    form.fields['phone_number'].label = 'WhatsApp ou telefone'
    form.fields['phone_number'].required = False
    form.fields['phone_number'].help_text = 'Opcional. Serve para receber codigo de verificacao em 2 etapas.'
    form.fields['phone_number'].widget.attrs.update({'placeholder': '+55 81 99999-9999', 'autocomplete': 'tel'})

    form.fields['role'].label = 'Tipo de perfil'
    form.fields['bio'].label = 'Bio'
    form.fields['bio'].required = False
    form.fields['bio'].help_text = 'Opcional. Uma frase curta sobre voce ou seu coletivo.'
    form.fields['bio'].widget.attrs.update({'placeholder': 'Fale um pouco sobre este perfil.'})

    form.fields['location'].label = 'Local'
    form.fields['location'].required = False
    form.fields['location'].help_text = 'Opcional. Cidade, assentamento, escola ou territorio.'
    form.fields['location'].widget.attrs.update({'placeholder': 'Ex.: Recife, ENFF, Assentamento Terra Livre'})

    form.fields['avatar'].label = 'Foto do perfil por arquivo'
    form.fields['avatar'].required = False
    form.fields['avatar'].help_text = 'Opcional. Envie uma imagem segura em JPG, PNG ou WEBP.'

    form.fields['password1'].label = 'Senha'
    form.fields['password1'].help_text = 'Use pelo menos 12 caracteres e evite senhas obvias.'
    form.fields['password1'].widget.attrs.update({'autocomplete': 'new-password'})
    form.fields['password1'].error_messages['required'] = 'Crie uma senha para a conta.'

    form.fields['password2'].label = 'Confirmar senha'
    form.fields['password2'].help_text = 'Repita a mesma senha para confirmar.'
    form.fields['password2'].widget.attrs.update({'autocomplete': 'new-password'})
    form.fields['password2'].error_messages['required'] = 'Confirme a senha para concluir o cadastro.'

    if allow_privileged_roles:
        role_choices = [
            (User.Role.MEMBER, 'Membro'),
            (User.Role.COLLECTIVE, 'Coletivo'),
            (User.Role.MODERATOR, 'Moderador'),
        ]
        if can_change_roles:
            role_choices.extend(
                [
                    (User.Role.ADMIN, 'Administrador'),
                    (User.Role.FOUNDER, 'Fundador'),
                ]
            )
        form.fields['role'].choices = role_choices
        form.fields['role'].help_text = 'Moderadores revisam conteudo. Administradores e fundadores controlam areas sensiveis.'
    else:
        form.fields['role'].choices = [
            (User.Role.MEMBER, 'Membro'),
            (User.Role.COLLECTIVE, 'Coletivo'),
        ]
        form.fields['role'].initial = User.Role.MEMBER
        form.fields['role'].help_text = 'Perfis elevados sao liberados apenas pelo centro de protecao.'


class SignUpForm(UserCreationForm):
    error_messages = {
        'password_mismatch': 'As duas senhas informadas precisam ser iguais.',
    }

    class Meta:
        model = User
        fields = (
            'username',
            'display_name',
            'handle',
            'email',
            'birth_date',
            'phone_number',
            'role',
            'bio',
            'location',
            'avatar',
            'password1',
            'password2',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configure_account_fields(self, allow_privileged_roles=False)
        self.order_fields(
            [
                'display_name',
                'handle',
                'username',
                'email',
                'birth_date',
                'phone_number',
                'role',
                'bio',
                'location',
                'avatar',
                'password1',
                'password2',
            ]
        )

    def clean_display_name(self):
        return clean_plain_text(self.cleaned_data['display_name'])

    def clean_bio(self):
        return clean_plain_text(self.cleaned_data.get('bio', ''))

    def clean_location(self):
        return clean_plain_text(self.cleaned_data.get('location', ''))

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_avatar(self):
        return validate_safe_image_upload(self.cleaned_data.get('avatar'), max_size_mb=2, field_label='Foto do perfil')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.onboarding_completed = True
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(label='Nome de usuario')
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Seu nome de usuario', 'autocomplete': 'username'})
        self.fields['password'].widget.attrs.update({'autocomplete': 'current-password'})

    def clean_username(self):
        value = str(self.cleaned_data['username']).strip()
        if not value:
            raise forms.ValidationError('Informe seu nome de usuario.')
        return value


class TwoFactorVerificationForm(forms.Form):
    code = forms.CharField(label='Codigo de verificacao', max_length=6)

    def __init__(self, *args, challenge=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge = challenge
        self.fields['code'].widget.attrs.update({'placeholder': 'Digite o codigo de 6 digitos'})

    def clean_code(self):
        code = ''.join(ch for ch in str(self.cleaned_data['code']) if ch.isdigit())
        if len(code) != 6:
            raise forms.ValidationError('Informe o codigo completo com 6 digitos.')
        return code


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'display_name',
            'birth_date',
            'phone_number',
            'bio',
            'location',
            'avatar',
            'is_profile_private',
            'background_theme',
            'two_factor_enabled',
            'two_factor_channel',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].label = 'Foto do perfil por arquivo'
        self.fields['avatar'].help_text = 'Envie uma imagem segura em JPG, PNG ou WEBP para substituir a foto atual.'
        self.fields['birth_date'].label = 'Data de nascimento'
        self.fields['birth_date'].widget.attrs.update({'type': 'date'})
        self.fields['phone_number'].label = 'WhatsApp ou telefone'
        self.fields['background_theme'].label = 'Tema de fundo'
        self.fields['background_theme'].help_text = 'Escolha a atmosfera visual que aparece quando voce usa a plataforma.'
        self.fields['two_factor_enabled'].label = 'Ativar verificacao em duas etapas'
        self.fields['two_factor_channel'].label = 'Canal do codigo'
        self.fields['two_factor_channel'].help_text = 'O sistema gera codigo por canal escolhido e pode usar integracao externa depois.'

    def clean_display_name(self):
        return clean_plain_text(self.cleaned_data['display_name'])

    def clean_bio(self):
        return clean_plain_text(self.cleaned_data.get('bio', ''))

    def clean_location(self):
        return clean_plain_text(self.cleaned_data.get('location', ''))

    def clean_avatar(self):
        return validate_safe_image_upload(self.cleaned_data.get('avatar'), max_size_mb=2, field_label='Foto do perfil')

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get('two_factor_enabled')
            and cleaned_data.get('two_factor_channel') in {User.TwoFactorChannel.SMS, User.TwoFactorChannel.WHATSAPP}
            and not cleaned_data.get('phone_number')
        ):
            self.add_error('phone_number', 'Informe um telefone para ativar a verificacao em duas etapas.')
        return cleaned_data


class ManagedUserCreateForm(UserCreationForm):
    error_messages = {
        'password_mismatch': 'As duas senhas informadas precisam ser iguais.',
    }

    class Meta:
        model = User
        fields = (
            'username',
            'display_name',
            'handle',
            'email',
            'birth_date',
            'phone_number',
            'role',
            'is_health_operator',
            'bio',
            'location',
            'avatar',
            'password1',
            'password2',
        )

    def __init__(self, *args, **kwargs):
        self.can_change_roles = kwargs.pop('can_change_roles', False)
        super().__init__(*args, **kwargs)
        configure_account_fields(self, allow_privileged_roles=True, can_change_roles=self.can_change_roles)
        self.fields['is_health_operator'].label = 'Operador da unidade de saude'
        self.fields['is_health_operator'].required = False
        self.fields['is_health_operator'].help_text = 'Permite gerenciar consultas, agendamentos e registros do setor de saude.'

    def clean_display_name(self):
        return clean_plain_text(self.cleaned_data['display_name'])

    def clean_bio(self):
        return clean_plain_text(self.cleaned_data.get('bio', ''))

    def clean_location(self):
        return clean_plain_text(self.cleaned_data.get('location', ''))

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_avatar(self):
        return validate_safe_image_upload(self.cleaned_data.get('avatar'), max_size_mb=2, field_label='Foto do perfil')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.onboarding_completed = True
        if commit:
            user.save()
        return user


class ManagedUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'display_name',
            'handle',
            'email',
            'birth_date',
            'phone_number',
            'role',
            'is_health_operator',
            'bio',
            'location',
            'is_profile_private',
            'background_theme',
            'two_factor_enabled',
            'two_factor_channel',
        )

    def __init__(self, *args, can_change_roles=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['display_name'].label = 'Nome'
        self.fields['handle'].label = 'Nome de perfil'
        self.fields['email'].label = 'Email'
        self.fields['birth_date'].label = 'Data de nascimento'
        self.fields['birth_date'].widget.attrs.update({'type': 'date'})
        self.fields['phone_number'].label = 'WhatsApp ou telefone'
        self.fields['role'].label = 'Tipo de perfil'
        self.fields['is_health_operator'].label = 'Operador da unidade de saude'
        self.fields['bio'].label = 'Bio'
        self.fields['location'].label = 'Local'
        self.fields['is_profile_private'].label = 'Perfil privado'
        self.fields['background_theme'].label = 'Tema de fundo'
        self.fields['two_factor_enabled'].label = 'Ativar verificacao em duas etapas'
        self.fields['two_factor_channel'].label = 'Canal do codigo'
        if not can_change_roles:
            self.fields.pop('role')

    def clean_display_name(self):
        return clean_plain_text(self.cleaned_data['display_name'])

    def clean_bio(self):
        return clean_plain_text(self.cleaned_data.get('bio', ''))

    def clean_location(self):
        return clean_plain_text(self.cleaned_data.get('location', ''))

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get('two_factor_enabled')
            and cleaned_data.get('two_factor_channel') in {User.TwoFactorChannel.SMS, User.TwoFactorChannel.WHATSAPP}
            and not cleaned_data.get('phone_number')
        ):
            self.add_error('phone_number', 'Informe um telefone para ativar a verificacao em duas etapas.')
        return cleaned_data


class AdminActionReasonForm(forms.Form):
    reason = forms.CharField(
        label='Explicacao obrigatoria',
        min_length=12,
        max_length=500,
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'placeholder': 'Explique o motivo da decisao para ficar registrado na auditoria.',
            }
        ),
    )

    def clean_reason(self):
        return clean_plain_text(self.cleaned_data['reason'])


class PasswordRequestForm(forms.Form):
    username = forms.CharField(label='Nome de usuario da conta')
    email = forms.EmailField(label='Email da conta')
    suggested_password1 = forms.CharField(label='Senha sugerida', widget=forms.PasswordInput)
    suggested_password2 = forms.CharField(label='Confirmar senha sugerida', widget=forms.PasswordInput)
    note = forms.CharField(
        label='Observacao da solicitacao',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Explique por que precisa da liberacao da senha.'}),
    )

    error_messages = {
        'password_mismatch': 'As duas senhas sugeridas precisam ser iguais.',
        'pending_request': 'Ja existe uma solicitacao de senha pendente para essa conta.',
        'account_not_found': 'Nao encontramos conta com esse nome de usuario e email.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'usuario cadastrado na conta', 'autocomplete': 'username'})
        self.fields['email'].widget.attrs.update({'placeholder': 'email cadastrado na conta'})
        self.fields['suggested_password1'].help_text = 'Digite a senha que voce quer usar depois da aprovacao do adm.'
        self.fields['suggested_password2'].help_text = 'Repita a mesma senha para confirmar a solicitacao.'

    def clean_note(self):
        return clean_plain_text(self.cleaned_data.get('note', ''))

    def clean(self):
        cleaned_data = super().clean()
        username = str(cleaned_data.get('username') or '').strip()
        email = (cleaned_data.get('email') or '').strip().lower()
        password1 = cleaned_data.get('suggested_password1')
        password2 = cleaned_data.get('suggested_password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(self.error_messages['password_mismatch'])

        if username and email:
            target_user = User.objects.filter(username__iexact=username, email__iexact=email).first()
            if target_user is None:
                raise forms.ValidationError(self.error_messages['account_not_found'])
            if PasswordRequest.objects.filter(target_user=target_user, status=PasswordRequest.Status.PENDING).exists():
                raise forms.ValidationError(self.error_messages['pending_request'])
            cleaned_data['target_user'] = target_user
            if password1:
                try:
                    validate_password(password1, user=target_user)
                except forms.ValidationError as error:
                    self.add_error('suggested_password1', error)
        return cleaned_data

    def save(self):
        target_user = self.cleaned_data['target_user']
        return PasswordRequest.objects.create(
            target_user=target_user,
            requested_username=target_user.username,
            requested_email=target_user.email,
            suggested_password_hash=make_password(self.cleaned_data['suggested_password1']),
            note=self.cleaned_data.get('note', ''),
        )
