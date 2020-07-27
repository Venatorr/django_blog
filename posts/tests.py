import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from posts.models import User, Post, Group, Follow
from django.core.cache import cache


class TestPosts(TestCase):
    def setUp(self):
        self.unauth_client = Client()
        self.auth_client = Client()
        self.user = User.objects.create_user(username='test_user')
        self.auth_client.force_login(self.user)
        self.group = Group.objects.create(title='test group', slug='test_group')
        self.post = Post.objects.create(text='Some text',
                                        author=self.user,
                                        group=self.group)
        self.following_user = User.objects.create_user(username='following_user')

    def test_profile_available(self):
        self.response = self.auth_client.get(
            reverse('profile', args=[self.user.username]))
        message = 'Profile is not available'
        self.assertEqual(self.response.status_code, 200, msg=message)

    def test_new_post_auth(self):
        self.response = self.auth_client.post(
            reverse('new_post'), {'text': 'Test text'}, follow=True)
        message = ('Added post from authorized user '
                   'should redirect to index')
        url = ''
        if 0 < len(self.response.redirect_chain) < 2:
            result_redirect, = self.response.redirect_chain
            url, *_ = result_redirect
        self.assertEqual('/', url, msg=message)
        message = ('Added post from authorized user '
                   'should create new post')
        self.assertEqual(Post.objects.count(), 2, msg=message)

    def test_new_post_unauth(self):
        self.response = self.unauth_client.post(
            reverse('new_post'), {'text': 'Test text'}, follow=True)
        message = ('Added post from unauthorized user '
                   'should redirect user to login')
        url = ''
        if 0 < len(self.response.redirect_chain) < 2:
            result_redirect, = self.response.redirect_chain
            url, *_ = result_redirect
        self.assertTrue('login' in url, msg=message)
        message = ('Added post from unauthorized user '
                   'should not create new post')
        self.assertEqual(Post.objects.count(), 1, msg=message)

    def check_post_existence(self, text):
        post = Post.objects.get(text__contains=text)
        pages = {'index': (reverse('index'),
                           'Added post should '
                           'be showed on main page'),
                 'profile': (reverse('profile', args=[self.user.username]),
                             'Added post should '
                             'be showed on profile page'),
                 'post': (reverse('post', args=[self.user.username, post.id]),
                          'Added post should '
                          'be showed on post page')}
        cache.clear()
        for url, message in pages.values():
            self.response = self.auth_client.get(url)
            self.assertContains(self.response, text, msg_prefix=message)

    def test_new_post_show(self):
        text = 'Test text'
        self.response = self.auth_client.post(
            reverse('new_post'), {'text': text}, follow=True)
        self.check_post_existence(text)

    def test_edit_post_show(self):
        text = 'Test text'
        self.response = self.auth_client.post(
            reverse('new_post'), {'text': text}, follow=True)
        post = Post.objects.get(text__contains=text)
        text = 'Modifying text'
        self.response = self.auth_client.post(
            reverse('post_edit', args=[self.user.username, post.id]),
            {'text': text})
        self.check_post_existence(text)

    def test_404(self):
        self.response = self.auth_client.get('/some_wrong_url/')
        message = 'Server should return code 404'
        self.assertEqual(self.response.status_code, 404, msg=message)

    def add_image_to_post(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open('media/tests/django.png', 'rb') as img:
                    url = reverse('post_edit', args=[self.user.username, self.post.id])
                    self.response = self.auth_client.post(
                        url,
                        {'text': 'Post with image',
                         'group': self.group.id,
                         'image': img},
                        follow=True)

    def test_image_in_post(self):
        self.add_image_to_post()
        message = 'Post page should have image from post'
        self.assertContains(self.response,
                            f'id="image_{self.post.id}"',
                            msg_prefix=message)

    def test_image_on_pages(self):
        pages = {'index': (reverse('index'),
                           'Main page should '
                           'have image from post'),
                 'profile': (reverse('profile', args=[self.user.username]),
                             'Profile page should '
                             'have image from post'),
                 'group': (reverse('group', args=[self.group.slug]),
                           'Group page should '
                           'have image from post')}
        self.add_image_to_post()
        cache.clear()
        for url, message in pages.values():
            self.response = self.auth_client.get(url)
            self.assertContains(self.response,
                                f'id="image_{self.post.id}"',
                                msg_prefix=message)

    def test_image_format(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open('media/tests/image.exe', 'rb') as img:
                    url = reverse('post_edit', args=[self.user.username,
                                                     self.post.id])
                    self.response = self.auth_client.post(
                        url,
                        {'author': self.user,
                         'text': 'post with image',
                         'image': img})
                    message = 'Page should contain error message'
                    self.assertContains(self.response,
                                        'File extension &#39;exe&#39; is not allowed',
                                        msg_prefix=message)

    def test_cache_index_page(self):
        self.response = self.auth_client.get(reverse('index'))
        new_post = Post.objects.create(text='Not cached text',
                                       author=self.user)
        self.response = self.auth_client.get(reverse('index'))
        message = 'Index page should be cached'
        self.assertNotContains(self.response, new_post.text, msg_prefix=message)

    def add_following(self):
        url = reverse('profile_follow',
                      args=[self.following_user.username])
        self.response = self.auth_client.post(url)

    def test_follow(self):
        self.add_following()
        is_exist_following = Follow.objects.filter(
            user=self.user, author=self.following_user).exists()
        message = 'Following does not work correctly'
        self.assertTrue(is_exist_following, msg=message)

    def test_unfollow(self):
        self.add_following()
        url = reverse('profile_unfollow', args=[self.following_user.username])
        self.response = self.auth_client.post(url)
        is_exist_following = Follow.objects.filter(
            user=self.user, author=self.following_user).exists()
        message = 'Cancel following does not work correctly'
        self.assertFalse(is_exist_following, msg=message)

    def test_follow_index(self):
        second_user = User.objects.create_user('second user')
        following_post = Post.objects.create(text='Post by following user',
                                             author=self.following_user)
        self.add_following()
        self.response = self.auth_client.get(reverse('follow_index'))
        message = ('Following post should be showed on follow page'
                   'if user have follow')
        self.assertContains(self.response, following_post.text, msg_prefix=message)

        self.unauth_client.force_login(second_user)
        self.response = self.unauth_client.get(reverse('follow_index'))
        message = ('Following post should be not showed on follow page'
                   'if user do not have follow')
        self.assertNotContains(self.response, following_post.text, msg_prefix=message)

    def test_adding_comment(self):
        url = reverse('add_comment', args=[self.user.username, self.post.id])
        text_comment = 'Some comment from auth user'
        self.response = self.auth_client.post(url,
                                              {'text': text_comment},
                                              follow=True)
        message = ('Comment from auth user should be showed '
                   'on post page')
        self.assertContains(self.response, text_comment, msg_prefix=message)

        text_comment = 'Some comment from unauth user'
        self.response = self.unauth_client.post(url,
                                                {'text': text_comment},
                                                follow=True)
        message = ('Comment from unauth user should be not showed '
                   'on post page')
        self.assertNotContains(self.response, text_comment, msg_prefix=message)

        url = reverse('post', args=[self.user.username, self.post.id])
        self.response = self.unauth_client.get(url)
        message = ('Adding comment form should be not showed '
                   'on post page for unauth user')
        self.assertNotContains(self.response,
                               'form id="adding_comment"',
                               msg_prefix=message)
