import shutil
import tempfile

from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, Comment
from ..forms import PostForm

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title="Тестовое название группы",
            slug="test_slug",
            description="Тестовое описание группы",
        )
        cls.post = Post.objects.create(
            text='Тестовый текст более 15 символов',
            author=cls.post_author,
            group=cls.group,
        )
        cls.form = PostForm()

    def setUp(self):
        self.guest_user = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.post_author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_create_authorized_client(self):
        """Создается новая запись в базе данных."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Данные из формы',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.post_author.username}))
        self.assertTrue(
            Post.objects.filter(
                group=self.group.pk,
                text='Данные из формы',
                image='posts/small.gif'
            ).exists()
        )

    def test_authorized_user_create_post(self):
        """Проверка создания записи авторизированным клиентом."""
        posts_count = Post.objects.count()
        form_data = {"text": "Текст поста", "group": self.group.id}
        response = self.authorized_user.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                "posts:profile", kwargs={"username": self.post_author.username}
            ),
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest("id")
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(post.author, self.post_author)
        self.assertEqual(post.group_id, form_data["group"])

    def test_authorized_user_edit_post(self):
        """Проверка редактирования записи авторизированным клиентом."""
        post = Post.objects.create(
            text="Текст поста для редактирования",
            author=self.post_author,
            group=self.group,
        )
        form_data = {
            "text": "Отредактированный текст поста",
            "group": self.group.id,
        }
        response = self.authorized_user.post(
            reverse("posts:post_edit", args=[post.id]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail", kwargs={"post_id": post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.latest("id")
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(post.author, self.post_author)
        self.assertEqual(post.group_id, form_data["group"])

    def test_comment_created(self):
        """проверка ваолидности комментария"""
        count_comment = Comment.objects.count()
        form_data = {
            'post': self.post,
            'author': self.post_author,
            'text': 'Текст комментария'
        }
        self.authorized_user.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), count_comment + 1)
        self.assertTrue(
            Comment.objects.filter(text=form_data['text']).exists()
        )
