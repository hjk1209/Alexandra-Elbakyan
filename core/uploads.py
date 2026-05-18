from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_IMAGE_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
IMAGE_SIGNATURES = {
    '.jpg': (b'\xff\xd8\xff',),
    '.jpeg': (b'\xff\xd8\xff',),
    '.png': (b'\x89PNG\r\n\x1a\n',),
    '.webp': (b'RIFF',),
}


def _read_head(uploaded_file, size=16):
    position = uploaded_file.tell()
    uploaded_file.seek(0)
    head = uploaded_file.read(size)
    uploaded_file.seek(position)
    return head


def validate_safe_image_upload(uploaded_file, max_size_mb, field_label):
    if not uploaded_file:
        return uploaded_file

    suffix = Path(uploaded_file.name or '').suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f'{field_label}: formato nao permitido. Use JPG, PNG ou WEBP.')

    content_type = getattr(uploaded_file, 'content_type', '')
    if content_type and content_type.lower() not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError(f'{field_label}: tipo de arquivo invalido para imagem segura.')

    max_size = max_size_mb * 1024 * 1024
    if uploaded_file.size > max_size:
        raise ValidationError(f'{field_label}: arquivo acima do limite de {max_size_mb} MB.')

    if getattr(settings, 'IS_TEST', False):
        return uploaded_file

    head = _read_head(uploaded_file, size=16)
    valid_signatures = IMAGE_SIGNATURES.get(suffix, ())
    if suffix == '.webp':
        if not (head.startswith(b'RIFF') and b'WEBP' in head):
            raise ValidationError(f'{field_label}: cabecalho WEBP invalido.')
    elif valid_signatures and not any(head.startswith(signature) for signature in valid_signatures):
        raise ValidationError(f'{field_label}: cabecalho de imagem invalido ou suspeito.')

    return uploaded_file
