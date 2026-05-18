from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class HealthUnit(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    location = models.CharField(max_length=140, blank=True)
    phone_number = models.CharField(max_length=24, blank=True)
    description = models.TextField(max_length=1200, blank=True)
    lead_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='led_health_units',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'unidade-saude'
            candidate = base_slug[:140]
            suffix = 1
            while type(self).objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f'{base_slug[:132]}-{suffix}'[:140]
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class HealthRecord(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='health_records',
    )
    unit = models.ForeignKey(
        HealthUnit,
        on_delete=models.CASCADE,
        related_name='health_records',
    )
    blood_type = models.CharField(max_length=8, blank=True)
    allergies = models.TextField(max_length=1200, blank=True)
    chronic_conditions = models.TextField(max_length=1200, blank=True)
    medications_in_use = models.TextField(max_length=1200, blank=True)
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_phone = models.CharField(max_length=24, blank=True)
    care_notes = models.TextField(max_length=1600, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_health_records',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['patient__display_name', 'unit__name']
        constraints = [
            models.UniqueConstraint(fields=['patient', 'unit'], name='unique_health_record_per_unit'),
        ]

    def clean(self):
        if getattr(self.patient, 'role', '') == 'collective':
            raise ValidationError('A ficha de saude deve ser vinculada a uma pessoa, nao a um coletivo.')

    def __str__(self):
        return f'Ficha de {self.patient} - {self.unit}'


class HealthAppointment(models.Model):
    class AppointmentType(models.TextChoices):
        CONSULTATION = 'consultation', 'Consulta'
        EXAM = 'exam', 'Exame'
        VACCINE = 'vaccine', 'Vacina'
        FOLLOW_UP = 'follow_up', 'Retorno'
        GUIDANCE = 'guidance', 'Orientacao'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Agendada'
        CONFIRMED = 'confirmed', 'Confirmada'
        COMPLETED = 'completed', 'Concluida'
        CANCELLED = 'cancelled', 'Cancelada'
        MISSED = 'missed', 'Nao compareceu'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='health_appointments',
    )
    unit = models.ForeignKey(
        HealthUnit,
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    assigned_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_health_appointments',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_health_appointments',
    )
    appointment_type = models.CharField(
        max_length=20,
        choices=AppointmentType.choices,
        default=AppointmentType.CONSULTATION,
    )
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    reason = models.CharField(max_length=240)
    notes = models.TextField(max_length=1200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_for', 'patient__display_name']

    def clean(self):
        if getattr(self.patient, 'role', '') == 'collective':
            raise ValidationError('Agendamentos devem ser feitos para pessoas cadastradas.')

    def __str__(self):
        return f'{self.patient} - {self.get_appointment_type_display()}'


class HealthConsultation(models.Model):
    appointment = models.OneToOneField(
        HealthAppointment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='consultation',
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='health_consultations',
    )
    unit = models.ForeignKey(
        HealthUnit,
        on_delete=models.CASCADE,
        related_name='consultations',
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='performed_health_consultations',
    )
    consultation_date = models.DateTimeField(default=timezone.now)
    symptoms = models.TextField(max_length=1200, blank=True)
    evaluation_notes = models.TextField(max_length=1600)
    procedures = models.TextField(max_length=1200, blank=True)
    guidance = models.TextField(max_length=1200, blank=True)
    referral_notes = models.TextField(max_length=1200, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-consultation_date', '-created_at']

    def clean(self):
        if getattr(self.patient, 'role', '') == 'collective':
            raise ValidationError('Consultas devem ser vinculadas a pessoas cadastradas.')
        if self.appointment:
            if self.appointment.patient_id != self.patient_id:
                raise ValidationError('A consulta precisa usar o mesmo paciente do agendamento selecionado.')
            if self.appointment.unit_id != self.unit_id:
                raise ValidationError('A consulta precisa usar a mesma unidade do agendamento selecionado.')

    def __str__(self):
        return f'Consulta de {self.patient} em {self.consultation_date:%d/%m/%Y}'

