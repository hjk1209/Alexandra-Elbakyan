import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, TemplateView, UpdateView

from core.models import SecurityEvent
from core.security import get_client_ip, is_login_locked_out, record_login_attempt, record_security_event, throttle_request
from social.models import Follow, WeeklyTask
from social.services import is_following, ordered_posts_for, with_social_totals

from .forms import (
    LoginForm,
    PasswordRequestForm,
    ProfileForm,
    SignUpForm,
    TwoFactorVerificationForm,
)
from .models import ApiRefreshToken, PasswordRequest, TwoFactorChallenge, User, UserBlock
from .services import deliver_two_factor_code, get_user_for_username
from .tokens import build_access_token, build_refresh_token, verify_token


def _safe_next_url(request):
    next_url = request.POST.get('next') or request.GET.get('next') or request.session.get('post_2fa_next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ''


def _default_success_url(user):
    if user.can_moderate or user.is_superuser:
        return reverse('security-center')
    if getattr(user, 'can_operate_health', False):
        return reverse('health-dashboard')
    return reverse('feed')


def _issue_session_login(request, user):
    login(request, user)
    request.session.cycle_key()
    record_login_attempt(request, username=user.username, success=True, user=user)
    record_security_event(
        request,
        SecurityEvent.EventType.LOGIN_SUCCESS,
        user=user,
        details={'handle': user.handle, 'username': user.username},
    )


def _set_refresh_cookie(response, token):
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        token,
        max_age=settings.JWT_REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        path=reverse('api-token-refresh'),
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(settings.JWT_REFRESH_COOKIE_NAME, path=reverse('api-token-refresh'))


def _parse_request_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return {}
    return request.POST


def _issue_api_tokens(request, user):
    access_token, access_payload = build_access_token(user)
    refresh_token, refresh_payload = build_refresh_token(user)
    ApiRefreshToken.issue(
        user=user,
        raw_token=refresh_token,
        jti=refresh_payload['jti'],
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        ttl_days=settings.JWT_REFRESH_TOKEN_TTL_DAYS,
    )
    record_security_event(
        request,
        SecurityEvent.EventType.TOKEN_ISSUED,
        user=user,
        details={'username': user.username, 'refresh_jti': refresh_payload['jti']},
    )
    response = JsonResponse(
        {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': settings.JWT_ACCESS_TOKEN_TTL_MINUTES * 60,
            'user': {
                'id': user.pk,
                'username': user.username,
                'display_name': user.display_name,
                'role': user.role,
            },
        }
    )
    _set_refresh_cookie(response, refresh_token)
    return response


class SignUpView(FormView):
    template_name = 'accounts/signup.html'
    form_class = SignUpForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(_default_success_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        limited, _ = throttle_request(self.request, 'signup-create', settings.SIGNUP_RATE_LIMIT_PER_HOUR, 3600)
        if limited:
            record_security_event(
                self.request,
                SecurityEvent.EventType.THROTTLE,
                severity=SecurityEvent.Severity.WARNING,
                details={'scope': 'signup-create'},
            )
            messages.error(self.request, 'Cadastro temporariamente limitado. Aguarde um pouco antes de tentar de novo.')
            return self.form_invalid(form)

        user = form.save()
        _issue_session_login(self.request, user)
        record_security_event(
            self.request,
            SecurityEvent.EventType.SIGNUP,
            user=user,
            details={'handle': user.handle, 'username': user.username},
        )
        messages.success(self.request, f'Perfil criado. Seu nome de usuario de acesso e {user.username}.')
        return redirect('feed')


class SecureLoginView(FormView):
    template_name = 'accounts/login.html'
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(_default_success_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        username = str(form.cleaned_data['username']).strip()
        ip_address = get_client_ip(self.request)
        if is_login_locked_out(username.lower(), ip_address):
            record_security_event(
                self.request,
                SecurityEvent.EventType.LOCKOUT,
                severity=SecurityEvent.Severity.WARNING,
                details={'username': username, 'reason': 'excesso de falhas recentes'},
            )
            messages.error(self.request, 'Bloqueio temporario ativado. Aguarde alguns minutos antes de tentar de novo.')
            response = self.render_to_response(self.get_context_data(form=form))
            response.status_code = 429
            return response

        user = get_user_for_username(form.cleaned_data['username'])
        if user is None or not user.check_password(form.cleaned_data['password']):
            record_login_attempt(self.request, username=username.lower(), success=False)
            messages.error(self.request, 'Nome de usuario ou senha invalidos.')
            return self.form_invalid(form)

        if user.two_factor_enabled:
            challenge, raw_code = TwoFactorChallenge.issue(
                user=user,
                channel=user.two_factor_channel,
                ttl_minutes=settings.TWO_FACTOR_CODE_TTL_MINUTES,
            )
            masked_destination = deliver_two_factor_code(user, challenge, raw_code)
            self.request.session['pending_2fa_user_id'] = user.pk
            self.request.session['pending_2fa_challenge_id'] = challenge.pk
            self.request.session['post_2fa_next'] = _safe_next_url(self.request)
            record_security_event(
                self.request,
                SecurityEvent.EventType.TWO_FACTOR_CHALLENGE,
                user=user,
                details={'channel': challenge.channel, 'sent_to': masked_destination},
            )
            messages.info(self.request, f'Codigo de verificacao enviado para {masked_destination}.')
            if settings.DEBUG:
                messages.info(self.request, f'Codigo de teste: {raw_code}')
            return redirect('two-factor-verify')

        _issue_session_login(self.request, user)
        destination = _safe_next_url(self.request) or _default_success_url(user)
        return HttpResponseRedirect(destination)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_password_request_total'] = PasswordRequest.objects.filter(
            status=PasswordRequest.Status.PENDING
        ).count()
        return context


class TwoFactorVerifyView(FormView):
    template_name = 'accounts/two_factor_verify.html'
    form_class = TwoFactorVerificationForm

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('pending_2fa_user_id') or not request.session.get('pending_2fa_challenge_id'):
            messages.error(request, 'Nao existe desafio 2FA pendente para esta sessao.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        challenge = get_object_or_404(TwoFactorChallenge, pk=self.request.session.get('pending_2fa_challenge_id'))
        kwargs['challenge'] = challenge
        return kwargs

    def form_valid(self, form):
        user = get_object_or_404(User, pk=self.request.session.get('pending_2fa_user_id'))
        challenge = get_object_or_404(TwoFactorChallenge, pk=self.request.session.get('pending_2fa_challenge_id'))
        if challenge.user_id != user.pk or not challenge.verify_code(form.cleaned_data['code']):
            record_security_event(
                self.request,
                SecurityEvent.EventType.TWO_FACTOR_FAILURE,
                severity=SecurityEvent.Severity.WARNING,
                user=user,
                details={'challenge_id': challenge.pk},
            )
            messages.error(self.request, 'Codigo invalido ou expirado.')
            return self.form_invalid(form)

        user.last_two_factor_verified_at = timezone.now()
        user.save(update_fields=['last_two_factor_verified_at'])
        _issue_session_login(self.request, user)
        record_security_event(
            self.request,
            SecurityEvent.EventType.TWO_FACTOR_SUCCESS,
            user=user,
            details={'challenge_id': challenge.pk},
        )
        destination = _safe_next_url(self.request) or _default_success_url(user)
        self.request.session.pop('pending_2fa_user_id', None)
        self.request.session.pop('pending_2fa_challenge_id', None)
        self.request.session.pop('post_2fa_next', None)
        return redirect(destination)


class ApiTokenLoginView(View):
    def post(self, request, *args, **kwargs):
        limited, _ = throttle_request(request, 'api-login', settings.LOGIN_API_RATE_LIMIT_PER_MINUTE, 60)
        if limited:
            return JsonResponse({'detail': 'Requisicao bloqueada temporariamente.'}, status=429)

        payload = _parse_request_payload(request)
        username = str(payload.get('username') or '').strip()
        password = payload.get('password') or ''
        two_factor_code = payload.get('two_factor_code') or ''
        ip_address = get_client_ip(request)
        if is_login_locked_out(username.lower(), ip_address):
            record_security_event(
                request,
                SecurityEvent.EventType.LOCKOUT,
                severity=SecurityEvent.Severity.WARNING,
                details={'username': username, 'scope': 'api-login'},
            )
            return JsonResponse({'detail': 'Login bloqueado temporariamente.'}, status=429)

        user = get_user_for_username(username)
        if user is None or not user.check_password(password):
            record_login_attempt(request, username=username.lower(), success=False)
            return JsonResponse({'detail': 'Credenciais invalidas.'}, status=401)

        if user.two_factor_enabled:
            challenge = user.two_factor_challenges.filter(
                purpose=TwoFactorChallenge.Purpose.LOGIN,
                consumed_at__isnull=True,
            ).order_by('-created_at').first()
            if not two_factor_code:
                challenge, raw_code = TwoFactorChallenge.issue(
                    user=user,
                    channel=user.two_factor_channel,
                    ttl_minutes=settings.TWO_FACTOR_CODE_TTL_MINUTES,
                )
                masked_destination = deliver_two_factor_code(user, challenge, raw_code)
                record_security_event(
                    request,
                    SecurityEvent.EventType.TWO_FACTOR_CHALLENGE,
                    user=user,
                    details={'channel': challenge.channel, 'sent_to': masked_destination},
                )
                return JsonResponse(
                    {
                        'detail': 'Codigo de verificacao exigido.',
                        'requires_two_factor': True,
                    },
                    status=401,
                )
            if challenge is None or not challenge.verify_code(two_factor_code):
                record_security_event(
                    request,
                    SecurityEvent.EventType.TWO_FACTOR_FAILURE,
                    severity=SecurityEvent.Severity.WARNING,
                    user=user,
                    details={'channel': user.two_factor_channel},
                )
                return JsonResponse({'detail': 'Codigo de verificacao invalido.'}, status=401)
            user.last_two_factor_verified_at = timezone.now()
            user.save(update_fields=['last_two_factor_verified_at'])
            record_security_event(
                request,
                SecurityEvent.EventType.TWO_FACTOR_SUCCESS,
                user=user,
                details={'channel': user.two_factor_channel},
            )

        record_login_attempt(request, username=user.username, success=True, user=user)
        return _issue_api_tokens(request, user)


class ApiTokenRefreshView(View):
    def post(self, request, *args, **kwargs):
        raw_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME) or _parse_request_payload(request).get('refresh_token')
        if not raw_token:
            return JsonResponse({'detail': 'Refresh token ausente.'}, status=401)

        try:
            payload = verify_token(raw_token, expected_type='refresh')
        except ValueError:
            return JsonResponse({'detail': 'Refresh token invalido.'}, status=401)

        stored = ApiRefreshToken.objects.filter(jti=payload['jti']).select_related('user').first()
        if stored is None or not stored.verify_token(raw_token):
            return JsonResponse({'detail': 'Refresh token revogado ou invalido.'}, status=401)

        user = stored.user
        stored.revoke()
        response = _issue_api_tokens(request, user)
        record_security_event(
            request,
            SecurityEvent.EventType.TOKEN_REFRESHED,
            user=user,
            details={'old_jti': payload['jti']},
        )
        return response


class ApiTokenRevokeView(View):
    def post(self, request, *args, **kwargs):
        raw_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME) or _parse_request_payload(request).get('refresh_token')
        response = JsonResponse({'detail': 'Sessao de API encerrada.'})
        if raw_token:
            try:
                payload = verify_token(raw_token, expected_type='refresh')
            except ValueError:
                _clear_refresh_cookie(response)
                return response
            stored = ApiRefreshToken.objects.filter(jti=payload['jti']).first()
            if stored:
                stored.revoke()
            record_security_event(
                request,
                SecurityEvent.EventType.TOKEN_REVOKED,
                details={'refresh_jti': payload['jti']},
            )
        _clear_refresh_cookie(response)
        return response


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        record_security_event(request, SecurityEvent.EventType.LOGOUT, user=request.user)
        logout(request)
    response = redirect('home')
    _clear_refresh_cookie(response)
    messages.info(request, 'Sessao encerrada com seguranca.')
    return response


class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/profile_detail.html'
    slug_field = 'handle'
    slug_url_kwarg = 'handle'
    context_object_name = 'profile_user'

    def get_queryset(self):
        return User.objects.filter(is_active=True)

    def get_object(self, queryset=None):
        profile_user = super().get_object(queryset)
        if not profile_user.can_view_profile(self.request.user):
            raise Http404('Perfil nao disponivel para este acesso.')
        return profile_user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = context['profile_user']
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        context['own_profile'] = profile_user == self.request.user
        context['following'] = is_following(self.request.user, profile_user)
        context['is_blocked'] = self.request.user.blocks(profile_user)
        context['followers_total'] = profile_user.follower_links.count()
        context['following_total'] = profile_user.following_links.count()
        context['posts'] = ordered_posts_for(self.request.user, filter_mode='latest', author=profile_user)
        context['weekly_tasks'] = WeeklyTask.objects.filter(
            assignee=profile_user,
            due_date__range=(week_start, week_end),
        ).select_related('created_by')
        context['week_label'] = f'{week_start:%d/%m} a {week_end:%d/%m}'
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile_edit.html'

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'handle': self.request.user.handle})


