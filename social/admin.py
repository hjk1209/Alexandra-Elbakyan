from django.contrib import admin

from .models import (
    CommunityNotice,
    Comment,
    Follow,
    GroupActivity,
    Post,
    PostLike,
    Story,
    StoryReaction,
    StoryReply,
    StoryView,
    WeeklyTask,
)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'visibility', 'age_rating', 'allow_download', 'allow_sharing', 'created_at', 'is_active')
    list_filter = ('visibility', 'age_rating', 'allow_download', 'allow_sharing', 'is_active', 'created_at')
    search_fields = ('author__username', 'author__handle', 'author__display_name', 'caption')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    search_fields = ('author__username', 'author__handle', 'body')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')


@admin.register(CommunityNotice)
class CommunityNoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'community', 'author', 'is_pinned', 'created_at')
    list_filter = ('is_pinned', 'created_at', 'community')
    search_fields = ('title', 'body', 'community__display_name', 'author__display_name')


@admin.register(GroupActivity)
class GroupActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'community', 'activity_date', 'start_time', 'location')
    list_filter = ('activity_date', 'community')
    search_fields = ('title', 'description', 'location', 'community__display_name')


@admin.register(WeeklyTask)
class WeeklyTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assignee', 'due_date', 'status', 'created_by')
    list_filter = ('status', 'due_date')
    search_fields = ('title', 'description', 'assignee__display_name', 'assignee__handle', 'assignee__username')


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('author', 'visibility', 'reply_scope', 'age_rating', 'allow_download', 'duration_hours', 'expires_at', 'is_active')
    list_filter = ('visibility', 'reply_scope', 'age_rating', 'allow_download', 'background_style', 'is_active', 'created_at')
    search_fields = ('author__display_name', 'author__handle', 'author__username', 'caption', 'music_label')
    filter_horizontal = ('allowed_viewers', 'allowed_responders')


@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ('story', 'viewer', 'created_at')
    search_fields = ('story__author__display_name', 'viewer__display_name')


@admin.register(StoryReaction)
class StoryReactionAdmin(admin.ModelAdmin):
    list_display = ('story', 'user', 'emoji', 'created_at')
    search_fields = ('story__author__display_name', 'user__display_name', 'emoji')


@admin.register(StoryReply)
class StoryReplyAdmin(admin.ModelAdmin):
    list_display = ('story', 'author', 'created_at')
    search_fields = ('story__author__display_name', 'author__display_name', 'body')
