from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from core.models import SecurityEvent
from core.security import record_security_event

from .forms import (
    HealthAppointmentForm,
    HealthAppointmentUpdateForm,
    HealthConsultationForm,
    HealthRecordForm,
    active_patient_queryset,
)
from .models import HealthAppointment, HealthConsultation, HealthRecord, HealthUnit


def managed_health_units_for(user):
    units = HealthUnit.objects.filter(is_active=True)
    if not getattr(user, 'is_authenticated', False):
        return units.none()
    if user.is_superuser or user.can_administer or user.can_found:
        return units
    if getattr(user, 'is_health_operator', False):
        return units.filter(lead_operator=user)
    return units.none()


def can_manage_health_unit(user):
    return bool(getattr(user, 'can_operate_health', False))


def can_access_unit(user, unit):
    return managed_health_units_for(user).filter(pk=unit.pk).exists()


def redirect_for_health(user):
    return 'health-dashboard' if can_manage_health_unit(user) else 'my-health'


class HealthHomeRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect(redirect_for_health(request.user))


class MyHealthView(LoginRequiredMixin, TemplateView):
    template_name = 'health/my_health.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['health_records'] = HealthRecord.objects.filter(
            patient=self.request.user,
        ).select_related('unit', 'updated_by')
        context['appointments'] = HealthAppointment.objects.filter(
            patient=self.request.user,
        ).select_related('unit', 'assigned_operator')
        context['consultations'] = HealthConsultation.objects.filter(
            patient=self.request.user,
        ).select_related('unit', 'operator', 'appointment')
        return context


class HealthOperatorRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not can_manage_health_unit(request.user):
            messages.error(request, 'Essa area da unidade de saude e reservada para operadores autorizados.')
            return redirect('my-health')
        return super().dispatch(request, *args, **kwargs)


class HealthDashboardView(HealthOperatorRequiredMixin, TemplateView):
    template_name = 'health/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_units = managed_health_units_for(self.request.user).select_related('lead_operator')
        patient_queryset = active_patient_queryset()
        selected_patient = None
        selected_patient_id = self.request.GET.get('patient')
        if selected_patient_id:
            selected_patient = patient_queryset.filter(pk=selected_patient_id).first()
        default_unit = managed_units.first()

        context['managed_units'] = managed_units
        context['unit_total'] = managed_units.count()
        context['patient_total'] = patient_queryset.count()
        context['selected_patient'] = selected_patient
        context['selected_patient_records'] = HealthRecord.objects.none()
        context['selected_patient_appointments'] = HealthAppointment.objects.none()
        context['selected_patient_consultations'] = HealthConsultation.objects.none()
        if selected_patient:
            context['selected_patient_records'] = HealthRecord.objects.filter(
                patient=selected_patient,
                unit__in=managed_units,
            ).select_related('unit', 'updated_by')
            context['selected_patient_appointments'] = HealthAppointment.objects.filter(
                patient=selected_patient,
                unit__in=managed_units,
            ).select_related('unit', 'assigned_operator')
            context['selected_patient_consultations'] = HealthConsultation.objects.filter(
                patient=selected_patient,
                unit__in=managed_units,
            ).select_related('unit', 'operator', 'appointment')

        context['record_form'] = kwargs.get('record_form') or HealthRecordForm(
            allowed_units=managed_units,
            initial={'patient': selected_patient, 'unit': default_unit},
        )
        context['appointment_form'] = kwargs.get('appointment_form') or HealthAppointmentForm(
            allowed_units=managed_units,
            initial={'patient': selected_patient, 'unit': default_unit, 'assigned_operator': self.request.user},
        )
        context['consultation_form'] = kwargs.get('consultation_form') or HealthConsultationForm(
            allowed_units=managed_units,
            initial={'patient': selected_patient, 'unit': default_unit},
        )
        context['recent_records'] = HealthRecord.objects.filter(
            unit__in=managed_units,
        ).select_related('patient', 'unit', 'updated_by')[:12]
        context['upcoming_appointments'] = HealthAppointment.objects.filter(
            unit__in=managed_units,
        ).select_related('patient', 'unit', 'assigned_operator')[:12]
        context['recent_consultations'] = HealthConsultation.objects.filter(
            unit__in=managed_units,
        ).select_related('patient', 'unit', 'operator')[:12]
        appointment_source = context['selected_patient_appointments'] if selected_patient else context['upcoming_appointments']
        consultation_source = context['selected_patient_consultations'] if selected_patient else context['recent_consultations']
        context['appointment_cards'] = [
            {
                'instance': appointment,
                'update_form': HealthAppointmentUpdateForm(instance=appointment),
            }
            for appointment in appointment_source
        ]
        context['consultation_rows'] = consultation_source
        context['open_appointment_total'] = HealthAppointment.objects.filter(
            unit__in=managed_units,
        ).exclude(
            status__in=[HealthAppointment.Status.COMPLETED, HealthAppointment.Status.CANCELLED]
        ).count()
        context['recent_patient_total'] = HealthRecord.objects.filter(
            unit__in=managed_units,
        ).values('patient_id').distinct().count()
        context['patient_cards'] = patient_queryset.annotate(
            health_record_total=Count('health_records', distinct=True),
            appointment_total=Count('health_appointments', distinct=True),
        )[:18]
        return context