class ProfileConnectionsView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile_connections.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = get_object_or_404(User, handle=self.kwargs['handle'], is_active=True)
        if not profile_user.can_view_profile(self.request.user):
            raise Http404('Lista protegida.')
        relation_type = self.kwargs['relation_type']
        if relation_type not in {'seguidores', 'seguindo'}:
            raise Http404('Lista de conexoes nao encontrada.')
        if relation_type == 'seguidores':
            connections = with_social_totals(
                User.objects.filter(following_links__following=profile_user, is_active=True).distinct()
            )
            context['page_title'] = f'Seguidores de {profile_user.display_name}'
            context['page_description'] = 'Perfis que acompanham este perfil na rede.'
        else:
            connections = with_social_totals(
                User.objects.filter(follower_links__follower=profile_user, is_active=True).distinct()
            )
            context['page_title'] = f'{profile_user.display_name} esta seguindo'
            context['page_description'] = 'Perfis acompanhados por este usuario ou coletivo.'
        context['profile_user'] = profile_user
        context['relation_type'] = relation_type
        context['connections'] = connections.order_by('-followers_total', 'display_name', 'username')
        context['following_ids'] = set(
            self.request.user.following_links.values_list('following_id', flat=True)
        )
        return context


class UserBlockToggleView(LoginRequiredMixin, View):
    def post(self, request, handle, *args, **kwargs):
        target = get_object_or_404(User, handle=handle, is_active=True)
        if target == request.user:
            messages.error(request, 'Nao e possivel bloquear a propria conta.')
            return redirect('profile', handle=handle)

        block, created = UserBlock.objects.get_or_create(blocker=request.user, blocked=target)
        if created:
            Follow.objects.filter(follower=request.user, following=target).delete()
            Follow.objects.filter(follower=target, following=request.user).delete()
            record_security_event(
                request,
                SecurityEvent.EventType.USER_BLOCKED,
                severity=SecurityEvent.Severity.WARNING,
                user=target,
                details={'blocked_by': request.user.login_id},
            )
            messages.success(request, f'{target.display_name} foi bloqueado para sua seguranca.')
        else:
            block.delete()
            record_security_event(
                request,
                SecurityEvent.EventType.USER_UNBLOCKED,
                user=target,
                details={'unblocked_by': request.user.login_id},
            )
            messages.info(request, f'Bloqueio removido para {target.display_name}.')
        return redirect('profile', handle=handle)


class PasswordRequestView(FormView):
    template_name = 'accounts/password_request.html'
    form_class = PasswordRequestForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('security-center' if request.user.can_moderate or request.user.is_superuser else 'profile-edit')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        limited, _ = throttle_request(self.request, 'password-recovery-request', settings.RECOVERY_RATE_LIMIT_PER_HOUR, 3600)
        if limited:
            messages.error(self.request, 'Recuperacao temporariamente limitada. Aguarde antes de tentar de novo.')
            return self.form_invalid(form)

        password_request = form.save()
        record_security_event(
            self.request,
            SecurityEvent.EventType.PASSWORD_REQUESTED,
            severity=SecurityEvent.Severity.WARNING,
            user=password_request.target_user,
            details={'requested_username': password_request.requested_username},
        )
        messages.success(
            self.request,
            'Solicitacao de senha enviada. Aguarde a aprovacao da equipe administrativa para entrar com a nova senha.',
        )
        return redirect('login')
