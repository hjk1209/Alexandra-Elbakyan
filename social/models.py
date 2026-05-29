from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from core.security import build_protected_media_url


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Post(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Publico'
        COMMUNITY = 'community', 'Comunidade'
        FOLLOWERS = 'followers', 'Amigos e seguidores'
        PRIVATE = 'private', 'Privado'

    class AgeRating(models.TextChoices):
        FREE = 'free', 'Livre'
        AGE_12 = '12', '12'
        AGE_14 = '14', '14'
        AGE_16 = '16', '16'
        AGE_18 = '18', '18'

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts', db_index=True)
    caption = models.TextField(max_length=2200, blank=True)
    media = models.FileField(
        upload_to='posts/%Y/%m/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.COMMUNITY, db_index=True)
    allow_download = models.BooleanField(default=False)
    allow_sharing = models.BooleanField(default=True)
    age_rating = models.CharField(max_length=8, choices=AgeRating.choices, default=AgeRating.FREE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    objects = ActiveManager()
    all_objects = models.Manager()

    def clean(self):
        if not self.caption and not self.media:
            raise ValidationError('Escreva algo ou envie uma imagem para publicar.')

    def __str__(self):
        return f'{self.author} - {self.created_at:%d/%m/%Y %H:%M}'

    @property
    def media_view_url(self):
        if not self.media:
            return ''
        return build_protected_media_url('post', self.pk, action='view')

    @property
    def media_download_url(self):
        if not self.media or not self.allow_download:
            return ''
        return build_protected_media_url('post', self.pk, action='download')

    @property
    def minimum_age(self):
        if self.age_rating == self.AgeRating.FREE:
            return 0
        return int(self.age_rating)


class Story(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Publico'
        COMMUNITY = 'community', 'Comunidade'
        FOLLOWERS = 'followers', 'Amigos e seguidores'
        PRIVATE = 'private', 'Privado'
        CUSTOM = 'custom', 'Lista personalizada'

    class ReplyScope(models.TextChoices):
        VISIBLE = 'visible', 'Quem pode ver'
        FOLLOWERS = 'followers', 'Seguidores'
        CUSTOM = 'custom', 'Lista personalizada'
        NONE = 'none', 'Sem respostas'

    class BackgroundStyle(models.TextChoices):
        FOREST = 'forest', 'Mata'
        SUNSET = 'sunset', 'Entardecer'
        SOIL = 'soil', 'Terra'
        SKY = 'sky', 'Ceu'

    class AgeRating(models.TextChoices):
        FREE = 'free', 'Livre'
        AGE_12 = '12', '12'
        AGE_14 = '14', '14'
        AGE_16 = '16', '16'
        AGE_18 = '18', '18'

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stories', db_index=True)
    caption = models.CharField(max_length=280, blank=True)
    media = models.FileField(
        upload_to='stories/%Y/%m/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.COMMUNITY, db_index=True)
    reply_scope = models.CharField(max_length=20, choices=ReplyScope.choices, default=ReplyScope.VISIBLE)
    background_style = models.CharField(
        max_length=20,
        choices=BackgroundStyle.choices,
        default=BackgroundStyle.FOREST,
    )
    allow_download = models.BooleanField(default=False)
    music_label = models.CharField(max_length=140, blank=True)
    music_url = models.URLField(blank=True)
    age_rating = models.CharField(max_length=8, choices=AgeRating.choices, default=AgeRating.FREE)
    duration_hours = models.PositiveIntegerField(default=24)
    expires_at = models.DateTimeField(blank=True, null=True, db_index=True)
    allowed_viewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='story_visibility_permissions',
    )
    allowed_responders = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='story_reply_permissions',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    objects = ActiveManager()
    all_objects = models.Manager()

    def clean(self):
        if not self.caption and not self.media:
            raise ValidationError('Escreva algo ou envie uma imagem para montar o story.')
        if self.duration_hours < 1 or self.duration_hours > 168:
            raise ValidationError('Defina uma duracao entre 1 e 168 horas para o story.')

    def save(self, *args, **kwargs):
        if self._state.adding or not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=self.duration_hours)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Story de {self.author} em {self.created_at:%d/%m/%Y %H:%M}'

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def media_view_url(self):
        if not self.media:
            return ''
        return build_protected_media_url('story', self.pk, action='view')

    @property
    def media_download_url(self):
        if not self.media or not self.allow_download:
            return ''
        return build_protected_media_url('story', self.pk, action='download')

    @property
    def minimum_age(self):
        if self.age_rating == self.AgeRating.FREE:
            return 0
        return int(self.age_rating)

    def can_reply(self, user):
        if not getattr(user, 'is_authenticated', False) or user.pk == self.author_id or not self.is_active or self.is_expired:
            return False
        if not self.is_visible_to(user):
            return False
        if self.reply_scope == self.ReplyScope.NONE:
            return False
        if self.reply_scope == self.ReplyScope.VISIBLE:
            return True
        if self.reply_scope == self.ReplyScope.FOLLOWERS:
            return self.author.follower_links.filter(follower=user).exists()
        return self.allowed_responders.filter(pk=user.pk).exists()

    def is_visible_to(self, user):
        if not getattr(user, 'is_authenticated', False) or not self.is_active or self.is_expired:
            return False
        if user.pk == self.author_id:
            return True
        if self.author.blocks(user) or user.blocks(self.author):
            return False
        viewer_age = getattr(user, 'age', None)
        if self.minimum_age >= 18 and (viewer_age is None or viewer_age < 18):
            return False
        if self.visibility == self.Visibility.PRIVATE:
            return False
        if self.visibility == self.Visibility.CUSTOM:
            return self.allowed_viewers.filter(pk=user.pk).exists()
        if self.visibility == self.Visibility.COMMUNITY and self.author.role == 'collective':
            return self.author.follower_links.filter(follower=user).exists()
        if self.visibility == self.Visibility.FOLLOWERS:
            return self.author.follower_links.filter(follower=user).exists()
        if self.author.is_profile_private:
            return self.author.follower_links.filter(follower=user).exists()
        return True


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='story_views')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['story', 'viewer'], name='unique_story_view_per_user'),
        ]

    def __str__(self):
        return f'{self.viewer} viu story #{self.story_id}'


