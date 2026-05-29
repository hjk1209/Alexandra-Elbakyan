from django.urls import path

from .views import (
    ActivityReportDashboardView,
    CommentCreateView,
    CommunityDirectoryView,
    CommunityHubView,
    CommunityJoinRequestActionView,
    FeedView,
    FollowToggleView,
    PeopleDirectoryView,
    PostCreateView,
    StoryDetailView,
    StoryEditorView,
    StoryReactionToggleView,
    StoryReplyCreateView,
    ToggleLikeView,
)

urlpatterns = [
    path('', FeedView.as_view(), name='feed'),
    path('stories/editor/', StoryEditorView.as_view(), name='story-editor'),
    path('stories/<int:pk>/', StoryDetailView.as_view(), name='story-detail'),
    path('stories/<int:pk>/reagir/', StoryReactionToggleView.as_view(), name='story-react'),
    path('stories/<int:pk>/responder/', StoryReplyCreateView.as_view(), name='story-reply'),
    path('pessoas/', PeopleDirectoryView.as_view(), name='people-directory'),
    path('comunidades/', CommunityDirectoryView.as_view(), name='community-directory'),
    path('comunidades/geral/', CommunityHubView.as_view(), name='community-hub'),
    path('comunidades/solicitacoes/<int:pk>/<slug:action>/', CommunityJoinRequestActionView.as_view(), name='community-join-action'),
    path('relatoria/', ActivityReportDashboardView.as_view(), name='activity-report-dashboard'),
    path('publicar/', PostCreateView.as_view(), name='post-create'),
    path('curtir/<int:pk>/', ToggleLikeView.as_view(), name='post-like'),
    path('comentar/<int:pk>/', CommentCreateView.as_view(), name='post-comment'),
    path('seguir/<slug:handle>/', FollowToggleView.as_view(), name='follow-toggle'),
]
