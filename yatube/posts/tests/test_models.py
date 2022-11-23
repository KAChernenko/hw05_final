from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

FIRST_SYMBOLS: int = 15


User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост более 15 символов',
        )

    def test_models_have_correct_object_names(self):
        group = PostModelTest.group
        expected_name = group.title
        self.assertEqual(expected_name, str(group))

    def test_models_have_correct_obj_name_post(self):
        post = PostModelTest.post
        expected_obj_name = post.text[:FIRST_SYMBOLS]
        self.assertEqual(expected_obj_name, str(post))
