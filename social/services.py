import random

from django.core.files.storage import default_storage
from django.db.models import Case, Count, IntegerField, Q, When
from django.utils import timezone

from accounts.models import User

from .models import Follow, Post, Story


def with_social_totals(queryset):
    return queryset.annotate(
        followers_total=Count('follower_links', distinct=True),
        following_total=Count('following_links', distinct=True),
        posts_total=Count('posts', filter=Q(posts__is_active=True), distinct=True),
    )


def blocked_user_ids(current_user):
    if not getattr(current_user, 'is_authenticated', False):
        return []
    own_blocked_ids = list(current_user.block_entries.values_list('blocked_id', flat=True))
    blocked_by_ids = list(current_user.blocked_entries.values_list('blocker_id', flat=True))
    return list({*own_blocked_ids, *blocked_by_ids})


def discoverable_users(current_user, query='', role=None):
    queryset = User.objects.filter(is_active=True).exclude(pk=current_user.pk)
    hidden_user_ids = [] if getattr(current_user, 'can_view_all_content', False) else blocked_user_ids(current_user)
    if hidden_user_ids:
        queryset = queryset.exclude(pk__in=hidden_user_ids)
    if role:
        queryset = queryset.filter(role=role)
    query = (query or '').strip()
    if query:
        queryset = queryset.filter(
            Q(display_name__icontains=query)
            | Q(handle__icontains=query)
            | Q(username__icontains=query)
            | Q(location__icontains=query)
        )
    return with_social_totals(queryset).order_by('-followers_total', 'display_name', 'username')


def visible_posts_for(user, author=None):
    followed_users = Follow.objects.filter(follower=user).values('following_id')
    queryset = Post.objects.filter(is_active=True)
    if getattr(user, 'can_view_all_content', False):
        if author is not None:
            queryset = queryset.filter(author=author)
        return queryset.select_related('author').annotate(
            likes_total=Count('likes', distinct=True),
            comments_total=Count('comments', distinct=True),
        )

    hidden_user_ids = blocked_user_ids(user)
    if hidden_user_ids:
        queryset = queryset.exclude(author_id__in=hidden_user_ids)
    if getattr(user, 'age', None) is None or user.age < 18:
        queryset = queryset.exclude(age_rating=Post.AgeRating.AGE_18)

    queryset = queryset.filter(
        Q(author=user)
        | Q(visibility=Post.Visibility.PRIVATE, author=user)
        | Q(visibility=Post.Visibility.FOLLOWERS, author__in=followed_users)
        | (
            Q(author__is_profile_private=False)
            & Q(visibility__in=[Post.Visibility.PUBLIC, Post.Visibility.COMMUNITY])
        )
    )
    if author is not None:
        queryset = queryset.filter(author=author)
    return queryset.select_related('author').annotate(
        likes_total=Count('likes', distinct=True),
        comments_total=Count('comments', distinct=True),
    )


def ordered_posts_for(user, filter_mode='latest', author=None):
    queryset = visible_posts_for(user, author=author)
    following_ids = Follow.objects.filter(follower=user).values('following_id')
    follower_ids = Follow.objects.filter(following=user).values('follower_id')

    if filter_mode == 'liked':
        return queryset.order_by('-likes_total', '-created_at')
    if filter_mode == 'commented':
        return queryset.order_by('-comments_total', '-created_at')
    if filter_mode == 'followers':
        return queryset.filter(Q(author__in=following_ids) | Q(author__in=follower_ids)).order_by('-created_at')
    if filter_mode == 'random':
        post_ids = list(queryset.values_list('pk', flat=True))
        random.shuffle(post_ids)
        if not post_ids:
            return queryset.none()
        preserved = Case(*[When(pk=pk, then=position) for position, pk in enumerate(post_ids)], output_field=IntegerField())
        return queryset.filter(pk__in=post_ids).order_by(preserved)
    return queryset.order_by('-created_at')


def cleanup_expired_stories():
    expired_stories = Story.objects.filter(is_active=True, expires_at__isnull=False, expires_at__lte=timezone.now())
    for story in expired_stories:
        if story.media:
            storage = story.media.storage or default_storage
            if storage.exists(story.media.name):
                storage.delete(story.media.name)
        story.is_active = False
        story.save(update_fields=['is_active'])


def visible_stories_for(user):
    cleanup_expired_stories()
    queryset = Story.objects.filter(is_active=True, expires_at__gt=timezone.now()).select_related('author').annotate(
        views_total=Count('views', distinct=True),
        reactions_total=Count('reactions', distinct=True),
        replies_total=Count('replies', distinct=True),
    )
    if not user.is_authenticated:
        return queryset.none()
    if getattr(user, 'can_view_all_content', False):
        return queryset.distinct().order_by('-created_at')

    hidden_user_ids = blocked_user_ids(user)
    if hidden_user_ids:
        queryset = queryset.exclude(author_id__in=hidden_user_ids)
    if getattr(user, 'age', None) is None or user.age < 18:
        queryset = queryset.exclude(age_rating=Story.AgeRating.AGE_18)

    return queryset.filter(
        Q(author=user)
        | Q(visibility=Story.Visibility.PRIVATE, author=user)
        | Q(visibility=Story.Visibility.CUSTOM, allowed_viewers=user)
        | Q(visibility=Story.Visibility.FOLLOWERS, author__follower_links__follower=user)
        | (
            Q(author__is_profile_private=False)
            & Q(visibility__in=[Story.Visibility.PUBLIC, Story.Visibility.COMMUNITY])
        )
    ).distinct().order_by('-created_at')


def is_following(user, target):
    if not user.is_authenticated or user.pk == target.pk or user.blocks(target) or target.blocks(user):
        return False
    return Follow.objects.filter(follower=user, following=target).exists()
