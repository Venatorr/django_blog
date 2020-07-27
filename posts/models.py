from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
MAX_TEXT_LENGTH = 100


class Group(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название группы')
    slug = models.SlugField(unique=True, verbose_name='Адрес группы')
    description = models.TextField(verbose_name='Описание группы')

    class Meta:
        ordering = ['title', ]
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(verbose_name='Пост')
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='posts',
                               verbose_name='Автор')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True,
                              null=True, related_name='posts',
                              verbose_name='Группа')
    image = models.ImageField(upload_to='posts/', blank=True, null=True,
                              verbose_name='Изображение')

    class Meta:
        ordering = ['-pub_date', ]
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        if len(self.text) > MAX_TEXT_LENGTH:
            return self.text[:MAX_TEXT_LENGTH] + '...'
        return self.text


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, blank=False,
                             null=False, related_name='comments',
                             verbose_name='Пост')
    author = models.ForeignKey(User, on_delete=models.CASCADE, blank=False,
                               null=False, related_name='comments',
                               verbose_name='Автор комментария')
    text = models.TextField(verbose_name='Комментарий')
    created = models.DateTimeField('date created', auto_now_add=True)

    class Meta:
        ordering = ['-created', ]
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        if len(self.text) > MAX_TEXT_LENGTH:
            return self.text[:MAX_TEXT_LENGTH] + '...'
        return self.text


class Follow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False,
                             null=False, related_name='follower',
                             verbose_name='Подписчик')
    author = models.ForeignKey(User, on_delete=models.CASCADE, blank=False,
                               null=False, related_name='following',
                               verbose_name='Авторы на которых подписан')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
