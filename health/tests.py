from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import HealthAppointment, HealthConsultation, HealthRecord, HealthUnit


class HealthFlowTests(TestCase):
    password = 'SenhaSegura!2026'

    def setUp(self):
        self.operator = User.objects.create_user(
            username='saude.operadora',
            display_name='Operadora de Saude',
            handle='saude_operadora',
            email='saude@example.com',
            password=self.password,
            is_health_operator=True,
        )
        self.patient = User.objects.create_user(
            username='paciente',
            display_name='Paciente Popular',
            handle='paciente_popular',
            email='paciente@example.com',
            password=self.password,
        )
        self.unit = HealthUnit.objects.create(
            name='Unidade Popular de Saude',
            location='Nucleo central',
            lead_operator=self.operator,
            description='Acolhimento, consultas e agendamentos da base.',
        )

    def _force_login(self, user):
        self.client.force_login(user)

    def test_health_operator_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {'username': self.operator.username, 'password': self.password},
        )
        self.assertRedirects(response, reverse('health-dashboard'))

    def test_regular_user_is_redirected_to_my_health(self):
        self._force_login(self.patient)
        response = self.client.get(reverse('health-home'))
        self.assertRedirects(response, reverse('my-health'))

    def test_operator_can_create_record_appointment_and_consultation(self):
        self._force_login(self.operator)
        response = self.client.post(
            reverse('health-record-upsert'),
            {
                'patient': self.patient.pk,
                'unit': self.unit.pk,
                'blood_type': 'O+',
                'allergies': 'Poeira',
                'chronic_conditions': 'Nenhuma',
                'medications_in_use': '',
                'emergency_contact_name': 'Mae da base',
                'emergency_contact_phone': '+55 81 99999-1111',
                'care_notes': 'Acompanhar hidratacao.',
            },
        )
        self.assertRedirects(response, f'{reverse("health-dashboard")}?patient={self.patient.pk}')
        self.assertTrue(HealthRecord.objects.filter(patient=self.patient, unit=self.unit, blood_type='O+').exists())

        response = self.client.post(
            reverse('health-appointment-create'),
            {
                'patient': self.patient.pk,
                'unit': self.unit.pk,
                'assigned_operator': self.operator.pk,
                'appointment_type': HealthAppointment.AppointmentType.CONSULTATION,
                'scheduled_for': '2026-05-20T14:00',
                'status': HealthAppointment.Status.SCHEDULED,
                'reason': 'Consulta de rotina',
                'notes': 'Levar exames anteriores.',
            },
        )
        self.assertRedirects(response, f'{reverse("health-dashboard")}?patient={self.patient.pk}')
        appointment = HealthAppointment.objects.get(patient=self.patient, unit=self.unit)

        response = self.client.post(
            reverse('health-consultation-create'),
            {
                'appointment': appointment.pk,
                'patient': self.patient.pk,
                'unit': self.unit.pk,
                'consultation_date': '2026-05-20T14:15',
                'symptoms': 'Dor de cabeca leve',
                'evaluation_notes': 'Quadro estavel e sem sinais de gravidade.',
                'procedures': 'Afericao de pressao',
                'guidance': 'Repouso e hidratacao',
                'referral_notes': '',
                'follow_up_date': '2026-05-27',
            },
        )
        self.assertRedirects(response, f'{reverse("health-dashboard")}?patient={self.patient.pk}')
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, HealthAppointment.Status.COMPLETED)
        self.assertTrue(HealthConsultation.objects.filter(patient=self.patient, unit=self.unit).exists())

    def test_user_only_sees_own_health_data(self):
        other_user = User.objects.create_user(
            username='outra.pessoa',
            display_name='Outra Pessoa',
            handle='outra_pessoa',
            email='outra@example.com',
            password=self.password,
        )
        HealthRecord.objects.create(
            patient=self.patient,
            unit=self.unit,
            blood_type='A+',
            allergies='Nenhuma',
            updated_by=self.operator,
        )
        HealthRecord.objects.create(
            patient=other_user,
            unit=self.unit,
            blood_type='B+',
            allergies='Po',
            updated_by=self.operator,
        )
        self._force_login(self.patient)
        response = self.client.get(reverse('my-health'))
        self.assertContains(response, 'A+')
        self.assertNotContains(response, 'B+')

    def test_admin_can_access_health_dashboard(self):
        admin = User.objects.create_user(
            username='adm.saude',
            display_name='Admin Saude',
            handle='adm_saude',
            email='adm.saude@example.com',
            role=User.Role.ADMIN,
            password=self.password,
        )
        self._force_login(admin)
        response = self.client.get(reverse('health-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Painel da unidade de saude')

