from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from ..models import Post, Group

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )

        cls.user_author = User.objects.create_user(
            username='user_author')
        cls.another_user = User.objects.create_user(
            username='another_user')

        cls.post = Post.objects.create(
            author=cls.user_author,
            group=cls.group,
            text='Теcстовый пост более 15 символов.',
        )
        cls.public_urls = {
            "/": "posts/index.html",
            f"/group/{cls.group.slug}/": "posts/group_list.html",
            f"/profile/{cls.another_user.username}/": "posts/profile.html",
            f"/posts/{cls.post.id}/": "posts/post_detail.html",
        }
        cls.private_urls = {
            "/create/": "posts/post_create.html"
        }
        cls.author_urls = {
            f'/posts/{cls.post.id}/edit/': 'posts/post_create.html',
        }
        cls.urls_for_login_client = {**cls.public_urls, **cls.private_urls}
        cls.urls_not_for_guest = {**cls.private_urls, **cls.author_urls}
        cls.urls = {**cls.public_urls, **cls.private_urls, **cls.author_urls}

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.post_author = Client()
        self.post_author.force_login(self.user_author)
        self.authorized_user = Client()
        self.authorized_user.force_login(self.another_user)

    def test_guest_urls(self):
        """Проверка status_code для гостя."""
        for url in self.public_urls.keys():
            with self.subTest(url=url):
                status_code = self.guest_client.get(url).status_code
                self.assertEqual(status_code, HTTPStatus.OK)

    def test_authorized_user_urls_status_code(self):
        """Проверка status_code для авторизованного пользователя."""
        for url in self.private_urls.keys():
            with self.subTest(url=url):
                status_code = self.authorized_user.get(url).status_code
                self.assertEqual(status_code, HTTPStatus.OK)

    def test_author_user_urls_status_code(self):
        """Проверка status_code для автора поста."""
        for url in self.urls_not_for_guest.keys():
            with self.subTest(url=url):
                status_code = self.post_author.get(url).status_code
                self.assertEqual(status_code, HTTPStatus.OK)

    def test_urls(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in self.urls.items():
            with self.subTest(url=url):
                response = self.post_author.get(url)
                self.assertTemplateUsed(response, template)

    def test_create_url_redirect_guest(self):
        """Страница /create/ перенаправляет неавторизованного клиента
        на страницу авторизации."""
        response = self.guest_client.get('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit_url_redirect_guest(self):
        """Страница posts/post_id/edit/ перенаправляет
         неавторизованного клиента на страницу авторизации."""
        response = self.guest_client.get(f'/posts/{self.post.id}/edit/')
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.id}/edit/')

    def test_wrong_uri_returns_404(self):
        """Запрос к несуществующей странице вернёт ошибку 404."""
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
