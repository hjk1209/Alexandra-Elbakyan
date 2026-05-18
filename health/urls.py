from django.urls import path

from .views import (
    HealthAppointmentCreateView,
    HealthAppointmentUpdateView,
    HealthConsultationCreateView,
    HealthDashboardView,
    HealthHomeRedirectView,
    HealthRecordUpsertView,
    MyHealthView,
)

urlpatterns = [
    path('', HealthHomeRedirectView.as_view(), name='health-home'),
    path('minha-saude/', MyHealthView.as_view(), name='my-health'),
    path('painel/', HealthDashboardView.as_view(), name='health-dashboard'),
    path('fichas/salvar/', HealthRecordUpsertView.as_view(), name='health-record-upsert'),
    path('agendamentos/criar/', HealthAppointmentCreateView.as_view(), name='health-appointment-create'),
    path('agendamentos/<int:pk>/atualizar/', HealthAppointmentUpdateView.as_view(), name='health-appointment-update'),
    path('consultas/criar/', HealthConsultationCreateView.as_view(), name='health-consultation-create'),
]

