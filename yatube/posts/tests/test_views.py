import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Group, Post, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

TEST_OF_POST: int = 13


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.no_follow_user = User.objects.create_user(username='biba')
        cls.follow_user = User.objects.create_user(username='boba')
        cls.follower = Follow.objects.create(
            user=cls.follow_user, author=cls.user)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.follower_client = Client()
        self.follower_client.force_login(self.follow_user)
        self.no_follower_client = Client()
        self.no_follower_client.force_login(self.no_follow_user)
        self.group = Group.objects.create(title='Тестовая группа',
                                          slug='test_group')
        self.post = Post.objects.create(text='Тестовый текст',
                                        group=self.group,
                                        author=self.user)

    def check_post_info(self, post):
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)
            self.assertEqual(post.image, self.post.image)

    def test_views_correct_template(self):
        '''Проверка,что URL-адрес использует соответствующий шаблон.'''
        templates_url_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug':
                            f'{self.group.slug}'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username':
                            f'{self.user.username}'}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id':
                            self.post.id}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit',
                    kwargs={'post_id':
                            self.post.id}): 'posts/post_create.html'}
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                error = f'Ошибка: {url} ожидал шаблон {template}'
                self.assertTemplateUsed(response, template, error)

    def test_forms_show_correct(self):
        """"Шаблон post_create.html сформирован с правильным контекстом."""
        urls = [reverse('posts:post_create'),
                reverse('posts:post_edit', kwargs={'post_id': self.post.id})]
        for url in urls:
            response = self.authorized_client.get(url)
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
                'image': forms.fields.ImageField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_index_page_show_correct_context(self):
        """Шаблон index.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post_info(response.context['page_obj'][0])

    def test_groups_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['group'], self.group)
        self.check_post_info(response.context['page_obj'][0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}))
        self.assertEqual(response.context['user'], self.user)
        self.check_post_info(response.context['page_obj'][0])

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}))
        post_text = {response.context['post'].text: 'Тестовый пост',
                     response.context['post'].group: self.group,
                     response.context['post'].author: PostPagesTests.user
                     }
        for value, expected in post_text.items():
            self.assertEqual(post_text[value], expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на страницах с выбранной группой"""
        form_fields = {
            reverse("posts:index"): Post.objects.get(group=self.post.group),
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                "posts:profile", kwargs={"username": self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем чтобы созданный Пост с группой не попал в чужую группу."""
        form_fields = {
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertNotIn(expected, form_field)

    def test_add_comment(self):
        """Авторизированный пользователь может оставить коментарий"""

        comments = {'text': 'тестовый комментарий'}
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=comments, follow=True
        )
        response = self.authorized_client.get(f'/posts/{self.post.id}/')
        self.assertContains(response, comments['text'])

    def test_anonym_cannot_add_comments(self):
        """НЕ Авторизированный пользователь не может оставить коментарий"""
        comments = {'text': 'комент не пройдет'}
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=comments, follow=True
        )
        response = self.guest_client.get(f'/posts/{self.post.id}/')
        self.assertNotContains(response, comments['text'])

    def test_cache_index(self):
        """Проверка хранения и очищения кэша для index."""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            text='новейший пост',
            author=self.post.author,
        )
        response_old = self.authorized_client.get(reverse('posts:index'))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertNotEqual(old_posts, new_posts)

    def test_follow_index_show_cont(self):
        """Шаблон follow сформирован с правильным контекстом."""
        response = self.follower_client.get(reverse('posts:follow_index'))
        count_post_follower = len(response.context['page_obj'])
        response = self.no_follower_client.get(reverse('posts:follow_index'))
        count_post_no_follower = len(response.context['page_obj'])
        Post.objects.create(
            author=self.user,
            text='Новый тестовый пост',
            group=self.group,
        )
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertEqual(
            len(response.context['page_obj']), count_post_follower + 1)
        response = self.no_follower_client.get(reverse('posts:follow_index'))
        self.assertEqual(
            len(response.context['page_obj']), count_post_no_follower)

    def test_user_follow(self):
        """Проверка на создание подписчика."""
        response = self.no_follower_client.get(reverse('posts:follow_index'))
        count_post_follower = len(response.context['page_obj'])
        response = self.no_follower_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user}))
        response = self.no_follower_client.get(reverse('posts:follow_index'))
        self.assertFalse(count_post_follower)
        self.assertTrue(len(response.context['page_obj']))

    def test_follower_delete_to_user(self):
        """Проверка на удаление подписчика."""
        response = self.follower_client.get(reverse('posts:follow_index'))
        count_post_follower = len(response.context['page_obj'])
        response = self.follower_client.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.user}))
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertTrue(count_post_follower)
        self.assertFalse(len(response.context['page_obj']))


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='auth',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        for i in range(13):
            Post.objects.create(
                text=f'Пост #{i}',
                author=cls.user,
                group=cls.group
            )

    def setUp(self):
        self.unauthorized_client = Client()

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        posts_on_first_page = 10
        posts_on_second_page = 3
        url_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for reverse_ in url_pages:
            with self.subTest(reverse_=reverse_):
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_).context.get('page_obj')),
                    posts_on_first_page
                )
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_ + '?page=2').context.get('page_obj')),
                    posts_on_second_page
                )
