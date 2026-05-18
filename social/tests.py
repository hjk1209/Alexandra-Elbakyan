from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import CommunityNotice, Follow, GroupActivity, Post, PostLike, Story, StoryReply


class FeedTests(TestCase):
    password = 'SenhaSegura!2026'

    def setUp(self):
        self.author = User.objects.create_user(
            username='autor',
            display_name='Autor',
            handle='autor',
            email='autor@example.com',
            birth_date='1999-01-01',
            password=self.password,
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            display_name='Viewer',
            handle='viewer',
            email='viewer@example.com',
            birth_date='2000-01-01',
            password=self.password,
        )
        self.collective = User.objects.create_user(
            username='brigada',
            display_name='Brigada Popular',
            handle='brigada_popular',
            email='brigada@example.com',
            role=User.Role.COLLECTIVE,
            birth_date='1998-01-01',
            password=self.password,
        )
        self.outsider = User.objects.create_user(
            username='outsider',
            display_name='Fora da Lista',
            handle='fora_lista',
            email='outsider@example.com',
            birth_date='2002-01-01',
            password=self.password,
        )
        self.minor = User.objects.create_user(
            username='menor',
            display_name='Menor',
            handle='menor',
            email='menor@example.com',
            birth_date=str(timezone.localdate().replace(year=timezone.localdate().year - 16)),
            password=self.password,
        )

    def _force_login(self, user):
        self.client.force_login(user)

    def test_authenticated_user_can_post(self):
        self._force_login(self.viewer)
        response = self.client.post(
            reverse('post-create'),
            {
                'caption': 'Primeira publicacao da juventude',
                'visibility': Post.Visibility.PUBLIC,
                'allow_download': '',
                'allow_sharing': 'on',
                'age_rating': Post.AgeRating.FREE,
            },
        )
        self.assertRedirects(response, reverse('feed'))
        self.assertTrue(Post.objects.filter(author=self.viewer).exists())

    def test_followers_post_hidden_until_follow(self):
        self.author.is_profile_private = True
        self.author.save(update_fields=['is_profile_private'])
        Post.objects.create(
            author=self.author,
            caption='Planejamento secreto da brigada',
            visibility=Post.Visibility.FOLLOWERS,
        )
        self._force_login(self.viewer)
        response = self.client.get(reverse('feed'))
        self.assertNotContains(response, 'Planejamento secreto da brigada')

        Follow.objects.create(follower=self.viewer, following=self.author)
        response = self.client.get(reverse('feed'))
        self.assertContains(response, 'Planejamento secreto da brigada')

    def test_admin_can_see_private_and_restricted_content(self):
        admin = User.objects.create_user(
            username='adm',
            display_name='Administrador',
            handle='adm',
            email='adm@example.com',
            role=User.Role.ADMIN,
            birth_date='1990-01-01',
            password=self.password,
        )
        self.author.is_profile_private = True
        self.author.save(update_fields=['is_profile_private'])
        Post.objects.create(
            author=self.author,
            caption='Post privado para auditoria',
            visibility=Post.Visibility.PRIVATE,
        )
        story = Story.objects.create(
            author=self.author,
            caption='Story restrito para auditoria',
            visibility=Story.Visibility.CUSTOM,
            reply_scope=Story.ReplyScope.NONE,
            duration_hours=12,
        )
        story.allowed_viewers.add(self.viewer)

        self._force_login(admin)
        response = self.client.get(reverse('feed'))
        self.assertContains(response, 'Post privado para auditoria')
        response = self.client.get(reverse('profile', args=[self.author.handle]))
        self.assertContains(response, 'Autor')
        response = self.client.get(reverse('story-detail', args=[story.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Story restrito para auditoria')

    def test_people_directory_filters_by_query(self):
        self._force_login(self.viewer)
        response = self.client.get(reverse('people-directory'), {'q': 'Brigada'})
        self.assertContains(response, 'Brigada Popular')
        self.assertNotContains(response, 'Autor')

    def test_community_directory_lists_collective_profiles(self):
        self._force_login(self.viewer)
        response = self.client.get(reverse('community-directory'))
        self.assertContains(response, 'Brigada Popular')
        self.assertNotContains(response, 'Autor')

    def test_community_hub_shows_notice_and_month_activity(self):
        CommunityNotice.objects.create(
            title='Assembleia da comunidade',
            body='Toda a base deve confirmar presenca.',
            author=self.collective,
        )
        GroupActivity.objects.create(
            title='Mutirao do grupo',
            description='Atividade principal do mes.',
            activity_date=timezone.localdate(),
            community=self.collective,
            created_by=self.collective,
        )
        self._force_login(self.viewer)
        response = self.client.get(reverse('community-hub'))
        self.assertContains(response, 'Assembleia da comunidade')
        self.assertContains(response, 'Mutirao do grupo')

    def test_custom_story_only_allowed_viewer_can_open(self):
        story = Story.objects.create(
            author=self.author,
            caption='Convocacao restrita',
            visibility=Story.Visibility.CUSTOM,
            reply_scope=Story.ReplyScope.NONE,
            duration_hours=12,
        )
        story.allowed_viewers.add(self.viewer)

        self._force_login(self.viewer)
        response = self.client.get(reverse('story-detail', args=[story.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Convocacao restrita')

        self._force_login(self.outsider)
        response = self.client.get(reverse('story-detail', args=[story.pk]))
        self.assertEqual(response.status_code, 404)

    def test_story_reply_respects_custom_list(self):
        story = Story.objects.create(
            author=self.author,
            caption='Resposta so para a equipe',
            visibility=Story.Visibility.COMMUNITY,
            reply_scope=Story.ReplyScope.CUSTOM,
            duration_hours=24,
        )
        story.allowed_responders.add(self.viewer)

        self._force_login(self.viewer)
        response = self.client.post(reverse('story-reply', args=[story.pk]), {'body': 'Estou dentro'})
        self.assertRedirects(response, reverse('story-detail', args=[story.pk]))
        self.assertTrue(StoryReply.objects.filter(story=story, author=self.viewer, body='Estou dentro').exists())

        self._force_login(self.outsider)
        response = self.client.post(reverse('story-reply', args=[story.pk]), {'body': 'Quero entrar'})
        self.assertRedirects(response, reverse('story-detail', args=[story.pk]))
        self.assertFalse(StoryReply.objects.filter(story=story, author=self.outsider).exists())

    def test_minor_cannot_see_or_publish_age_18_content(self):
        adult_post = Post.objects.create(
            author=self.author,
            caption='Conteudo adulto protegido',
            visibility=Post.Visibility.PUBLIC,
            age_rating=Post.AgeRating.AGE_18,
        )
        self._force_login(self.minor)
        response = self.client.get(reverse('feed'))
        self.assertNotContains(response, adult_post.caption)

        response = self.client.post(
            reverse('post-create'),
            {
                'caption': 'Tentativa inadequada',
                'visibility': Post.Visibility.PUBLIC,
                'allow_download': '',
                'allow_sharing': 'on',
                'age_rating': Post.AgeRating.AGE_18,
            },
        )
        self.assertRedirects(response, reverse('feed'))
        self.assertFalse(Post.objects.filter(author=self.minor, caption='Tentativa inadequada').exists())

    def test_feed_filter_orders_by_most_liked(self):
        post_recent = Post.objects.create(
            author=self.author,
            caption='Recente da base',
            visibility=Post.Visibility.PUBLIC,
        )
        post_popular = Post.objects.create(
            author=self.collective,
            caption='Popular na rede',
            visibility=Post.Visibility.PUBLIC,
        )
        PostLike.objects.create(post=post_popular, user=self.viewer)
        PostLike.objects.create(post=post_popular, user=self.outsider)
        PostLike.objects.create(post=post_recent, user=self.collective)

        self._force_login(self.viewer)
        response = self.client.get(reverse('feed'), {'filter': 'liked'})
        content = response.content.decode('utf-8')
        self.assertLess(content.index('Popular na rede'), content.index('Recente da base'))

    def test_feed_filter_followers_limits_to_connected_network(self):
        Follow.objects.create(follower=self.viewer, following=self.author)
        Post.objects.create(
            author=self.author,
            caption='Post da minha rede',
            visibility=Post.Visibility.PUBLIC,
        )
        Post.objects.create(
            author=self.outsider,
            caption='Post de fora',
            visibility=Post.Visibility.PUBLIC,
        )

        self._force_login(self.viewer)
        response = self.client.get(reverse('feed'), {'filter': 'followers'})
        self.assertContains(response, 'Post da minha rede')
        self.assertNotContains(response, 'Post de fora')

    def test_protected_post_media_requires_allowed_viewer(self):
        post = Post.objects.create(
            author=self.author,
            caption='Midia privada',
            visibility=Post.Visibility.FOLLOWERS,
            allow_download=True,
            media=SimpleUploadedFile('post.jpg', b'file-content', content_type='image/jpeg'),
        )
        self._force_login(self.viewer)
        response = self.client.get(post.media_view_url)
        self.assertEqual(response.status_code, 404)

        Follow.objects.create(follower=self.viewer, following=self.author)
        response = self.client.get(post.media_view_url)
        self.assertEqual(response.status_code, 200)


class PostModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            handle='testuser',
            display_name='Test User',
            email='test@example.com',
            birth_date='2000-01-01',
            password='testpass123',
        )

    def test_post_soft_delete_with_active_manager(self):
        post = Post.objects.create(author=self.user, caption='Test')
        post.is_active = False
        post.save()
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(Post.all_objects.count(), 1)

    def test_post_ordering_by_created_at(self):
        post1 = Post.objects.create(author=self.user, caption='First')
        post2 = Post.objects.create(author=self.user, caption='Second')
        self.assertEqual(list(Post.objects.values_list('caption', flat=True)), ['Second', 'First'])


class StoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            handle='testuser',
            display_name='Test User',
            email='test@example.com',
            birth_date='2000-01-01',
            password='testpass123',
        )

    def test_story_soft_delete(self):
        story = Story.objects.create(author=self.user, caption='Test')
        story.is_active = False
        story.save()
        self.assertEqual(Story.objects.count(), 0)
        self.assertEqual(Story.all_objects.count(), 1)

    def test_story_expiration_check(self):
        from django.utils import timezone
        story = Story.objects.create(
            author=self.user,
            caption='Expiring story',
            duration_hours=1,
        )
        self.assertFalse(story.is_expired)
        story.expires_at = timezone.now()
        story.save()
        self.assertTrue(story.is_expired)

