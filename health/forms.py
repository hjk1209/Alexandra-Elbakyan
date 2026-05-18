from django import forms
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from core.security import clean_plain_text

from .models import HealthAppointment, HealthConsultation, HealthRecord, HealthUnit


DATETIME_LOCAL_FORMAT = '%Y-%m-%dT%H:%M'


def active_patient_queryset():
    return User.objects.filter(is_active=True).exclude(role=User.Role.COLLECTIVE).order_by('display_name', 'username')


def health_operator_queryset():
    return User.objects.filter(
        is_active=True,
    ).filter(
        Q(is_health_operator=True)
        | Q(role__in=[User.Role.ADMIN, User.Role.FOUNDER])
        | Q(is_superuser=True)
    ).order_by('display_name', 'username')


class HealthRecordForm(forms.ModelForm):
    class Meta:
        model = HealthRecord
        fields = (
            'patient',
            'unit',
            'blood_type',
            'allergies',
            'chronic_conditions',
            'medications_in_use',
            'emergency_contact_name',
            'emergency_contact_phone',
            'care_notes',
        )

    def __init__(self, *args, allowed_units=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = active_patient_queryset()
        self.fields['patient'].label = 'Pessoa atendida'
        self.fields['unit'].queryset = allowed_units if allowed_units is not None else HealthUnit.objects.filter(is_active=True)
        self.fields['unit'].label = 'Unidade de saude'
        self.fields['blood_type'].label = 'Tipo sanguineo'
        self.fields['allergies'].label = 'Alergias'
        self.fields['chronic_conditions'].label = 'Condicoes cronicas'
        self.fields['medications_in_use'].label = 'Medicacoes em uso'
        self.fields['emergency_contact_name'].label = 'Contato de emergencia'
        self.fields['emergency_contact_phone'].label = 'Telefone de emergencia'
        self.fields['care_notes'].label = 'Observacoes gerais'

    def clean_blood_type(self):
        return clean_plain_text(self.cleaned_data.get('blood_type', ''))

    def clean_allergies(self):
        return clean_plain_text(self.cleaned_data.get('allergies', ''))

    def clean_chronic_conditions(self):
        return clean_plain_text(self.cleaned_data.get('chronic_conditions', ''))

    def clean_medications_in_use(self):
        return clean_plain_text(self.cleaned_data.get('medications_in_use', ''))

    def clean_emergency_contact_name(self):
        return clean_plain_text(self.cleaned_data.get('emergency_contact_name', ''))

    def clean_emergency_contact_phone(self):
        return clean_plain_text(self.cleaned_data.get('emergency_contact_phone', ''))

    def clean_care_notes(self):
        return clean_plain_text(self.cleaned_data.get('care_notes', ''))


class HealthAppointmentForm(forms.ModelForm):
    class Meta:
        model = HealthAppointment
        fields = (
            'patient',
            'unit',
            'assigned_operator',
            'appointment_type',
            'scheduled_for',
            'status',
            'reason',
            'notes',
        )
        widgets = {
            'scheduled_for': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format=DATETIME_LOCAL_FORMAT,
            ),
        }

    def __init__(self, *args, allowed_units=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = active_patient_queryset()
        self.fields['patient'].label = 'Pessoa atendida'
        self.fields['unit'].queryset = allowed_units if allowed_units is not None else HealthUnit.objects.filter(is_active=True)
        self.fields['unit'].label = 'Unidade de saude'
        self.fields['assigned_operator'].queryset = health_operator_queryset()
        self.fields['assigned_operator'].label = 'Operador responsavel'
        self.fields['appointment_type'].label = 'Tipo de atendimento'
        self.fields['scheduled_for'].label = 'Data e horario'
        self.fields['scheduled_for'].input_formats = [DATETIME_LOCAL_FORMAT]
        self.fields['status'].label = 'Status'
        self.fields['reason'].label = 'Motivo do atendimento'
        self.fields['notes'].label = 'Observacoes'
        if self.instance.pk and self.instance.scheduled_for:
            self.initial['scheduled_for'] = timezone.localtime(self.instance.scheduled_for).strftime(DATETIME_LOCAL_FORMAT)

    def clean_reason(self):
        return clean_plain_text(self.cleaned_data['reason'])

    def clean_notes(self):
        return clean_plain_text(self.cleaned_data.get('notes', ''))


class HealthAppointmentUpdateForm(forms.ModelForm):
    class Meta:
        model = HealthAppointment
        fields = ('scheduled_for', 'status', 'assigned_operator', 'notes')
        widgets = {
            'scheduled_for': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format=DATETIME_LOCAL_FORMAT,
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scheduled_for'].label = 'Data e horario'
        self.fields['scheduled_for'].input_formats = [DATETIME_LOCAL_FORMAT]
        self.fields['status'].label = 'Status'
        self.fields['assigned_operator'].label = 'Operador responsavel'
        self.fields['assigned_operator'].queryset = health_operator_queryset()
        self.fields['notes'].label = 'Observacoes'
        if self.instance.pk and self.instance.scheduled_for:
            self.initial['scheduled_for'] = timezone.localtime(self.instance.scheduled_for).strftime(DATETIME_LOCAL_FORMAT)

    def clean_notes(self):
        return clean_plain_text(self.cleaned_data.get('notes', ''))


class HealthConsultationForm(forms.ModelForm):
    class Meta:
        model = HealthConsultation
        fields = (
            'appointment',
            'patient',
            'unit',
            'consultation_date',
            'symptoms',
            'evaluation_notes',
            'procedures',
            'guidance',
            'referral_notes',
            'follow_up_date',
        )
        widgets = {
            'consultation_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format=DATETIME_LOCAL_FORMAT,
            ),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, allowed_units=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['appointment'].queryset = HealthAppointment.objects.select_related('patient', 'unit').order_by('-scheduled_for')
        self.fields['appointment'].required = False
        self.fields['appointment'].label = 'Agendamento relacionado'
        self.fields['patient'].queryset = active_patient_queryset()
        self.fields['patient'].label = 'Pessoa atendida'
        self.fields['unit'].queryset = allowed_units if allowed_units is not None else HealthUnit.objects.filter(is_active=True)
        self.fields['unit'].label = 'Unidade de saude'
        self.fields['consultation_date'].label = 'Data e horario da consulta'
        self.fields['consultation_date'].input_formats = [DATETIME_LOCAL_FORMAT]
        self.fields['symptoms'].label = 'Sintomas'
        self.fields['evaluation_notes'].label = 'Avaliacao e registro clinico'
        self.fields['procedures'].label = 'Procedimentos'
        self.fields['guidance'].label = 'Orientacoes'
        self.fields['referral_notes'].label = 'Encaminhamentos'
        self.fields['follow_up_date'].label = 'Retorno sugerido'
        if allowed_units is not None:
            self.fields['appointment'].queryset = self.fields['appointment'].queryset.filter(unit__in=allowed_units)
        if self.instance.pk and self.instance.consultation_date:
            self.initial['consultation_date'] = timezone.localtime(self.instance.consultation_date).strftime(DATETIME_LOCAL_FORMAT)
        elif not self.is_bound:
            self.initial['consultation_date'] = timezone.localtime().strftime(DATETIME_LOCAL_FORMAT)

    def clean_symptoms(self):
        return clean_plain_text(self.cleaned_data.get('symptoms', ''))

    def clean_evaluation_notes(self):
        return clean_plain_text(self.cleaned_data['evaluation_notes'])

    def clean_procedures(self):
        return clean_plain_text(self.cleaned_data.get('procedures', ''))

    def clean_guidance(self):
        return clean_plain_text(self.cleaned_data.get('guidance', ''))

    def clean_referral_notes(self):
        return clean_plain_text(self.cleaned_data.get('referral_notes', ''))

