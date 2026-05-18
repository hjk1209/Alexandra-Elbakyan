import mimetypes

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from accounts.forms import AdminActionReasonForm, ManagedUserCreateForm, ManagedUserUpdateForm
from accounts.models import PasswordRequest, User
from messaging.models import Conversation, Message, MessageReport
from social.models import Post, Story
from social.services import visible_posts_for, visible_stories_for

from .models import LoginAttempt, SecurityEvent
from .security import record_security_event, resolve_protected_media_token


def can_moderate_content(user):
    return user.is_authenticated and (user.can_moderate or user.can_administer or user.can_found or user.is_superuser)


def can_manage_users(user):
    return user.is_authenticated and (user.can_administer or user.can_found or user.is_superuser)


def can_change_roles(user):
    return user.is_authenticated and (user.can_found or user.is_superuser)


def can_manage_target_user(actor, target):
    if not can_manage_users(actor):
        return False
    if actor.pk == target.pk:
        return False
    if target.is_superuser and not actor.is_superuser:
        return False
    role_rank = {
        User.Role.MEMBER: 10,
        User.Role.COLLECTIVE: 10,
        User.Role.MODERATOR: 20,
        User.Role.ADMIN: 30,
        User.Role.FOUNDER: 40,
    }
    if not actor.is_superuser and role_rank.get(target.role, 0) >= role_rank.get(actor.role, 0):
        return False
    return True


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['member_total'] = User.objects.count()
        context['post_total'] = Post.objects.count()
        context['conversation_total'] = Conversation.objects.count()
        context['message_total'] = Message.objects.count()
        return context


class ProtectedMediaView(LoginRequiredMixin, View):
    def get(self, request, kind, object_id, action, token, *args, **kwargs):
        try:
            payload = resolve_protected_media_token(token)
        except Exception as exc:  # pragma: no cover - generic by design
            raise Http404('Arquivo indisponivel.') from exc

        if payload.get('kind') != kind or int(payload.get('object_id', 0)) != int(object_id) or payload.get('action') != action:
            raise Http404('Arquivo indisponivel.')

        if kind == 'avatar':
            target = get_object_or_404(User, pk=object_id, is_active=True)
            if not target.can_view_profile(request.user):
                raise Http404('Arquivo indisponivel.')
            file_field = target.avatar
            file_label = f'avatar:{target.pk}'
            allow_download = True
        elif kind == 'post':
            post = get_object_or_404(visible_posts_for(request.user), pk=object_id)
            file_field = post.media
            file_label = f'post:{post.pk}'
            allow_download = post.allow_download
        elif kind == 'story':
            story = get_object_or_404(visible_stories_for(request.user), pk=object_id)
            file_field = story.media
            file_label = f'story:{story.pk}'
            allow_download = story.allow_download
        else:
            raise Http404('Arquivo indisponivel.')

        if not file_field:
            raise Http404('Arquivo indisponivel.')
        if action == 'download' and not allow_download:
            raise Http404('Arquivo indisponivel.')

        guessed_type, _ = mimetypes.guess_type(file_field.name)
        response = FileResponse(
            file_field.open('rb'),
            as_attachment=action == 'download',
            filename=file_field.name.rsplit('/', 1)[-1],
            content_type=guessed_type or 'application/octet-stream',
        )
        response['Cache-Control'] = 'private, no-store, max-age=0'
        response['Pragma'] = 'no-cache'
        if action == 'download':
            record_security_event(
                request,
                SecurityEvent.EventType.DOWNLOAD,
                user=request.user,
                details={'resource': file_label},
            )
        return response


