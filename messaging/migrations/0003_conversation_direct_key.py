from django.db import migrations, models
from django.db.models import Q


def normalize_direct_conversations(apps, schema_editor):
    Conversation = apps.get_model('messaging', 'Conversation')
    ConversationParticipant = apps.get_model('messaging', 'ConversationParticipant')
    Message = apps.get_model('messaging', 'Message')

    direct_groups = {}
    conversations = Conversation.objects.filter(is_group=False).order_by('-updated_at', '-created_at', 'pk')
    for conversation in conversations:
        participant_ids = list(
            ConversationParticipant.objects.filter(conversation_id=conversation.pk)
            .order_by('user_id')
            .values_list('user_id', flat=True)
            .distinct()
        )
        if len(participant_ids) != 2:
            Conversation.objects.filter(pk=conversation.pk).update(is_group=True, direct_key='')
            continue

        direct_key = f'{participant_ids[0]}:{participant_ids[1]}'
        direct_groups.setdefault(direct_key, []).append(conversation)

    for direct_key, group in direct_groups.items():
        canonical = group[0]
        created_at = canonical.created_at
        updated_at = canonical.updated_at

        for duplicate in group[1:]:
            Message.objects.filter(conversation_id=duplicate.pk).update(conversation_id=canonical.pk)
            if duplicate.created_at < created_at:
                created_at = duplicate.created_at
            if duplicate.updated_at > updated_at:
                updated_at = duplicate.updated_at
            duplicate.delete()

        Conversation.objects.filter(pk=canonical.pk).update(
            direct_key=direct_key,
            created_at=created_at,
            updated_at=updated_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0002_messagereport'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='direct_key',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.RunPython(normalize_direct_conversations, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='conversation',
            constraint=models.UniqueConstraint(
                condition=Q(is_group=False) & ~Q(direct_key=''),
                fields=('direct_key',),
                name='unique_direct_conversation_pair',
            ),
        ),
    ]
