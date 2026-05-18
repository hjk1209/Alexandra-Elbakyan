from django.conf import settings
from django.db import models


class LoginAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='login_attempts',
    )
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    was_successful = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['username', 'attempted_at']),
            models.Index(fields=['ip_address', 'attempted_at']),
        ]

    def __str__(self):
        status = 'ok' if self.was_successful else 'falhou'
        return f'{self.username} - {status}'


class SecurityEvent(models.Model):
    class EventType(models.TextChoices):
        LOGIN_SUCCESS = 'login_success', 'Login bem-sucedido'
        LOGIN_FAILURE = 'login_failure', 'Falha de login'
        TWO_FACTOR_CHALLENGE = 'two_factor_challenge', 'Desafio 2FA enviado'
        TWO_FACTOR_SUCCESS = 'two_factor_success', '2FA validado'
        TWO_FACTOR_FAILURE = 'two_factor_failure', 'Falha no 2FA'
        TOKEN_ISSUED = 'token_issued', 'JWT emitido'
        TOKEN_REFRESHED = 'token_refreshed', 'Refresh token usado'
        TOKEN_REVOKED = 'token_revoked', 'Refresh token revogado'
        LOGOUT = 'logout', 'Logout'
        LOCKOUT = 'lockout', 'Bloqueio temporario'
        SIGNUP = 'signup', 'Cadastro'
        THROTTLE = 'throttle', 'Limitacao de frequencia'
        USER_CREATED = 'user_created', 'Usuario criado'
        USER_DEACTIVATED = 'user_deactivated', 'Usuario desativado'
        USER_REACTIVATED = 'user_reactivated', 'Usuario reativado'
        USER_BLOCKED = 'user_blocked', 'Usuario bloqueado'
        USER_UNBLOCKED = 'user_unblocked', 'Usuario desbloqueado'
        MESSAGE_REPORTED = 'message_reported', 'Mensagem reportada'
        DOWNLOAD = 'download', 'Arquivo baixado'
        ADMIN_ACCESS = 'admin_access', 'Acesso administrativo'
        PERMISSION_CHANGED = 'permission_changed', 'Permissao alterada'
        PASSWORD_REQUESTED = 'password_requested', 'Solicitacao de senha'
        PASSWORD_REQUEST_APPROVED = 'password_request_approved', 'Solicitacao de senha aprovada'
        PASSWORD_REQUEST_REJECTED = 'password_request_rejected', 'Solicitacao de senha recusada'
        HEALTH_RECORD_UPDATED = 'health_record_updated', 'Ficha de saude atualizada'
        HEALTH_APPOINTMENT_SCHEDULED = 'health_appointment_scheduled', 'Agendamento de saude criado'
        HEALTH_APPOINTMENT_UPDATED = 'health_appointment_updated', 'Agendamento de saude atualizado'
        HEALTH_CONSULTATION_RECORDED = 'health_consultation_recorded', 'Consulta de saude registrada'
        CONTENT_BLOCKED = 'content_blocked', 'Conteudo bloqueado'

    class Severity(models.TextChoices):
        INFO = 'info', 'Informacao'
        WARNING = 'warning', 'Alerta'
        CRITICAL = 'critical', 'Critico'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='security_events',
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    request_path = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} ({self.get_severity_display()})'
