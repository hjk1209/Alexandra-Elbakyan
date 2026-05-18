from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from core.moderation import moderation_findings
from core.models import SecurityEvent
from core.security import record_security_event, throttle_request

from .forms import ConversationForm, MessageForm
from .models import Conversation, Message, MessageReport


def _avatar_letter(user):
    return (user.display_name or user.username or '?')[:1].upper()


def _conversation_card(conversation, current_user):
    participants = list(conversation.participants.all())
    others = [participant for participant in participants if participant.pk != current_user.pk]
    peer = others[0] if others else (participants[0] if participants else current_user)
    messages = list(conversation.messages.all())
    last_message = messages[-1] if messages else None
    if conversation.is_group and conversation.title:
        display_title = conversation.title
        display_subtitle = f'{len(participants)} participantes'
        privacy_label = 'Conversa em grupo'
        privacy_summary = 'Essa conversa pode ter mais de duas pessoas.'
    else:
        display_title = peer.display_name
        display_subtitle = f'@{peer.handle} | pessoal'
        privacy_label = 'Ponta a ponta'
        privacy_summary = f'So voce e {peer.display_name} acessam este chat pessoal.'
        if current_user.can_view_all_content and current_user not in participants:
            display_title = conversation.title or 'Conversa monitorada'
            display_subtitle = 'acesso administrativo'
            privacy_label = 'Visao do adm'
            privacy_summary = 'Administrador visualiza esta conversa para gestao e auditoria.'
    return {
        'instance': conversation,
        'peer': peer,
        'peer_letter': _avatar_letter(peer),
        'title': display_title,
        'subtitle': display_subtitle,
        'privacy_label': privacy_label,
        'privacy_summary': privacy_summary,
        'last_message': last_message,
        'participants_total': len(participants),
    }


class InboxView(LoginRequiredMixin, TemplateView):
    template_name = 'messaging/inbox.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversations = Conversation.objects.for_user(self.request.user).prefetch_related('participants', 'messages__author')
        if not self.request.user.can_view_all_content:
            conversations = [
                conversation
                for conversation in conversations
                if not any(
                    self.request.user.blocks(participant) or participant.blocks(self.request.user)
                    for participant in conversation.participants.all()
                    if participant.pk != self.request.user.pk
                )
            ]
        selected_id = kwargs.get('conversation_id')
        selected_conversation = None
        if selected_id is not None:
            selected_conversation = next((conversation for conversation in conversations if conversation.pk == selected_id), None)
            if selected_conversation is None:
                raise Http404('Conversa nao encontrada.')
        conversation_cards = [_conversation_card(conversation, self.request.user) for conversation in conversations]
        context['conversation_cards'] = conversation_cards
        context['conversations'] = conversations
        context['selected_conversation'] = selected_conversation
        context['conversation_form'] = ConversationForm(user=self.request.user)
        context['message_form'] = MessageForm()
        context['reported_message_ids'] = set()
        if selected_conversation is not None:
            context['selected_card'] = _conversation_card(selected_conversation, self.request.user)
            context['reported_message_ids'] = set(
                MessageReport.objects.filter(
                    message__conversation=selected_conversation,
                    reported_by=self.request.user,
                ).values_list('message_id', flat=True)
            )
        else:
            context['selected_card'] = None
        return context


class StartConversationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        limited, _ = throttle_request(request, 'conversation-start', 5, 600)
        if limited:
            record_security_event(
                request,
                SecurityEvent.EventType.THROTTLE,
                severity=SecurityEvent.Severity.WARNING,
                user=request.user,
                details={'scope': 'conversation-start'},
            )
            messages.error(request, 'Muitas conversas abertas em pouco tempo. Espere alguns minutos.')
            return redirect('inbox')

        form = ConversationForm(request.POST, user=request.user)
        if not form.is_valid():
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
            return redirect('inbox')

        recipient = form.cleaned_data['recipient']
        if request.user.blocks(recipient) or recipient.blocks(request.user):
            messages.error(request, 'Essa conversa nao pode ser iniciada por causa de um bloqueio entre os perfis.')
            return redirect('inbox')
        findings = moderation_findings(form.cleaned_data['initial_message'])
        if findings['should_block']:
            record_security_event(
                request,
                SecurityEvent.EventType.CONTENT_BLOCKED,
                severity=SecurityEvent.Severity.WARNING,
                user=request.user,
                details={'scope': 'direct_message_opening', 'findings': findings},
            )
            messages.error(request, 'A mensagem inicial foi bloqueada por conteudo suspeito ou padrao de spam.')
            return redirect('inbox')
        conversation, created = Conversation.get_or_create_direct(request.user, recipient)
        Message.objects.create(
            conversation=conversation,
            author=request.user,
            body=form.cleaned_data['initial_message'],
        )
        if created:
            messages.success(request, f'Chat pessoal criado com {recipient.display_name}.')
        else:
            messages.success(request, f'Chat pessoal com {recipient.display_name} atualizado na mesma conversa.')
        return redirect('conversation-detail', conversation_id=conversation.pk)


