import calendar
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from accounts.models import User
from core.moderation import moderation_findings
from core.models import SecurityEvent
from core.security import record_security_event, throttle_request

from .forms import ActivityReportForm, PostForm, StoryForm, StoryReplyForm
from .models import (
    ActivityReport,
    Comment,
    CommunityJoinRequest,
    CommunityNotice,
    Follow,
    GroupActivity,
    Post,
    PostLike,
    Story,
    StoryReaction,
    StoryReply,
    StoryView,
)
from .services import discoverable_users, ordered_posts_for, visible_posts_for, visible_stories_for


FEED_FILTER_OPTIONS = [
    ('latest', 'Ultimas mostradas'),
    ('liked', 'Mais curtidas'),
    ('commented', 'Mais comentadas'),
    ('followers', 'Seguidores'),
    ('random', 'Aleatoria'),
]

STORY_REACTION_OPTIONS = ['🔥', '❤️', '👏', '🌱', '⚡']


def redirect_back(request, fallback='feed'):
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or fallback)


def can_manage_community_requests(user, community):
    return (
        getattr(user, 'is_authenticated', False)
        and community.role == User.Role.COLLECTIVE
        and (
            user.pk == community.pk
            or user.can_administer
            or user.can_found
            or user.is_superuser
        )
    )


def report_communities_for(user):
    return User.objects.filter(is_active=True, role=User.Role.COLLECTIVE).order_by('display_name', 'username')


def build_activity_report_caption(report):
    body = report.body.strip()
    activity_date = report.activity_date.strftime('%d/%m/%Y')
    attachment_note = '\n\nArquivo de apoio anexado na relatoria.' if report.attachment else ''
    caption = (
        f'Relatoria: {report.title}\n'
        f'Atividade em {activity_date}\n'
        f'Enviada por {report.reporter.display_name}\n\n'
        f'{body}'
        f'{attachment_note}'
    )
    if len(caption) <= 2200:
        return caption
    return f'{caption[:2197]}...'


def build_month_calendar(reference_date, activities):
    activity_map = defaultdict(list)
    for activity in activities:
        activity_map[activity.activity_date].append(activity)

    weeks = []
    month_calendar = calendar.Calendar(firstweekday=0)
    for week in month_calendar.monthdatescalendar(reference_date.year, reference_date.month):
        week_cells = []
        for day in week:
            week_cells.append(
                {
                    'date': day,
                    'is_current_month': day.month == reference_date.month,
                    'is_today': day == timezone.localdate(),
                    'activities': activity_map.get(day, []),
                }
            )
        weeks.append(week_cells)
    return weeks


def format_month_label(reference_date):
    month_names = [
        'janeiro',
        'fevereiro',
        'marco',
        'abril',
        'maio',
        'junho',
        'julho',
        'agosto',
        'setembro',
        'outubro',
        'novembro',
        'dezembro',
    ]
    return f'{month_names[reference_date.month - 1]} de {reference_date.year}'


class FeedView(LoginRequiredMixin, TemplateView):
    template_name = 'social/feed.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_mode = (self.request.GET.get('filter') or 'latest').strip().lower()
        valid_filters = {key for key, _ in FEED_FILTER_OPTIONS}
        if filter_mode not in valid_filters:
            filter_mode = 'latest'

        posts = ordered_posts_for(self.request.user, filter_mode=filter_mode).prefetch_related('comments__author')
        stories = visible_stories_for(self.request.user)
        liked_post_ids = list(
            PostLike.objects.filter(user=self.request.user, post__in=posts).values_list('post_id', flat=True)
        )
        following_ids = list(Follow.objects.filter(follower=self.request.user).values_list('following_id', flat=True))
        quick_query = self.request.GET.get('q', '').strip()
        context['post_form'] = PostForm()
        context['posts'] = posts
        context['stories'] = stories[:10]
        context['story_total'] = stories.count()
        context['liked_post_ids'] = liked_post_ids
        context['quick_query'] = quick_query
        context['feed_filter'] = filter_mode
        context['feed_filter_options'] = FEED_FILTER_OPTIONS
        context['suggested_users'] = discoverable_users(self.request.user, query=quick_query).exclude(
            pk__in=following_ids
        )[:5]
        context['community_highlights'] = discoverable_users(
            self.request.user,
            role=User.Role.COLLECTIVE,
        )[:4]
        context['community_notice_total'] = CommunityNotice.objects.count()
        today = timezone.localdate()
        context['current_month_activity_total'] = GroupActivity.objects.filter(
            activity_date__year=today.year,
            activity_date__month=today.month,
        ).count()
        return context


