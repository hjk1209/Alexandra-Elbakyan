from django.conf import settings
from django.core.mail import send_mail

from .models import User


def get_user_for_username(username):
    identifier = str(username or '').strip()
    if not identifier:
        return None
    return User.objects.filter(username__iexact=identifier, is_active=True).first()


def mask_contact(value):
    raw_value = str(value or '').strip()
    if not raw_value:
        return 'canal protegido'
    if len(raw_value) <= 4:
        return raw_value
    return f'{raw_value[:2]}***{raw_value[-2:]}'


def deliver_two_factor_code(user, challenge, raw_code):
    requested_destination = challenge.sent_to or user.phone_number or user.email or challenge.channel
    message = (
        f'Codigo de verificacao da Raiz Coletiva: {raw_code}\n'
        f'Canal escolhido: {challenge.get_channel_display()}\n'
        'Se voce nao tentou entrar, ignore esta mensagem.'
    )
    if user.email:
        send_mail(
            'Codigo de verificacao da Raiz Coletiva',
            message,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@raizcoletiva.local'),
            [user.email],
            fail_silently=True,
        )
    return mask_contact(requested_destination)