class MessageCreateView(LoginRequiredMixin, View):
    def post(self, request, conversation_id, *args, **kwargs):
        conversation = Conversation.objects.for_user(request.user).filter(pk=conversation_id).first()
        if conversation is None:
            raise Http404('Conversa nao encontrada.')
        participants = list(conversation.participants.all())
        if request.user.can_view_all_content and request.user not in participants:
            messages.error(request, 'Administradores podem visualizar esta conversa, mas nao enviar mensagens por usuarios.')
            return redirect('conversation-detail', conversation_id=conversation.pk)
        if any(
            request.user.blocks(participant) or participant.blocks(request.user)
            for participant in participants
            if participant.pk != request.user.pk
        ):
            messages.error(request, 'O envio foi bloqueado por regra de privacidade entre os perfis.')
            return redirect('inbox')

        limited, _ = throttle_request(
            request,
            f'message-send:{conversation_id}',
            settings.MESSAGE_RATE_LIMIT_PER_MINUTE,
            60,
        )
        if limited:
            record_security_event(
                request,
                SecurityEvent.EventType.THROTTLE,
                severity=SecurityEvent.Severity.WARNING,
                user=request.user,
                details={'scope': 'message'},
            )
            messages.error(request, 'Voce esta enviando mensagens rapido demais. Aguarde um minuto.')
            return redirect('conversation-detail', conversation_id=conversation.pk)

        form = MessageForm(request.POST)
        if form.is_valid():
            findings = moderation_findings(form.cleaned_data['body'])
            if findings['should_block']:
                record_security_event(
                    request,
                    SecurityEvent.EventType.CONTENT_BLOCKED,
                    severity=SecurityEvent.Severity.WARNING,
                    user=request.user,
                    details={'scope': 'message', 'findings': findings},
                )
                messages.error(request, 'Mensagem bloqueada por conteudo suspeito ou padrao de spam.')
                return redirect('conversation-detail', conversation_id=conversation.pk)
            Message.objects.create(
                conversation=conversation,
                author=request.user,
                body=form.cleaned_data['body'],
            )
            messages.success(request, 'Mensagem enviada.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('conversation-detail', conversation_id=conversation.pk)


class MessageReportCreateView(LoginRequiredMixin, View):
    def post(self, request, conversation_id, message_id, *args, **kwargs):
        conversation = Conversation.objects.for_user(request.user).filter(pk=conversation_id).first()
        if conversation is None:
            raise Http404('Conversa nao encontrada.')
        if request.user.can_view_all_content:
            messages.info(request, 'Administrador nao reporta mensagem: use o painel de moderacao para gerenciar a situacao.')
            return redirect('conversation-detail', conversation_id=conversation.pk)
        limited, _ = throttle_request(
            request,
            'message-report',
            settings.REPORT_RATE_LIMIT_PER_MINUTE,
            60,
        )
        if limited:
            messages.error(request, 'Denuncias temporariamente limitadas. Aguarde um minuto.')
            return redirect('conversation-detail', conversation_id=conversation.pk)

        message = get_object_or_404(conversation.messages.select_related('author'), pk=message_id)
        if message.author_id == request.user.pk:
            messages.error(request, 'Nao e possivel reportar a propria mensagem.')
            return redirect('conversation-detail', conversation_id=conversation.pk)

        report, created = MessageReport.objects.get_or_create(
            message=message,
            reported_by=request.user,
            defaults={
                'reason': (request.POST.get('reason') or '').strip()[:280],
            },
        )
        if not created:
            messages.info(request, 'Essa mensagem ja foi reportada anteriormente por voce.')
            return redirect('conversation-detail', conversation_id=conversation.pk)

        if not report.reason:
            report.reason = 'Mensagem marcada como estranha pelo usuario.'
            report.save(update_fields=['reason'])

        record_security_event(
            request,
            SecurityEvent.EventType.MESSAGE_REPORTED,
            severity=SecurityEvent.Severity.WARNING,
            user=message.author,
            details={
                'reported_by': request.user.login_id,
                'conversation_id': conversation.pk,
                'message_id': message.pk,
            },
        )
        messages.success(request, 'Mensagem reportada para a equipe de moderacao.')
        return redirect('conversation-detail', conversation_id=conversation.pk)
