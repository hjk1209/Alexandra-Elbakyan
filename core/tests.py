from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from accounts.models import PasswordRequest, User


class HomeTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Raiz Coletiva')
        self.assertContains(response, 'js/app.js')
        self.assertContains(response, 'Som: ligado')
        self.assertContains(response, 'Popup web')


class SecurityCenterTests(TestCase):
    password = 'SenhaSegura!2026'

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            display_name='Administrador da Rede',
            handle='admin_rede',
            email='admin@example.com',
            role=User.Role.ADMIN,
            password=self.password,
        )
        self.founder_user = User.objects.create_user(
            username='fundador',
            display_name='Fundador',
            handle='fundador',
            email='fundador@example.com',
            role=User.Role.FOUNDER,
            password=self.password,
        )
        self.member_user = User.objects.create_user(
            username='militante',
            display_name='Militante',
            handle='militante',
            email='militante@example.com',
            role=User.Role.MEMBER,
            password=self.password,
        )

    def _session_login(self, user, password=None):
        return self.client.post(
            reverse('login'),
            {'username': user.username, 'password': password or self.password},
        )

    def test_admin_user_can_create_member_user(self):
        self._session_login(self.admin_user)
        response = self.client.post(
            reverse('security-center'),
            {
                'username': 'novo.usuario',
                'display_name': 'Novo Usuario',
                'handle': 'novo_usuario',
                'email': 'novo@example.com',
                'birth_date': '',
                'phone_number': '',
                'role': User.Role.COLLECTIVE,
                'bio': 'Perfil criado pela administracao',
                'location': 'Sao Paulo',
                'password1': self.password,
                'password2': self.password,
            },
        )
        self.assertRedirects(response, reverse('security-center'))
        self.assertTrue(User.objects.filter(username='novo.usuario', role=User.Role.COLLECTIVE).exists())

    def test_admin_user_cannot_create_founder(self):
        self._session_login(self.admin_user)
        response = self.client.post(
            reverse('security-center'),
            {
                'username': 'invasor.role',
                'display_name': 'Escalada Indevida',
                'handle': 'escalada_indevida',
                'email': 'escalada@example.com',
                'birth_date': '',
                'phone_number': '',
                'role': User.Role.FOUNDER,
                'bio': 'Nao deveria passar',
                'location': 'Recife',
                'password1': self.password,
                'password2': self.password,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='invasor.role').exists())

    def test_admin_user_can_toggle_member_access(self):
        self._session_login(self.admin_user)
        response = self.client.post(
            reverse('security-user-toggle', args=[self.member_user.pk]),
            {'reason': 'Quebra das regras de convivencia da plataforma.'},
        )
        self.assertRedirects(response, reverse('security-center'))
        self.member_user.refresh_from_db()
        self.assertFalse(self.member_user.is_active)

        response = self.client.post(
            reverse('security-user-toggle', args=[self.member_user.pk]),
            {'reason': 'Usuario orientado e acesso liberado novamente.'},
        )
        self.assertRedirects(response, reverse('security-center'))
        self.member_user.refresh_from_db()
        self.assertTrue(self.member_user.is_active)

    def test_admin_user_cannot_toggle_founder(self):
        self._session_login(self.admin_user)
        response = self.client.post(
            reverse('security-user-toggle', args=[self.founder_user.pk]),
            {'reason': 'Tentativa indevida de suspensao.'},
        )
        self.assertRedirects(response, reverse('security-center'))
        self.founder_user.refresh_from_db()
        self.assertTrue(self.founder_user.is_active)

    def test_admin_user_must_explain_access_toggle(self):
        self._session_login(self.admin_user)
        response = self.client.post(reverse('security-user-toggle', args=[self.member_user.pk]))
        self.assertRedirects(response, reverse('security-center'))
        self.member_user.refresh_from_db()
        self.assertTrue(self.member_user.is_active)

    def test_founder_can_edit_managed_user_and_change_role(self):
        self._session_login(self.founder_user)
        response = self.client.post(
            reverse('security-user-edit', args=[self.member_user.pk]),
            {
                f'user-{self.member_user.pk}-display_name': 'Militante Editado',
                f'user-{self.member_user.pk}-handle': 'militante_editado',
                f'user-{self.member_user.pk}-email': 'militante.editado@example.com',
                f'user-{self.member_user.pk}-birth_date': '',
                f'user-{self.member_user.pk}-phone_number': '',
                f'user-{self.member_user.pk}-role': User.Role.MODERATOR,
                f'user-{self.member_user.pk}-bio': 'Perfil ajustado pela gestao.',
                f'user-{self.member_user.pk}-location': 'Brasilia',
                f'user-{self.member_user.pk}-is_profile_private': '',
                f'user-{self.member_user.pk}-background_theme': User.BackgroundTheme.CEU,
                f'user-{self.member_user.pk}-two_factor_enabled': '',
                f'user-{self.member_user.pk}-two_factor_channel': User.TwoFactorChannel.CONSOLE,
            },
        )
        self.assertRedirects(response, reverse('security-center'))
        self.member_user.refresh_from_db()
        self.assertEqual(self.member_user.display_name, 'Militante Editado')
        self.assertEqual(self.member_user.role, User.Role.MODERATOR)
        self.assertEqual(self.member_user.background_theme, User.BackgroundTheme.CEU)

    def test_regular_user_cannot_manage_users(self):
        self._session_login(self.member_user)
        response = self.client.post(
            reverse('security-center'),
            {
                'username': 'invasor',
                'display_name': 'Invasor',
                'handle': 'invasor',
                'email': 'invasor@example.com',
                'birth_date': '',
                'phone_number': '',
                'role': User.Role.ADMIN,
                'bio': 'Nao deveria passar',
                'location': 'Recife',
                'password1': self.password,
                'password2': self.password,
            },
        )
        self.assertRedirects(response, reverse('security-center'))
        self.assertFalse(User.objects.filter(username='invasor').exists())

    def test_admin_user_can_approve_password_request(self):
        target_user = User.objects.create_user(
            username='pedido',
            display_name='Pedido',
            handle='pedido',
            email='pedido@example.com',
            password='SenhaAntiga!2026',
        )
        password_request = PasswordRequest.objects.create(
            target_user=target_user,
            requested_username=target_user.username,
            requested_email=target_user.email,
            suggested_password_hash=make_password('NovaSenhaSegura!2026'),
        )
        self._session_login(self.admin_user)
        response = self.client.post(
            reverse('security-password-request-action', args=[password_request.pk, 'aprovar'])
        )
        self.assertRedirects(response, reverse('security-center'))
        password_request.refresh_from_db()
        self.assertEqual(password_request.status, PasswordRequest.Status.APPROVED)
        self.client.logout()
        login_response = self.client.post(
            reverse('login'),
            {'username': target_user.username, 'password': 'NovaSenhaSegura!2026'},
        )
        self.assertRedirects(login_response, reverse('feed'))