class StoryEditorView(LoginRequiredMixin, FormView):
    template_name = 'social/story_editor.html'
    form_class = StoryForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['story_reaction_options'] = STORY_REACTION_OPTIONS
        context['active_stories'] = visible_stories_for(self.request.user).filter(author=self.request.user)[:6]
        return context

    def form_valid(self, form):
        if self.request.FILES:
            limited_upload, _ = throttle_request(
                self.request,
                'story-upload',
                settings.UPLOAD_RATE_LIMIT_PER_MINUTE,
                60,
            )
            if limited_upload:
                record_security_event(
                    self.request,
                    SecurityEvent.EventType.THROTTLE,
                    severity=SecurityEvent.Severity.WARNING,
                    user=self.request.user,
                    details={'scope': 'story-upload'},
                )
                messages.error(self.request, 'Upload de story temporariamente limitado. Aguarde um minuto.')
                return self.form_invalid(form)

        findings = moderation_findings(form.cleaned_data.get('caption'))
        if findings['should_block']:
            record_security_event(
                self.request,
                SecurityEvent.EventType.CONTENT_BLOCKED,
                severity=SecurityEvent.Severity.WARNING,
                user=self.request.user,
                details={'scope': 'story', 'findings': findings},
            )
            messages.error(self.request, 'Story bloqueado por conteudo suspeito ou padrao de spam.')
            return self.form_invalid(form)

        story = form.save(commit=False)
        story.author = self.request.user
        if self.request.user.is_minor and story.age_rating == Story.AgeRating.AGE_18:
            messages.error(self.request, 'Perfis de menores nao podem publicar story marcado como 18+.')
            return self.form_invalid(form)
        story.save()
        form.save_m2m()
        messages.success(
            self.request,
            f'Story publicado por {story.duration_hours} hora(s). O rascunho local do editor pode ser limpo agora.',
        )
        return redirect('story-detail', pk=story.pk)


class StoryDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'social/story_detail.html'

    def dispatch(self, request, *args, **kwargs):
        self.story = get_object_or_404(
            visible_stories_for(request.user).prefetch_related(
                'allowed_viewers',
                'allowed_responders',
                'views__viewer',
                'reactions__user',
                'replies__author',
            ),
            pk=kwargs['pk'],
        )
        if request.user.pk != self.story.author_id:
            StoryView.objects.get_or_create(story=self.story, viewer=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_reaction = StoryReaction.objects.filter(story=self.story, user=self.request.user).first()
        visible_replies = self.story.replies.select_related('author')
        if self.request.user.pk != self.story.author_id:
            visible_replies = visible_replies.filter(author=self.request.user)

        context['story'] = self.story
        context['story_reply_form'] = StoryReplyForm()
        context['story_reaction_options'] = STORY_REACTION_OPTIONS
        context['can_reply'] = self.story.can_reply(self.request.user)
        context['user_reaction'] = user_reaction
        context['is_story_owner'] = self.request.user.pk == self.story.author_id
        context['story_views'] = self.story.views.select_related('viewer')[:20]
        context['story_reactions'] = self.story.reactions.select_related('user')[:20]
        context['story_replies'] = visible_replies[:20]
        return context


class StoryReactionToggleView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        limited, _ = throttle_request(
            request,
            'story-react',
            settings.LIKE_RATE_LIMIT_PER_MINUTE,
            60,
        )
        if limited:
            messages.error(request, 'Reacoes temporariamente limitadas. Aguarde um minuto.')
            return redirect('story-detail', pk=pk)

        story = get_object_or_404(visible_stories_for(request.user), pk=pk)
        if story.author_id == request.user.pk:
            messages.info(request, 'O autor nao precisa reagir ao proprio story.')
            return redirect('story-detail', pk=story.pk)

        emoji = (request.POST.get('emoji') or '').strip()
        if emoji not in STORY_REACTION_OPTIONS:
            messages.error(request, 'Escolha uma reacao valida para o story.')
            return redirect('story-detail', pk=story.pk)

        reaction, created = StoryReaction.objects.get_or_create(
            story=story,
            user=request.user,
            defaults={'emoji': emoji},
        )
        if created:
            messages.success(request, 'Reacao registrada no story.')
        elif reaction.emoji == emoji:
            reaction.delete()
            messages.info(request, 'Reacao removida do story.')
        else:
            reaction.emoji = emoji
            reaction.save(update_fields=['emoji'])
            messages.success(request, 'Reacao atualizada no story.')
        return redirect('story-detail', pk=story.pk)


class StoryReplyCreateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        story = get_object_or_404(visible_stories_for(request.user), pk=pk)
        if not story.can_reply(request.user):
            messages.error(request, 'Este story nao aceita resposta do seu perfil.')
            return redirect('story-detail', pk=story.pk)

        limited, _ = throttle_request(
            request,
            'story-reply',
            settings.MESSAGE_RATE_LIMIT_PER_MINUTE,
            60,
        )
        if limited:
            messages.error(request, 'Voce respondeu rapido demais. Aguarde um minuto.')
            return redirect('story-detail', pk=story.pk)

        form = StoryReplyForm(request.POST)
        if form.is_valid():
            findings = moderation_findings(form.cleaned_data['body'])
            if findings['should_block']:
                record_security_event(
                    request,
                    SecurityEvent.EventType.CONTENT_BLOCKED,
                    severity=SecurityEvent.Severity.WARNING,
                    user=request.user,
                    details={'scope': 'story_reply', 'findings': findings},
                )
                messages.error(request, 'Resposta bloqueada por conteudo suspeito ou padrao de spam.')
                return redirect('story-detail', pk=story.pk)
            StoryReply.objects.create(
                story=story,
                author=request.user,
                body=form.cleaned_data['body'],
            )
            messages.success(request, 'Resposta enviada ao story.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('story-detail', pk=story.pk)


class PeopleDirectoryView(LoginRequiredMixin, TemplateView):
    template_name = 'social/directory.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        context['following_ids'] = set(
            Follow.objects.filter(follower=self.request.user).values_list('following_id', flat=True)
        )
        context['pending_following_ids'] = set(
            CommunityJoinRequest.objects.filter(
                requester=self.request.user,
                status=CommunityJoinRequest.Status.PENDING,
            ).values_list('community_id', flat=True)
        )
        context['directory_title'] = 'Pessoas da rede'
        context['directory_eyebrow'] = 'Pesquisa de usuarios'
        context['directory_description'] = (
            'Busque por nome, nome de perfil, usuario interno ou local para encontrar militantes, brigadas e equipes.'
        )
        context['search_placeholder'] = 'Buscar por nome, perfil, usuario ou local'
        context['query'] = query
        context['users'] = discoverable_users(self.request.user, query=query)
        context['empty_message'] = 'Nenhum perfil encontrado com esse termo.'
        context['show_role_badge'] = True
        context['directory_kind'] = 'people'
        return context


class CommunityDirectoryView(LoginRequiredMixin, TemplateView):
    template_name = 'social/directory.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        context['following_ids'] = set(
            Follow.objects.filter(follower=self.request.user).values_list('following_id', flat=True)
        )
        context['pending_following_ids'] = set(
            CommunityJoinRequest.objects.filter(
                requester=self.request.user,
                status=CommunityJoinRequest.Status.PENDING,
            ).values_list('community_id', flat=True)
        )
        context['users'] = discoverable_users(
            self.request.user,
            query=query,
            role=User.Role.COLLECTIVE,
        )
        context['directory_title'] = 'Comunidades'
        context['directory_eyebrow'] = 'Aba de comunidades'
        context['directory_description'] = (
            'Encontre coletivos, brigadas e perfis comunitarios para acompanhar articulacoes, campanhas e agendas.'
        )
        context['search_placeholder'] = 'Buscar comunidades por nome, perfil ou territorio'
        context['query'] = query
        context['empty_message'] = 'Nenhuma comunidade encontrada com esse termo.'
        context['show_role_badge'] = False
        context['directory_kind'] = 'communities'
        today = timezone.localdate()
        context['community_notice_total'] = CommunityNotice.objects.count()
        context['current_month_activity_total'] = GroupActivity.objects.filter(
            activity_date__year=today.year,
            activity_date__month=today.month,
        ).count()
        return context