class SecurityCenterView(LoginRequiredMixin, TemplateView):
    template_name = 'core/security_center.html'

    def dispatch(self, request, *args, **kwargs):
        if can_moderate_content(request.user):
            record_security_event(
                request,
                SecurityEvent.EventType.ADMIN_ACCESS,
                user=request.user,
                details={'section': 'security_center'},
            )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not can_manage_users(request.user):
            messages.error(request, 'Apenas administradores autorizados podem cadastrar usuarios por aqui.')
            return redirect('security-center')
        if not request.user.has_recent_strong_auth():
            messages.error(request, 'Reforce a autenticacao entrando novamente antes de criar usuarios.')
            return redirect('security-center')

        form = ManagedUserCreateForm(
            request.POST,
            request.FILES,
            can_change_roles=can_change_roles(request.user),
        )
        if form.is_valid():
            managed_user = form.save()
            record_security_event(
                request,
                SecurityEvent.EventType.USER_CREATED,
                user=managed_user,
                details={'managed_by': request.user.login_id, 'role': managed_user.role},
            )
            messages.success(
                request,
                f'Usuario {managed_user.display_name} criado com sucesso. Nome de usuario: {managed_user.username}.',
            )
            return redirect('security-center')

        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return self.render_to_response(self.get_context_data(user_create_form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['recent_attempts'] = user.login_attempts.all()[:10]
        context['recent_events'] = user.security_events.all()[:10]
        context['safety_items'] = [
            'Login por nome de usuario, trilha de auditoria e bloqueio temporario por abuso.',
            'Privacidade reforcada para perfis, arquivos, posts, stories e mensagens.',
            'Setor de saude com prontuarios separados por usuario e operador autorizado por unidade.',
            'Headers defensivos, sessao sem cache autenticado, cookies restritos e refresh token protegido.',
            'Limites por minuto para login, publicacoes, comentarios, mensagens, upload, curtidas e recuperacao.',
        ]
        context['audit_events'] = context['recent_events']
        context['can_moderate_content'] = can_moderate_content(user)
        context['can_manage_users'] = can_manage_users(user)
        context['can_change_roles'] = can_change_roles(user)
        if context['can_moderate_content']:
            context['platform_attempts'] = LoginAttempt.objects.select_related('user')[:12]
            context['platform_events'] = SecurityEvent.objects.select_related('user')[:15]
            context['message_reports'] = MessageReport.objects.select_related(
                'message__author',
                'reported_by',
            )[:12]
            context['password_requests'] = PasswordRequest.objects.select_related(
                'target_user',
                'processed_by',
            )[:12]
            context['audit_events'] = context['platform_events']
        if context['can_manage_users']:
            managed_users = User.objects.order_by('-is_active', 'display_name', 'username')
            context['user_create_form'] = kwargs.get('user_create_form') or ManagedUserCreateForm(
                can_change_roles=can_change_roles(user),
            )
            context['admin_reason_form'] = AdminActionReasonForm()
            context['managed_users'] = [
                {
                    'instance': managed_user,
                    'can_toggle': can_manage_target_user(user, managed_user),
                    'can_edit': can_manage_target_user(user, managed_user) or user.pk == managed_user.pk,
                    'edit_form': ManagedUserUpdateForm(
                        instance=managed_user,
                        can_change_roles=can_change_roles(user),
                        prefix=f'user-{managed_user.pk}',
                    ),
                }
                for managed_user in managed_users
            ]
            context['active_user_total'] = User.objects.filter(is_active=True).count()
            context['inactive_user_total'] = User.objects.filter(is_active=False).count()
        return context


class SecurityUserStatusToggleView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        if not can_manage_users(request.user):
            messages.error(request, 'Apenas administradores autorizados podem alterar usuarios.')
            return redirect('security-center')
        if not request.user.has_recent_strong_auth():
            messages.error(request, 'Reentre na plataforma antes de alterar acessos.')
            return redirect('security-center')

        managed_user = get_object_or_404(User, pk=pk)
        if not can_manage_target_user(request.user, managed_user):
            messages.error(request, 'Esse perfil nao pode ser alterado por esta conta.')
            return redirect('security-center')

        reason_form = AdminActionReasonForm(request.POST)
        if not reason_form.is_valid():
            messages.error(request, 'Explique o motivo antes de alterar o acesso de alguem.')
            return redirect('security-center')

        reason = reason_form.cleaned_data['reason']
        managed_user.is_active = not managed_user.is_active
        managed_user.save(update_fields=['is_active'])
        event_type = (
            SecurityEvent.EventType.USER_REACTIVATED
            if managed_user.is_active
            else SecurityEvent.EventType.USER_DEACTIVATED
        )
        record_security_event(
            request,
            event_type,
            severity=SecurityEvent.Severity.WARNING if not managed_user.is_active else SecurityEvent.Severity.INFO,
            user=managed_user,
            details={'managed_by': request.user.login_id, 'reason': reason},
        )
        action_label = 'reativado' if managed_user.is_active else 'desativado'
        messages.success(request, f'Acesso de {managed_user.username} {action_label}. Motivo registrado: {reason}')
        return redirect('security-center')


class SecurityUserEditView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        if not can_manage_users(request.user):
            messages.error(request, 'Apenas administradores autorizados podem editar usuarios.')
            return redirect('security-center')
        if not request.user.has_recent_strong_auth():
            messages.error(request, 'Reentre na plataforma antes de editar dados de usuarios.')
            return redirect('security-center')

        managed_user = get_object_or_404(User, pk=pk)
        if not (can_manage_target_user(request.user, managed_user) or request.user.pk == managed_user.pk):
            messages.error(request, 'Esse perfil nao pode ser editado por esta conta.')
            return redirect('security-center')

        form = ManagedUserUpdateForm(
            request.POST,
            instance=managed_user,
            can_change_roles=can_change_roles(request.user),
            prefix=f'user-{managed_user.pk}',
        )
        if form.is_valid():
            updated_user = form.save()
            record_security_event(
                request,
                SecurityEvent.EventType.PERMISSION_CHANGED,
                severity=SecurityEvent.Severity.WARNING,
                user=updated_user,
                details={'managed_by': request.user.login_id, 'edited_fields': list(form.changed_data)},
            )
            messages.success(request, f'Dados de {updated_user.username} atualizados pelo gestor do sistema.')
            return redirect('security-center')

        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return redirect('security-center')


class SecurityPasswordRequestActionView(LoginRequiredMixin, View):
    def post(self, request, pk, action, *args, **kwargs):
        if not can_manage_users(request.user):
            messages.error(request, 'Apenas administradores autorizados podem aprovar solicitacoes de senha.')
            return redirect('security-center')
        if not request.user.has_recent_strong_auth():
            messages.error(request, 'Reforce a autenticacao entrando novamente antes de aprovar ou recusar senhas.')
            return redirect('security-center')

        password_request = get_object_or_404(PasswordRequest, pk=pk)
        if password_request.status != PasswordRequest.Status.PENDING:
            messages.info(request, 'Essa solicitacao ja foi processada.')
            return redirect('security-center')

        if action == 'aprovar':
            target_user = password_request.target_user
            target_user.password = password_request.suggested_password_hash
            target_user.save(update_fields=['password'])
            password_request.status = PasswordRequest.Status.APPROVED
            password_request.processed_by = request.user
            password_request.processed_at = timezone.now()
            password_request.save(update_fields=['status', 'processed_by', 'processed_at'])
            record_security_event(
                request,
                SecurityEvent.EventType.PASSWORD_REQUEST_APPROVED,
                severity=SecurityEvent.Severity.WARNING,
                user=target_user,
                details={'requested_username': password_request.requested_username},
            )
            messages.success(request, f'Senha sugerida para {target_user.username} aprovada com sucesso.')
            return redirect('security-center')

        if action == 'recusar':
            password_request.status = PasswordRequest.Status.REJECTED
            password_request.processed_by = request.user
            password_request.processed_at = timezone.now()
            password_request.save(update_fields=['status', 'processed_by', 'processed_at'])
            record_security_event(
                request,
                SecurityEvent.EventType.PASSWORD_REQUEST_REJECTED,
                user=password_request.target_user,
                details={'requested_username': password_request.requested_username},
            )
            messages.info(request, f'Solicitacao de senha para {password_request.requested_username} foi recusada.')
            return redirect('security-center')

        messages.error(request, 'Acao de solicitacao de senha nao reconhecida.')
        return redirect('security-center')