class HealthRecordUpsertView(HealthOperatorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        managed_units = managed_health_units_for(request.user)
        form = HealthRecordForm(request.POST, allowed_units=managed_units)
        patient_id = request.POST.get('patient')
        if form.is_valid():
            unit = form.cleaned_data['unit']
            if not can_access_unit(request.user, unit):
                messages.error(request, 'Essa unidade de saude nao esta liberada para seu operador.')
                return redirect('health-dashboard')
            patient = form.cleaned_data['patient']
            record, created = HealthRecord.objects.update_or_create(
                patient=patient,
                unit=unit,
                defaults={
                    'blood_type': form.cleaned_data['blood_type'],
                    'allergies': form.cleaned_data['allergies'],
                    'chronic_conditions': form.cleaned_data['chronic_conditions'],
                    'medications_in_use': form.cleaned_data['medications_in_use'],
                    'emergency_contact_name': form.cleaned_data['emergency_contact_name'],
                    'emergency_contact_phone': form.cleaned_data['emergency_contact_phone'],
                    'care_notes': form.cleaned_data['care_notes'],
                    'updated_by': request.user,
                },
            )
            record_security_event(
                request,
                SecurityEvent.EventType.HEALTH_RECORD_UPDATED,
                severity=SecurityEvent.Severity.INFO,
                user=patient,
                details={'unit': unit.name, 'operator': request.user.username, 'created': created},
            )
            messages.success(
                request,
                f'Ficha de saude de {patient.display_name} {"criada" if created else "atualizada"} com sucesso.',
            )
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        if patient_id:
            return redirect(f'{reverse("health-dashboard")}?patient={patient_id}')
        return redirect('health-dashboard')


class HealthAppointmentCreateView(HealthOperatorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        managed_units = managed_health_units_for(request.user)
        form = HealthAppointmentForm(request.POST, allowed_units=managed_units)
        patient_id = request.POST.get('patient')
        if form.is_valid():
            appointment = form.save(commit=False)
            if not can_access_unit(request.user, appointment.unit):
                messages.error(request, 'Esse agendamento nao pertence a uma unidade liberada para voce.')
                return redirect('health-dashboard')
            if not (request.user.can_administer or request.user.can_found or request.user.is_superuser):
                appointment.assigned_operator = request.user
            appointment.created_by = request.user
            appointment.save()
            record_security_event(
                request,
                SecurityEvent.EventType.HEALTH_APPOINTMENT_SCHEDULED,
                severity=SecurityEvent.Severity.INFO,
                user=appointment.patient,
                details={
                    'unit': appointment.unit.name,
                    'operator': request.user.username,
                    'scheduled_for': appointment.scheduled_for.isoformat(),
                },
            )
            messages.success(request, f'Agendamento criado para {appointment.patient.display_name}.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        if patient_id:
            return redirect(f'{reverse("health-dashboard")}?patient={patient_id}')
        return redirect('health-dashboard')


class HealthAppointmentUpdateView(HealthOperatorRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        appointment = get_object_or_404(HealthAppointment.objects.select_related('unit', 'patient'), pk=pk)
        if not can_access_unit(request.user, appointment.unit):
            messages.error(request, 'Esse agendamento nao pode ser alterado por este operador.')
            return redirect('health-dashboard')
        form = HealthAppointmentUpdateForm(request.POST, instance=appointment)
        if form.is_valid():
            updated_appointment = form.save(commit=False)
            if not (request.user.can_administer or request.user.can_found or request.user.is_superuser):
                updated_appointment.assigned_operator = request.user
            updated_appointment.save()
            record_security_event(
                request,
                SecurityEvent.EventType.HEALTH_APPOINTMENT_UPDATED,
                severity=SecurityEvent.Severity.INFO,
                user=updated_appointment.patient,
                details={
                    'unit': updated_appointment.unit.name,
                    'operator': request.user.username,
                    'status': updated_appointment.status,
                },
            )
            messages.success(request, f'Agendamento de {updated_appointment.patient.display_name} atualizado.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect(f'{reverse("health-dashboard")}?patient={appointment.patient_id}')


class HealthConsultationCreateView(HealthOperatorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        managed_units = managed_health_units_for(request.user)
        form = HealthConsultationForm(request.POST, allowed_units=managed_units)
        patient_id = request.POST.get('patient')
        if form.is_valid():
            consultation = form.save(commit=False)
            if not can_access_unit(request.user, consultation.unit):
                messages.error(request, 'Essa consulta nao pertence a uma unidade liberada para voce.')
                return redirect('health-dashboard')
            consultation.operator = request.user
            consultation.save()
            if consultation.appointment:
                consultation.appointment.status = HealthAppointment.Status.COMPLETED
                if not consultation.appointment.assigned_operator_id:
                    consultation.appointment.assigned_operator = request.user
                consultation.appointment.save(update_fields=['status', 'assigned_operator'])
            record_security_event(
                request,
                SecurityEvent.EventType.HEALTH_CONSULTATION_RECORDED,
                severity=SecurityEvent.Severity.INFO,
                user=consultation.patient,
                details={
                    'unit': consultation.unit.name,
                    'operator': request.user.username,
                    'consultation_date': consultation.consultation_date.isoformat(),
                },
            )
            messages.success(request, f'Consulta registrada para {consultation.patient.display_name}.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        if patient_id:
            return redirect(f'{reverse("health-dashboard")}?patient={patient_id}')
        return redirect('health-dashboard')
