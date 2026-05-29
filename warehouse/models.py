from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.security import build_protected_media_url


class Artwork(models.Model):
    name = models.CharField(max_length=160)
    inventory_number = models.CharField(max_length=60, unique=True)
    author = models.CharField(max_length=140, blank=True)
    storage_location = models.CharField(max_length=180, blank=True)
    photo = models.FileField(
        upload_to='almoxarifado/quadros/%Y/%m/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    condition_notes = models.CharField(max_length=240, blank=True)
    notes = models.TextField(max_length=1600, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_warehouse_artworks',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'inventory_number']

    def __str__(self):
        return f'{self.name} ({self.inventory_number})'

    @property
    def photo_view_url(self):
        if not self.photo:
            return ''
        return build_protected_media_url('warehouse-artwork-photo', self.pk, action='view')


class ArtworkMovement(models.Model):
    class MovementType(models.TextChoices):
        CHECK_OUT = 'saida', 'Saida / emprestimo'
        CHECK_IN = 'entrada', 'Entrada / devolucao'

    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, default=MovementType.CHECK_OUT)
    movement_date = models.DateField(default=timezone.localdate)
    taken_by = models.CharField(max_length=140)
    phone_number = models.CharField(max_length=24, blank=True)
    class_group = models.CharField(max_length=120, blank=True)
    cpp_responsible = models.CharField(max_length=120, blank=True)
    operator_name = models.CharField(max_length=120, blank=True)
    due_date = models.DateField(null=True, blank=True)
    returned_at = models.DateField(null=True, blank=True)
    notes = models.TextField(max_length=1200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_artwork_movements',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-movement_date', '-created_at']

    def clean(self):
        if self.movement_type == self.MovementType.CHECK_OUT and not self.due_date:
            raise ValidationError('Informe o prazo de devolucao para saidas de quadros.')

    @property
    def is_open(self):
        return self.movement_type == self.MovementType.CHECK_OUT and self.returned_at is None

    @property
    def is_overdue(self):
        return bool(self.is_open and self.due_date and self.due_date < timezone.localdate())

    def mark_returned(self):
        self.returned_at = timezone.localdate()
        self.movement_type = self.MovementType.CHECK_IN
        self.save(update_fields=['returned_at', 'movement_type', 'updated_at'])

    def __str__(self):
        return f'{self.get_movement_type_display()} - {self.artwork}'


class WarehouseActivity(models.Model):
    class ActivityType(models.TextChoices):
        CLASS = 'aula', 'Aula'
        EXHIBITION = 'exposicao', 'Exposicao'
        MEETING = 'reuniao', 'Reuniao'
        WORKSHOP = 'oficina', 'Oficina'
        EVALUATION = 'avaliacao', 'Avaliacao'

    class Status(models.TextChoices):
        SCHEDULED = 'agendado', 'Agendado'
        CONFIRMED = 'confirmado', 'Confirmado'
        DONE = 'concluido', 'Concluido'
        CANCELLED = 'cancelado', 'Cancelado'

    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='activities')
    activity_date = models.DateField()
    activity_time = models.TimeField(null=True, blank=True)
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices, default=ActivityType.EXHIBITION)
    responsible = models.CharField(max_length=140, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(max_length=1200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_warehouse_activities',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['activity_date', 'activity_time', 'artwork__name']

    def __str__(self):
        return f'{self.artwork} - {self.activity_date:%d/%m/%Y}'


class WarehouseFollowUp(models.Model):
    class Status(models.TextChoices):
        DONE = 'concluido', 'Concluido'
        OPEN = 'aberto', 'Acompanhamento aberto'
        IN_PROGRESS = 'andamento', 'Em acompanhamento'

    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='followups')
    followup_date = models.DateField(default=timezone.localdate)
    followup_time = models.TimeField(null=True, blank=True)
    responsible = models.CharField(max_length=140)
    reason = models.TextField(max_length=1200, blank=True)
    action_taken = models.TextField(max_length=1200, blank=True)
    support_material = models.CharField(max_length=180, blank=True)
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    destination = models.CharField(max_length=180, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_warehouse_followups',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-followup_date', '-created_at']

    def __str__(self):
        return f'{self.artwork} - {self.get_status_display()}'


class WarehouseStockItem(models.Model):
    class Unit(models.TextChoices):
        UNITS = 'unidades', 'Unidades'
        BOXES = 'caixas', 'Caixas'
        PAIRS = 'pares', 'Pares'
        BOTTLES = 'frascos', 'Frascos'
        ML = 'ml', 'ml'
        KG = 'kg', 'kg'

    material = models.CharField(max_length=160)
    item_class = models.CharField(max_length=120, blank=True)
    batch = models.CharField(max_length=80)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.UNITS)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    minimum_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    expiry_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=160, blank=True)
    notes = models.TextField(max_length=1200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_warehouse_stock_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['material', 'batch']
        constraints = [
            models.UniqueConstraint(fields=['material', 'batch'], name='unique_warehouse_stock_material_batch'),
        ]

    @property
    def needs_attention(self):
        return self.quantity <= self.minimum_quantity

    @property
    def expires_soon(self):
        return bool(self.expiry_date and self.expiry_date <= timezone.localdate() + timezone.timedelta(days=30))

    def __str__(self):
        return f'{self.material} - {self.batch}'
