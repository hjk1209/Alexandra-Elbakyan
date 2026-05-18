from django.contrib import admin

from .models import HealthAppointment, HealthConsultation, HealthRecord, HealthUnit


@admin.register(HealthUnit)
class HealthUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'lead_operator', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'location', 'lead_operator__display_name', 'lead_operator__username')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'unit', 'blood_type', 'updated_by', 'updated_at')
    search_fields = ('patient__display_name', 'patient__username', 'unit__name')
    list_filter = ('unit',)


@admin.register(HealthAppointment)
class HealthAppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'unit', 'appointment_type', 'scheduled_for', 'status', 'assigned_operator')
    list_filter = ('unit', 'appointment_type', 'status')
    search_fields = ('patient__display_name', 'patient__username', 'unit__name', 'reason')


@admin.register(HealthConsultation)
class HealthConsultationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'unit', 'consultation_date', 'operator', 'follow_up_date')
    list_filter = ('unit', 'consultation_date')
    search_fields = ('patient__display_name', 'patient__username', 'unit__name', 'evaluation_notes')

