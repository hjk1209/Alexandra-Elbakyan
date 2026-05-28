import json

from django.contrib.auth.hashers import identify_hasher
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from social.models import Follow, WeeklyTask

from .models import PasswordRequest, User
from .tokens import verify_token


class AuthFlowTests(TestCase):
    password = 'SenhaSegura!2026'

    def _force_login(self, user):
        self.client.force_login(user)

    def _session_login(self, user, password=None):
        return self.client.post(
            reverse('login'),
            {'username': user.username, 'password': password or self.password},
        )

    def test_signup_creates_user_and_redirects(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'ana',
                'display_name': 'Ana da Base',
                'handle': 'ana_base',
                'email': 'ana@example.com',
                'birth_date': '2000-01-20',
                'phone_number': '+55 81 99999-9999',
                'role': User.Role.MEMBER,
                'bio': 'Juventude em movimento',
                'location': 'Goiania',
                'password1': self.password,
                'password2': self.password,
            },
        )
        self.assertRedirects(response, reverse('feed'))
        user = User.objects.get(username='ana')
        self.assertIn('_auth_user_id', self.client.session)

    def test_password_is_never_saved_as_plain_text(self):
        user = User.objects.create_user(
            username='hash',
            display_name='Hash Seguro',
            handle='hash_seguro',
            email='hash@example.com',
            password=self.password,
        )
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))
        self.assertIn(identify_hasher(user.password).algorithm, {'argon2', 'bcrypt_sha256', 'pbkdf2_sha256'})

    def test_signup_accepts_profile_photo_file(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'bia',
                'display_name': 'Bia da Rede',
                'handle': 'bia_rede',
                'email': 'bia@example.com',
                'birth_date': '2001-02-10',
                'phone_number': '',
                'role': User.Role.MEMBER,
                'bio': 'Base em movimento',
                'location': 'Sao Paulo',
                'password1': self.password,
                'password2': self.password,
                'avatar': SimpleUploadedFile('avatar.jpg', b'fake-image-content', content_type='image/jpeg'),
            },
        )
        self.assertRedirects(response, reverse('feed'))
        self.assertTrue(User.objects.filter(username='bia').exclude(avatar='').exists())

    def test_privileged_roles_cannot_be_self_registered(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'gestor',
                'display_name': 'Gestor da Rede',
                'handle': 'gestor_rede',
                'email': 'gestor@example.com',
                'birth_date': '1990-03-01',
                'phone_number': '',
                'role': User.Role.ADMIN,
                'bio': 'Equipe de acesso',
                'location': 'Brasilia',
                'password1': self.password,
                'password2': self.password,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='gestor').exists())
        self.assertIn('role', response.context['form'].errors)

    def test_signup_shows_clear_required_messages_for_name_and_profile_name(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'ana',
                'display_name': '',
                'handle': '',
                'email': 'ana@example.com',
                'birth_date': '',
                'phone_number': '',
                'role': User.Role.MEMBER,
                'bio': '',
                'location': '',
                'password1': self.password,
                'password2': self.password,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Informe seu nome.')
        self.assertContains(response, 'Informe o nome do perfil.')

    def test_login_lockout_after_repeated_failures(self):
        user = User.objects.create_user(
            username='ana',
            display_name='Ana',
            handle='ana',
            email='ana@example.com',
            password=self.password,
        )
        url = reverse('login')
        for _ in range(5):
            self.client.post(url, {'username': user.username, 'password': 'errada'})
        response = self.client.post(url, {'username': user.username, 'password': 'errada'})
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'data-notification-level="error"', status_code=429)

    def test_login_uses_username_identifier(self):
        User.objects.create_user(
            username='ana.user',
            display_name='Ana User',
            handle='ana_user',
            email='ana.user@example.com',
            password=self.password,
        )
        response = self.client.post(
            reverse('login'),
            {'username': 'ana.user', 'password': self.password},
        )
        self.assertRedirects(response, reverse('feed'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_rejects_numeric_id_identifier(self):
        user = User.objects.create_user(
            username='numerico',
            display_name='Numerico',
            handle='numerico',
            email='numerico@example.com',
            password=self.password,
        )
        response = self.client.post(
            reverse('login'),
            {'username': str(user.login_id), 'password': self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nome de usuario ou senha invalidos.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_admin_login_redirects_to_security_center(self):
        user = User.objects.create_user(
            username='admin',
            display_name='Administrador',
            handle='admin',
            email='admin@example.com',
            role=User.Role.ADMIN,
            password=self.password,
        )
        response = self._session_login(user)
        self.assertRedirects(response, reverse('security-center'))

    def test_profile_connections_page_lists_followers(self):
        author = User.objects.create_user(
            username='autor',
            display_name='Autor',
            handle='autor',
            email='autor@example.com',
            password=self.password,
        )
        follower = User.objects.create_user(
            username='seguidor',
            display_name='Seguidor',
            handle='seguidor',
            email='seguidor@example.com',
            password=self.password,
        )
        Follow.objects.create(follower=follower, following=author)
        self._force_login(author)
        response = self.client.get(reverse('profile-connections', args=[author.handle, 'seguidores']))
        self.assertContains(response, 'Seguidor')

    def test_profile_shows_weekly_tasks_for_user(self):
        author = User.objects.create_user(
            username='autor2',
            display_name='Autor 2',
            handle='autor_2',
            email='autor2@example.com',
            password=self.password,
        )
        WeeklyTask.objects.create(
            assignee=author,
            title='Organizar tarefa da semana',
            description='Fechar agenda ate sexta.',
            due_date=timezone.localdate(),
            created_by=author,
        )
        self._force_login(author)
        response = self.client.get(reverse('profile', args=[author.handle]))
        self.assertContains(response, 'Tarefas da semana')
        self.assertContains(response, 'Organizar tarefa da semana')

    def test_profile_edit_updates_background_theme(self):
        user = User.objects.create_user(
            username='tema',
            display_name='Tema',
            handle='tema',
            email='tema@example.com',
            password=self.password,
        )
        self._force_login(user)
        response = self.client.post(
            reverse('profile-edit'),
            {
                'display_name': user.display_name,
                'birth_date': '',
                'phone_number': '',
                'bio': 'Perfil com tema proprio.',
                'location': 'Fortaleza',
                'avatar': '',
                'is_profile_private': '',
                'background_theme': User.BackgroundTheme.MATA,
                'two_factor_enabled': '',
                'two_factor_channel': User.TwoFactorChannel.CONSOLE,
            },
        )
        self.assertRedirects(response, reverse('profile', args=[user.handle]))
        user.refresh_from_db()
        self.assertEqual(user.background_theme, User.BackgroundTheme.MATA)
        response = self.client.get(reverse('feed'))
        self.assertContains(response, 'class="theme-mata"')

    def test_password_request_creates_pending_request(self):
        user = User.objects.create_user(
            username='pedido',
            display_name='Pedido',
            handle='pedido',
            email='pedido@example.com',
            password=self.password,
        )
        response = self.client.post(
            reverse('password-request'),
            {
                'username': user.username,
                'email': user.email,
                'suggested_password1': 'NovaSenhaSegura!2026',
                'suggested_password2': 'NovaSenhaSegura!2026',
                'note': 'Preciso liberar um novo acesso.',
            },
        )
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(PasswordRequest.objects.filter(target_user=user, status=PasswordRequest.Status.PENDING).exists())

    def test_password_request_rejects_weak_suggested_password(self):
        user = User.objects.create_user(
            username='pedido.fraco',
            display_name='Pedido Fraco',
            handle='pedido_fraco',
            email='pedido.fraco@example.com',
            password=self.password,
        )
        response = self.client.post(
            reverse('password-request'),
            {
                'username': user.username,
                'email': user.email,
                'suggested_password1': '123',
                'suggested_password2': '123',
                'note': 'Preciso liberar um novo acesso.',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('suggested_password1', response.context['form'].errors)
        self.assertFalse(PasswordRequest.objects.filter(target_user=user).exists())

    def test_two_factor_login_creates_challenge(self):
        user = User.objects.create_user(
            username='doisfatores',
            display_name='Dois Fatores',
            handle='dois_fatores',
            email='doisfatores@example.com',
            phone_number='+55 11 99999-9999',
            two_factor_enabled=True,
            two_factor_channel=User.TwoFactorChannel.SMS,
            password=self.password,
        )
        response = self._session_login(user)
        self.assertRedirects(response, reverse('two-factor-verify'))
        challenge = user.two_factor_challenges.get()
        self.assertEqual(challenge.channel, User.TwoFactorChannel.SMS)
        self.assertEqual(challenge.sent_to, user.phone_number)

    def test_api_token_login_issues_short_access_token_and_protected_refresh_cookie(self):
        user = User.objects.create_user(
            username='api',
            display_name='API',
            handle='api',
            email='api@example.com',
            password=self.password,
        )
        response = self.client.post(
            reverse('api-token-login'),
            data=json.dumps({'username': user.username, 'password': self.password}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        access_payload = verify_token(payload['access_token'], expected_type='access')
        self.assertEqual(access_payload['username'], user.username)
        self.assertEqual(payload['user']['username'], user.username)
        self.assertEqual(payload['expires_in'], 600)
        refresh_cookie = response.cookies['raiz_refresh_token']
        self.assertTrue(refresh_cookie['httponly'])
        self.assertEqual(refresh_cookie['path'], reverse('api-token-refresh'))

    def test_blocker_can_open_profile_and_unblock(self):
        blocker = User.objects.create_user(
            username='bloqueador',
            display_name='Bloqueador',
            handle='bloqueador',
            email='bloqueador@example.com',
            password=self.password,
        )
        target = User.objects.create_user(
            username='alvo',
            display_name='Alvo',
            handle='alvo',
            email='alvo@example.com',
            password=self.password,
        )
        self._force_login(blocker)
        self.client.post(reverse('user-block-toggle', args=[target.handle]))
        response = self.client.get(reverse('profile', args=[target.handle]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Desbloquear')
