# Generated manually for stories and feed filters support.

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('social', '0002_communitynotice_groupactivity_weeklytask'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('caption', models.CharField(blank=True, max_length=280)),
                (
                    'media',
                    models.FileField(
                        blank=True,
                        upload_to='stories/%Y/%m/',
                        validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
                    ),
                ),
                (
                    'visibility',
                    models.CharField(
                        choices=[
                            ('public', 'Publico'),
                            ('community', 'Comunidade'),
                            ('followers', 'Seguidores'),
                            ('custom', 'Lista personalizada'),
                        ],
                        default='community',
                        max_length=20,
                    ),
                ),
                (
                    'reply_scope',
                    models.CharField(
                        choices=[
                            ('visible', 'Quem pode ver'),
                            ('followers', 'Seguidores'),
                            ('custom', 'Lista personalizada'),
                            ('none', 'Sem respostas'),
                        ],
                        default='visible',
                        max_length=20,
                    ),
                ),
                (
                    'background_style',
                    models.CharField(
                        choices=[
                            ('forest', 'Mata'),
                            ('sunset', 'Entardecer'),
                            ('soil', 'Terra'),
                            ('sky', 'Ceu'),
                        ],
                        default='forest',
                        max_length=20,
                    ),
                ),
                ('music_label', models.CharField(blank=True, max_length=140)),
                ('music_url', models.URLField(blank=True)),
                ('duration_hours', models.PositiveIntegerField(default=24)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('allowed_responders', models.ManyToManyField(blank=True, related_name='story_reply_permissions', to=settings.AUTH_USER_MODEL)),
                ('allowed_viewers', models.ManyToManyField(blank=True, related_name='story_visibility_permissions', to=settings.AUTH_USER_MODEL)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StoryReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.CharField(max_length=280)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='story_replies', to=settings.AUTH_USER_MODEL)),
                ('story', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='social.story')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='StoryReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('story', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='social.story')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='story_reactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'constraints': [models.UniqueConstraint(fields=('story', 'user'), name='unique_story_reaction_per_user')],
            },
        ),
        migrations.CreateModel(
            name='StoryView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('story', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='views', to='social.story')),
                ('viewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='story_views', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'constraints': [models.UniqueConstraint(fields=('story', 'viewer'), name='unique_story_view_per_user')],
            },
        ),
    ]