class CommunityHubView(LoginRequiredMixin, TemplateView):
    template_name = 'social/community_hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reference_date = timezone.localdate()
        monthly_activities = GroupActivity.objects.filter(
            activity_date__year=reference_date.year,
            activity_date__month=reference_date.month,
        ).select_related('community', 'created_by')
        context['community_notices'] = CommunityNotice.objects.select_related('community', 'author')[:8]
        context['monthly_activities'] = monthly_activities
        context['calendar_weeks'] = build_month_calendar(reference_date, monthly_activities)
        context['month_label'] = format_month_label(reference_date)
        context['week_day_labels'] = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
        context['community_groups'] = discoverable_users(self.request.user, role=User.Role.COLLECTIVE)[:6]
        return context


class ActivityReportDashboardView(LoginRequiredMixin, FormView):
    template_name = 'social/activity_report_dashboard.html'
    form_class = ActivityReportForm

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, 'can_report_activities', False):
            messages.error(request, 'A area de relatoria e reservada para usuarios autorizados.')
            return redirect('feed')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['communities'] = report_communities_for(self.request.user)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        communities = report_communities_for(self.request.user)
        reports = ActivityReport.objects.select_related('reporter', 'community', 'post')
        if not getattr(self.request.user, 'can_view_all_content', False):
            reports = reports.filter(
                Q(reporter=self.request.user)
                | Q(community=self.request.user)
                | Q(community__in=Follow.objects.filter(follower=self.request.user).values('following_id'))
            )
        context['available_communities'] = communities
        context['recent_reports'] = reports[:12]
        context['community_total'] = communities.count()
        return context

    def form_valid(self, form):
        if self.request.FILES:
            limited_upload, _ = throttle_request(
                self.request,
                'activity-report-upload',
                settings.UPLOAD_RATE_LIMIT_PER_MINUTE,
                60,
            )
            if limited_upload:
                messages.error(self.request, 'Upload de relatoria temporariamente limitado. Aguarde um minuto.')
                return self.form_invalid(form)

        findings = moderation_findings(
            f'{form.cleaned_data.get("title", "")}\n{form.cleaned_data.get("body", "")}'
        )
        if findings['should_block']:
            record_security_event(
                self.request,
                SecurityEvent.EventType.CONTENT_BLOCKED,
                severity=SecurityEvent.Severity.WARNING,
                user=self.request.user,
                details={'scope': 'activity_report', 'findings': findings},
            )
            messages.error(self.request, 'Relatoria bloqueada por conteudo suspeito ou padrao de spam.')
            return self.form_invalid(form)

        with transaction.atomic():
            report = form.save(commit=False)
            report.reporter = self.request.user
            report.save()
            post = Post.objects.create(
                author=report.community,
                caption=build_activity_report_caption(report),
                media=report.photo.name if report.photo else '',
                visibility=Post.Visibility.COMMUNITY,
                allow_download=False,
                allow_sharing=True,
                age_rating=Post.AgeRating.FREE,
            )
            report.post = post
            report.save(update_fields=['post'])

        messages.success(self.request, f'Relatoria enviada para {report.community.display_name}.')
        return redirect('activity-report-dashboard')


class PostCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if request.FILES:
            limited_upload, _ = throttle_request(
                request,
                'post-upload',
                settings.UPLOAD_RATE_LIMIT_PER_MINUTE,
                60,
            )
            if limited_upload:
                messages.error(request, 'Upload temporariamente limitado. Aguarde um minuto.')
                return redirect('feed')

        limited, _ = throttle_request(
            request,
            'post-create',
            settings.POST_RATE_LIMIT_PER_MINUTE,
            60,
        )
        if limited:
            record_security_event(
                request,
                SecurityEvent.EventType.THROTTLE,
                severity=SecurityEvent.Severity.WARNING,
                user=request.user,
                details={'scope': 'post'},
            )
            messages.error(request, 'Limite de publicacoes atingido. Aguarde um minuto e tente de novo.')
            return redirect('feed')

        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            findings = moderation_findings(form.cleaned_data.get('caption'))
            if findings['should_block']:
                record_security_event(
                    request,
                    SecurityEvent.EventType.CONTENT_BLOCKED,
                    severity=SecurityEvent.Severity.WARNING,
                    user=request.user,
                    details={'scope': 'post', 'findings': findings},
                )
                messages.error(request, 'Publicacao bloqueada por conteudo suspeito ou padrao de spam.')
                return redirect('feed')
            post = form.save(commit=False)
            post.author = request.user
            if request.user.is_minor and post.age_rating == Post.AgeRating.AGE_18:
                messages.error(request, 'Perfis de menores nao podem publicar conteudo marcado como 18+.')
                return redirect('feed')
            post.save()
            messages.success(request, 'Publicacao enviada para a rede.')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('feed')


