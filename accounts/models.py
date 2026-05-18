import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.security import build_protected_media_url


def generate_login_id():
    return 1_000_000_000 + secrets.randbelow(8_000_000_000)


class User(AbstractUser):
    class Role(models.TextChoices):
        MEMBER = 'member', 'Membro'
        COLLECTIVE = 'collective', 'Coletivo'
        MODERATOR = 'moderator', 'Moderador'
        ADMIN = 'admin', 'Administrador'
        FOUNDER = 'founder', 'Fundador'

    class TwoFactorChannel(models.TextChoices):
        CONSOLE = 'console', 'Console'
        SMS = 'sms', 'SMS'
        WHATSAPP = 'whatsapp', 'WhatsApp'

    class BackgroundTheme(models.TextChoices):
        TERRA = 'terra', 'Terra'
        MATA = 'mata', 'Mata'
        CEU = 'ceu', 'Ceu'
        NOITE = 'noite', 'Noite'
        SEMENTE = 'semente', 'Semente'

    email = models.EmailField('email address', unique=True)
    login_id = models.PositiveBigIntegerField(unique=True, null=True, blank=True, db_index=True)
    handle = models.SlugField(
        max_length=40,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9_-]+$',
                message='Use apenas letras minusculas, numeros, sublinhado e hifen no identificador.',
            )
        ],
    )
    display_name = models.CharField(max_length=120)
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=24, blank=True)
    bio = models.CharField(max_length=280, blank=True)
    location = models.CharField(max_length=120, blank=True)
    avatar = models.FileField(
        upload_to='avatars/%Y/%m/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    avatar_url = models.URLField(blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_health_operator = models.BooleanField(default=False)
    is_profile_private = models.BooleanField(default=False)
    requires_moderation_review = models.BooleanField(default=False)
    onboarding_completed = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_channel = models.CharField(
        max_length=20,
        choices=TwoFactorChannel.choices,
        default=TwoFactorChannel.CONSOLE,
    )
    background_theme = models.CharField(
        max_length=20,
        choices=BackgroundTheme.choices,
        default=BackgroundTheme.TERRA,
    )
    last_two_factor_verified_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    blocked_users = models.ManyToManyField(
        'self',
        through='UserBlock',
        through_fields=('blocker', 'blocked'),
        symmetrical=False,
        related_name='blocked_by_users',
    )

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.get_full_name().strip() or self.username
        if not self.login_id:
            candidate = generate_login_id()
            while type(self).objects.exclude(pk=self.pk).filter(login_id=candidate).exists():
                candidate = generate_login_id()
            self.login_id = candidate
        if not self.handle:
            base_value = slugify(self.username or self.display_name or 'juventude').replace('-', '_') or 'juventude'
            candidate = base_value[:40]
            suffix = 1
            while type(self).objects.exclude(pk=self.pk).filter(handle=candidate).exists():
                candidate = f'{base_value[:32]}_{suffix}'[:40]
                suffix += 1
            self.handle = candidate
        if self.role in {self.Role.ADMIN, self.Role.FOUNDER}:
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.username

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = timezone.localdate()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))

    @property
    def is_minor(self):
        age = self.age
        return age is not None and age < 18

    @property
    def can_moderate(self):
        return self.is_authenticated and self.role in {
            self.Role.MODERATOR,
            self.Role.ADMIN,
            self.Role.FOUNDER,
        }

    @property
    def can_administer(self):
        return self.is_authenticated and self.role in {self.Role.ADMIN, self.Role.FOUNDER}

    @property
    def can_found(self):
        return self.is_authenticated and self.role == self.Role.FOUNDER

    @property
    def can_view_all_content(self):
        return self.is_authenticated and (self.can_administer or self.can_found or self.is_superuser)

    @property
    def can_operate_health(self):
        return self.is_authenticated and (
            self.is_health_operator or self.can_administer or self.can_found or self.is_superuser
        )

    def has_recent_strong_auth(self, window_minutes=15):
        recent_reference = self.last_two_factor_verified_at or self.last_login
        if not recent_reference:
            return False
        return recent_reference >= timezone.now() - timedelta(minutes=window_minutes)

    def blocks(self, target):
        if not self.is_authenticated or not target:
            return False
        return UserBlock.objects.filter(blocker=self, blocked=target).exists()

    def is_blocked_by(self, target):
        if not self.is_authenticated or not target:
            return False
        return UserBlock.objects.filter(blocker=target, blocked=self).exists()

    def can_view_profile(self, viewer):
        if getattr(viewer, 'can_view_all_content', False):
            return True
        if viewer == self:
            return True
        if not getattr(viewer, 'is_authenticated', False):
            return False
        if self.blocks(viewer):
            return False
        if viewer.blocks(self):
            return True
        if self.is_profile_private:
            return self.follower_links.filter(follower=viewer).exists()
        return True

    @property
    def avatar_view_url(self):
        if not self.avatar:
            return self.avatar_url
        return build_protected_media_url('avatar', self.pk, action='view')

    @property
    def avatar_download_url(self):
        if not self.avatar:
            return self.avatar_url
        return build_protected_media_url('avatar', self.pk, action='download')


class PasswordRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        APPROVED = 'approved', 'Aprovada'
        REJECTED = 'rejected', 'Recusada'

    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_requests',
    )
    requested_username = models.CharField(max_length=150)
    requested_email = models.EmailField()
    suggested_password_hash = models.CharField(max_length=255)
    note = models.CharField(max_length=280, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='processed_password_requests',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Solicitacao de senha para {self.target_user.username}'


class UserBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='block_entries')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_entries')
    reason = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['blocker', 'blocked'], name='unique_user_block'),
        ]

    def __str__(self):
        return f'{self.blocker} bloqueou {self.blocked}'


class TwoFactorChallenge(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = 'login', 'Login'
        RECOVERY = 'recovery', 'Recuperacao'
        ADMIN_ACTION = 'admin_action', 'Acao administrativa'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='two_factor_challenges')
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.LOGIN)
    channel = models.CharField(
        max_length=20,
        choices=User.TwoFactorChannel.choices,
        default=User.TwoFactorChannel.CONSOLE,
    )
    code_hash = models.CharField(max_length=255)
    sent_to = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempt_total = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def is_active(self):
        return self.consumed_at is None and self.expires_at >= timezone.now()

    def verify_code(self, raw_code):
        self.attempt_total += 1
        self.save(update_fields=['attempt_total'])
        if not self.is_active():
            return False
        if not check_password(str(raw_code or '').strip(), self.code_hash):
            return False
        self.consumed_at = timezone.now()
        self.save(update_fields=['consumed_at'])
        return True

    @classmethod
    def issue(cls, user, channel, purpose=Purpose.LOGIN, ttl_minutes=10):
        raw_code = f'{secrets.randbelow(1_000_000):06d}'
        if channel in {User.TwoFactorChannel.SMS, User.TwoFactorChannel.WHATSAPP}:
            sent_to = user.phone_number
        elif user.email:
            sent_to = user.email
        else:
            sent_to = channel
        challenge = cls.objects.create(
            user=user,
            purpose=purpose,
            channel=channel,
            code_hash=make_password(raw_code),
            sent_to=sent_to,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
        return challenge, raw_code

    def __str__(self):
        return f'2FA {self.user} {self.purpose}'


class ApiRefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_refresh_tokens')
    token_hash = models.CharField(max_length=255)
    jti = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def is_active(self):
        return self.revoked_at is None and self.expires_at >= timezone.now()

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])

    def verify_token(self, raw_token):
        return self.is_active() and check_password(raw_token, self.token_hash)

    @classmethod
    def issue(cls, user, raw_token, jti, ip_address='', user_agent='', ttl_days=7):
        return cls.objects.create(
            user=user,
            token_hash=make_password(raw_token),
            jti=jti,
            ip_address=ip_address or None,
            user_agent=(user_agent or '')[:255],
            expires_at=timezone.now() + timedelta(days=ttl_days),
        )
