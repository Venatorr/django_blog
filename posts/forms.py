from django.forms import ModelForm, Textarea
from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['text', 'group', 'image']
        help_texts = {
            'text': 'Напишите свой текст поста',
            'group': 'Выберите группу',
            'group': 'Выберите изображение',
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {'text': Textarea(attrs={'rows': 3})}
        help_texts = {
            'text': 'Напишите свой комментарий',
        }
