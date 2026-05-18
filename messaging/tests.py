from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Conversation, Message, MessageReport


class MessagingTests(TestCase):
    password = 'SenhaSegura!2026'

    def setUp(self):
        self.user_a = User.objects.create_user(
            username='a',
            display_name='Pessoa A',
            handle='pessoa_a',
            email='a@example.com',
            password=self.password,
        )
        self.user_b = User.objects.create_user(
            username='b',
            display_name='Pessoa B',
            handle='pessoa_b',
            email='b@example.com',
            password=self.password,
        )
        self.user_c = User.objects.create_user(
            username='c',
            display_name='Pessoa C',
            handle='pessoa_c',
            email='c@example.com',
            password=self.password,
        )
        self.conversation, _ = Conversation.get_or_create_direct(self.user_a, self.user_b)
        self.message = Message.objects.create(
            conversation=self.conversation,
            author=self.user_b,
            body='Mensagem muito estranha aqui',
        )

    def _force_login(self, user):
        self.client.force_login(user)

    def test_non_participant_cannot_open_conversation(self):
        self._force_login(self.user_c)
        response = self.client.get(reverse('conversation-detail', args=[self.conversation.pk]))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_open_conversation_without_reporting_or_sending(self):
        admin = User.objects.create_user(
            username='adm',
            display_name='Administrador',
            handle='adm',
            email='adm@example.com',
            role=User.Role.ADMIN,
            password=self.password,
        )
        self._force_login(admin)
        response = self.client.get(reverse('conversation-detail', args=[self.conversation.pk]))
        self.assertContains(response, 'Mensagem muito estranha aqui')
        self.assertContains(response, 'Visao do adm')
        self.assertNotContains(response, 'Reportar para moderacao')

        response = self.client.post(
            reverse('message-send', args=[self.conversation.pk]),
            {'body': 'Mensagem administrativa indevida'},
        )
        self.assertRedirects(response, reverse('conversation-detail', args=[self.conversation.pk]))
        self.assertFalse(
            Message.objects.filter(conversation=self.conversation, author=admin, body='Mensagem administrativa indevida').exists()
        )

    def test_inbox_shows_contact_summary_and_message_preview(self):
        self._force_login(self.user_a)
        response = self.client.get(reverse('conversation-detail', args=[self.conversation.pk]))
        self.assertContains(response, 'Pessoa B')
        self.assertContains(response, 'Mensagem muito estranha aqui')
        self.assertContains(response, 'Ponta a ponta')
        self.assertContains(response, 'So voce e Pessoa B acessam este chat pessoal.')

    def test_same_pair_reuses_a_single_personal_chat(self):
        self._force_login(self.user_a)
        response = self.client.post(
            reverse('conversation-start'),
            {'recipient': self.user_b.pk, 'initial_message': 'Seguimos no mesmo chat pessoal'},
        )
        self.assertRedirects(response, reverse('conversation-detail', args=[self.conversation.pk]))
        self.assertEqual(
            Conversation.objects.filter(
                is_group=False,
                direct_key=Conversation.build_direct_key(self.user_a.pk, self.user_b.pk),
            ).count(),
            1,
        )
        self.assertEqual(Message.objects.filter(conversation=self.conversation).count(), 2)

    def test_participant_can_report_message_and_moderator_can_see_queue(self):
        moderator = User.objects.create_user(
            username='moderador',
            display_name='Moderador',
            handle='moderador',
            email='moderador@example.com',
            role=User.Role.MODERATOR,
            password=self.password,
        )

        self._force_login(self.user_a)
        response = self.client.post(
            reverse('message-report', args=[self.conversation.pk, self.message.pk]),
            {'reason': 'Conteudo suspeito'},
        )
        self.assertRedirects(response, reverse('conversation-detail', args=[self.conversation.pk]))
        self.assertTrue(MessageReport.objects.filter(message=self.message, reported_by=self.user_a).exists())

        self._force_login(moderator)
        response = self.client.get(reverse('security-center'))
        self.assertContains(response, 'Mensagem muito estranha aqui')
        self.assertContains(response, 'Conteudo suspeito')

    def test_blocked_users_disappear_from_start_conversation_and_existing_chat(self):
        self.user_a.blocked_users.add(self.user_b)
        self._force_login(self.user_a)
        response = self.client.get(reverse('inbox'))
        self.assertNotContains(response, 'Pessoa B')
        self.assertNotContains(response, 'Mensagem muito estranha aqui')
        self.assertNotContains(response, f'<option value="{self.user_b.pk}">', html=False)
