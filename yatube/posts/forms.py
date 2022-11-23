from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        labels = {'text': 'Текст поста', 'group': 'Группа'}
        help_texts = {'group': 'Выберите группу', 'text': 'Введите ссообщение'}
        fields = ('text', 'group', 'image')


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        labels = {'text': 'Добавить комментарий'}
        help_texts = {'text': 'Текст комментария'}
        fields = ('text',)
