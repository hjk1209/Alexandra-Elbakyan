from django import forms
from django.db.models import Q

from accounts.models import User
from core.security import clean_plain_text


class ConversationForm(forms.Form):
    recipient = forms.ModelChoiceField(queryset=User.objects.none(), label='Conversar com')
    initial_message = forms.CharField(
        label='Primeira mensagem',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escreva a primeira mensagem do chat pessoal...'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient'].widget.attrs.update({'class': 'chat-select'})
        if user is not None:
            blocked_ids = User.objects.filter(
                Q(blocked_entries__blocker=user) | Q(block_entries__blocked=user)
            ).values_list('pk', flat=True)
            self.fields['recipient'].queryset = User.objects.filter(is_active=True).exclude(pk=user.pk).order_by(
                'display_name',
                'username',
            ).exclude(pk__in=blocked_ids)

    def clean_initial_message(self):
        message = clean_plain_text(self.cleaned_data['initial_message'])
        if not message:
            raise forms.ValidationError('Escreva a primeira mensagem da conversa.')
        return message


class MessageForm(forms.Form):
    body = forms.CharField(
        label='Mensagem',
        widget=forms.Textarea(
            attrs={
                'rows': 2,
                'placeholder': 'Digite uma mensagem',
                'class': 'chat-compose-input',
            }
        ),
    )

    def clean_body(self):
        message = clean_plain_text(self.cleaned_data['body'])
        if not message:
            raise forms.ValidationError('A mensagem nao pode ficar vazia.')
        return message