class StoryReaction(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='story_reactions')
    emoji = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['story', 'user'], name='unique_story_reaction_per_user'),
        ]

    def __str__(self):
        return f'{self.user} reagiu ao story #{self.story_id}'


class StoryReply(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='story_replies')
    body = models.CharField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author}: {self.body[:40]}'


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author}: {self.body[:32]}'


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='liked_posts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_like_per_post'),
        ]

    def __str__(self):
        return f'{self.user} curtiu #{self.post_id}'


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following_links',
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower_links',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_follow_relationship'),
            models.CheckConstraint(condition=~Q(follower=F('following')), name='follow_cannot_target_self'),
        ]

    def __str__(self):
        return f'{self.follower} segue {self.following}'


class CommunityJoinRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        APPROVED = 'approved', 'Aprovada'
        REJECTED = 'rejected', 'Recusada'

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='community_join_requests',
    )
    community = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='community_join_requests_received',
        limit_choices_to={'role': 'collective'},
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='decided_community_join_requests',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['requester', 'community'],
                condition=Q(status='pending'),
                name='unique_pending_community_join_request',
            ),
            models.CheckConstraint(condition=~Q(requester=F('community')), name='community_join_cannot_target_self'),
        ]

    def approve(self, actor=None):
        Follow.objects.get_or_create(follower=self.requester, following=self.community)
        self.status = self.Status.APPROVED
        self.decided_by = actor
        self.decided_at = timezone.now()
        self.save(update_fields=['status', 'decided_by', 'decided_at'])

    def reject(self, actor=None):
        self.status = self.Status.REJECTED
        self.decided_by = actor
        self.decided_at = timezone.now()
        self.save(update_fields=['status', 'decided_by', 'decided_at'])

    def __str__(self):
        return f'{self.requester} -> {self.community} ({self.get_status_display()})'


class ActivityReport(models.Model):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_reports',
    )
    community = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_activity_reports',
        limit_choices_to={'role': 'collective'},
    )
    post = models.OneToOneField(
        Post,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activity_report',
    )
    title = models.CharField(max_length=160)
    activity_date = models.DateField(default=timezone.localdate)
    body = models.TextField(max_length=5000)
    photo = models.FileField(
        upload_to='relatoria/fotos/%Y/%m/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    attachment = models.FileField(
        upload_to='relatoria/arquivos/%Y/%m/',
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'odt', 'ods', 'txt', 'csv'])],
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-created_at']

    def clean(self):
        if getattr(self.community, 'role', None) != 'collective':
            raise ValidationError('A relatoria precisa ser enviada para uma comunidade/NB.')
        if not self.body.strip():
            raise ValidationError('Escreva o texto da atividade antes de salvar a relatoria.')

    def is_visible_to(self, user):
        if not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'can_view_all_content', False):
            return True
        if user.pk in {self.reporter_id, self.community_id}:
            return True
        if self.community.blocks(user) or user.blocks(self.community):
            return False
        return Follow.objects.filter(follower=user, following=self.community).exists()

    @property
    def photo_view_url(self):
        if not self.photo:
            return ''
        return build_protected_media_url('activity-report-photo', self.pk, action='view')

    @property
    def attachment_download_url(self):
        if not self.attachment:
            return ''
        return build_protected_media_url('activity-report-file', self.pk, action='download')

    def __str__(self):
        return f'{self.title} - {self.community} ({self.activity_date:%d/%m/%Y})'


class CommunityNotice(models.Model):
    community = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='community_notices',
        limit_choices_to={'role': 'collective'},
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='authored_community_notices',
    )
    title = models.CharField(max_length=140)
    body = models.TextField(max_length=1200)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


class GroupActivity(models.Model):
    community = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='group_activities',
        limit_choices_to={'role': 'collective'},
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_group_activities',
    )
    title = models.CharField(max_length=140)
    description = models.TextField(max_length=1200, blank=True)
    activity_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ['activity_date', 'start_time', 'title']

    def __str__(self):
        return f'{self.title} ({self.activity_date:%d/%m/%Y})'


class WeeklyTask(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        IN_PROGRESS = 'in_progress', 'Em andamento'
        DONE = 'done', 'Concluida'

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weekly_tasks',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_weekly_tasks',
    )
    title = models.CharField(max_length=140)
    description = models.TextField(max_length=600, blank=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ['due_date', 'status', 'title']

    def __str__(self):
        return f'{self.assignee} - {self.title}'

# Create your models here.
