from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.utils import timezone


class ConversationQuerySet(models.QuerySet):
    def for_user(self, user):
        if getattr(user, 'can_view_all_content', False):
            return self.all()
        return self.filter(participants=user).distinct()


class Conversation(models.Model):
    title = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_conversations')
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ConversationParticipant',
        related_name='conversations',
    )
    is_group = models.BooleanField(default=False)
    direct_key = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ConversationQuerySet.as_manager()

    class Meta:
        ordering = ['-updated_at', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['direct_key'],
                condition=Q(is_group=False) & ~Q(direct_key=''),
                name='unique_direct_conversation_pair',
            ),
        ]

    def __str__(self):
        return self.title or f'Conversa {self.pk}'

    def other_participants(self, user):
        return self.participants.exclude(pk=user.pk)

    @staticmethod
    def build_direct_key(user_a_id, user_b_id):
        first_id, second_id = sorted([int(user_a_id), int(user_b_id)])
        return f'{first_id}:{second_id}'

    @classmethod
    def get_or_create_direct(cls, user_a, user_b):
        direct_key = cls.build_direct_key(user_a.pk, user_b.pk)
        existing = cls.objects.filter(is_group=False, direct_key=direct_key).first()
        if existing:
            return existing, False

        with transaction.atomic():
            try:
                conversation = cls.objects.create(
                    created_by=user_a,
                    title=f'{user_a.display_name} e {user_b.display_name}',
                    direct_key=direct_key,
                )
            except IntegrityError:
                return cls.objects.get(is_group=False, direct_key=direct_key), False
            ConversationParticipant.objects.bulk_create(
                [
                    ConversationParticipant(conversation=conversation, user=user_a),
                    ConversationParticipant(conversation=conversation, user=user_b),
                ]
            )
        return conversation, True


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'user'], name='unique_participant_per_conversation'),
        ]

    def __str__(self):
        return f'{self.user} em #{self.conversation_id}'


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages_sent')
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            Conversation.objects.filter(pk=self.conversation_id).update(updated_at=timezone.now())

    def __str__(self):
        return f'{self.author}: {self.body[:40]}'


class MessageReport(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Aberta'
        REVIEWED = 'reviewed', 'Vista'

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reports_sent',
    )
    reason = models.CharField(max_length=280, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['message', 'reported_by'], name='unique_report_per_user_and_message'),
        ]

    def __str__(self):
        return f'Reporte #{self.pk} da mensagem {self.message_id}'

# Create your models here.