class ToggleLikeView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        limited, _ = throttle_request(
            request,
            'post-like',
            settings.LIKE_RATE_LIMIT_PER_MINUTE,
            60,
        )
        if limited:
            messages.error(request, 'Curtidas temporariamente limitadas. Aguarde um minuto.')
            return redirect_back(request)

        post = get_object_or_404(visible_posts_for(request.user), pk=pk)
        like, created = PostLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            messages.info(request, 'Curtida removida.')
        else:
            messages.success(request, 'Curtida registrada.')
        return redirect_back(request)


class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        post = get_object_or_404(visible_posts_for(request.user), pk=pk)
        limited, _ = throttle_request(
            request,
            'comment-create',
            settings.COMMENT_RATE_LIMIT_PER_MINUTE,
            60,
        )
        if limited:
            record_security_event(
                request,
                SecurityEvent.EventType.THROTTLE,
                severity=SecurityEvent.Severity.WARNING,
                user=request.user,
                details={'scope': 'comment'},
            )
            messages.error(request, 'Voce comentou rapido demais. Aguarde um minuto.')
            return redirect_back(request)

        body = request.POST.get('body', '').strip()
        if not body:
            messages.error(request, 'Escreva algo para comentar.')
            return redirect_back(request)

        findings = moderation_findings(body)
        if findings['should_block']:
            record_security_event(
                request,
                SecurityEvent.EventType.CONTENT_BLOCKED,
                severity=SecurityEvent.Severity.WARNING,
                user=request.user,
                details={'scope': 'comment', 'findings': findings},
            )
            messages.error(request, 'Comentario bloqueado por conteudo suspeito ou padrao de spam.')
            return redirect_back(request)

        Comment.objects.create(post=post, author=request.user, body=body[:500])
        messages.success(request, 'Comentario publicado.')
        return redirect_back(request)


class FollowToggleView(LoginRequiredMixin, View):
    def post(self, request, handle, *args, **kwargs):
        target = get_object_or_404(User, handle=handle, is_active=True)
        if target == request.user:
            messages.error(request, 'Nao e possivel seguir o proprio perfil.')
            return redirect_back(request)
        if request.user.blocks(target) or target.blocks(request.user):
            messages.error(request, 'Esse perfil esta indisponivel para seguir por regra de privacidade e bloqueio.')
            return redirect_back(request)

        relation = Follow.objects.filter(follower=request.user, following=target).first()
        if relation:
            relation.delete()
            messages.info(request, f'Voce deixou de seguir {target.display_name}.')
        elif target.role == User.Role.COLLECTIVE and target.is_profile_private:
            join_request, created = CommunityJoinRequest.objects.get_or_create(
                requester=request.user,
                community=target,
                status=CommunityJoinRequest.Status.PENDING,
            )
            if created:
                messages.success(request, f'Pedido enviado para entrar em {target.display_name}.')
            else:
                messages.info(request, f'Seu pedido para {target.display_name} ainda esta aguardando aprovacao.')
        else:
            Follow.objects.create(follower=request.user, following=target)
            messages.success(request, f'Agora voce acompanha {target.display_name}.')
        return redirect_back(request)


class CommunityJoinRequestActionView(LoginRequiredMixin, View):
    def post(self, request, pk, action, *args, **kwargs):
        join_request = get_object_or_404(
            CommunityJoinRequest.objects.select_related('requester', 'community'),
            pk=pk,
            status=CommunityJoinRequest.Status.PENDING,
        )
        community = join_request.community
        if not can_manage_community_requests(request.user, community):
            messages.error(request, 'Apenas a comunidade ou a gestao autorizada pode decidir esse pedido.')
            return redirect('profile', handle=community.handle)

        if action == 'aprovar':
            join_request.approve(actor=request.user)
            messages.success(request, f'{join_request.requester.display_name} entrou na comunidade.')
        elif action == 'recusar':
            join_request.reject(actor=request.user)
            messages.info(request, f'Pedido de {join_request.requester.display_name} recusado.')
        else:
            messages.error(request, 'Acao de comunidade nao reconhecida.')
        return redirect('profile', handle=community.handle)
