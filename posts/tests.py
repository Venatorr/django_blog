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
        self.following_user = User.objects.create_user(username='following_user')

    def test_profile_available(self):
        self.response = self.auth_client.get(
            reverse('profile', args=[self.user.username]))
        message = 'Profile is not available'
        self.assertEqual(self.response.status_code, 200, msg=message)

    def test_new_post_auth(self):
        text = 'Test text'
        self.response = self.auth_client.post(
            reverse('new_post'),
            {'text': text,
             'group': self.group.id,
             'author': self.user.id},
            follow=True)
        message = ('Added post from authorized user '
                   'should redirect to index')
        url = ''
        if 0 < len(self.response.redirect_chain) < 2:
            result_redirect, = self.response.redirect_chain
            url, *_ = result_redirect
        self.assertEqual('/', url, msg=message)
        message = ('Added post from authorized user '
                   'should create new post')
        self.assertEqual(Post.objects.count(), 1, msg=message)
        post, *_ = Post.objects.all()
        message = 'Added post has wrong text'
        self.assertEqual(post.text, text, msg=message)
        message = 'Added post has wrong author'
        self.assertEqual(post.author, self.user, msg=message)
        message = 'Added post has wrong group'
        self.assertEqual(post.group, self.group, msg=message)

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
        self.assertEqual(Post.objects.count(), 0, msg=message)

    def check_post_on_page(self, url, post, message):
        self.response = self.auth_client.get(url)
        self.assertContains(self.response, post.text, msg_prefix=message)
        self.assertContains(self.response, post.group.title, msg_prefix=message)
        self.assertContains(self.response, post.author.username, msg_prefix=message)

    def test_new_post_show(self):
        text = 'Test text'
        self.response = self.auth_client.post(
            reverse('new_post'),
            {'text': text,
             'group': self.group.id},
            follow=True)
        post = Post.objects.get(text__contains=text)
        pages = {'index': reverse('index'),
                 'profile': reverse('profile', args=[self.user.username]),
                 'post': reverse('post', args=[self.user.username, post.id])}
        cache.clear()
        message = 'Added post should be showed on page: '
        for name, url in pages.items():
            with self.subTest(url=url):
                self.check_post_on_page(url, post, message + name)

    def test_edit_post_show(self):
        text = 'Test text'
        self.response = self.auth_client.post(
            reverse('new_post'),
            {'text': text},
            follow=True)
        post = Post.objects.get(text__contains=text)
        text = 'Modifying text'
        self.response = self.auth_client.post(
            reverse('post_edit', args=[self.user.username, post.id]),
            {'text': text,
             'group': self.group.id},
            follow=True)
        post = Post.objects.get(id=post.id)
        pages = {'index': reverse('index'),
                 'profile': reverse('profile', args=[self.user.username]),
                 'post': reverse('post', args=[self.user.username, post.id])}
        # MESSAGE_TO_REVIEWER:
        # изначально делал с override_settings, с ним нормально работало если
        # кэширование делать в шаблоне html, если же делать через @cache_page
        # во view, как сейчас, то override_settings не работает
        # у других студентов такая же проблема - насколько я знаю пока не решена
        # и причины не ясны) ну и вроде в cache.clear ничего плохого нет. или есть?
        cache.clear()
        message = 'Edited post should be showed on page: '
        for name, url in pages.items():
            with self.subTest(url=url):
                self.check_post_on_page(url, post, message + name)

    def test_404(self):
        self.response = self.auth_client.get('/some_wrong_url/')
        message = 'Server should return code 404'
        self.assertEqual(self.response.status_code, 404, msg=message)

    def add_image_to_post(self, post):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open('media/tests/django.png', 'rb') as img:
                    url = reverse('post_edit', args=[self.user.username, post.id])
                    self.response = self.auth_client.post(
                        url,
                        {'text': 'Post with image',
                         'group': self.group.id,
                         'image': img},
                        follow=True)

    def test_image_in_post(self):
        post = Post.objects.create(text='Some text',
                                   author=self.user,
                                   group=self.group)
        self.add_image_to_post(post)
        message = 'Post page should have image from post'
        self.assertContains(self.response,
                            f'id="image_{post.id}"',
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
        post = Post.objects.create(text='Some text',
                                   author=self.user,
                                   group=self.group)
        self.add_image_to_post(post)
        cache.clear()
        for url, message in pages.values():
            self.response = self.auth_client.get(url)
            self.assertContains(self.response,
                                f'id="image_{post.id}"',
                                msg_prefix=message)

    def test_image_format(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open('media/tests/image.exe', 'rb') as img:
                    url = reverse('new_post')
                    self.response = self.auth_client.post(
                        url,
                        {'author': self.user,
                         'text': 'post with image',
                         'image': img}
                    )
                    message = 'Page should contain error message'
                    self.assertFormError(
                        self.response,
                        form='form',
                        field='image',
                        errors=("File extension 'exe' is not allowed. Allowed extensions are: "
                                "'bmp, dib, gif, tif, tiff, jfif, jpe, jpg, jpeg, pbm, pgm, ppm, "
                                "pnm, png, apng, blp, bufr, cur, pcx, dcx, dds, ps, eps, fit, fits, "
                                "fli, flc, ftc, ftu, gbr, grib, h5, hdf, jp2, j2k, jpc, jpf, jpx, "
                                "j2c, icns, ico, im, iim, mpg, mpeg, mpo, msp, palm, pcd, pdf, pxr, "
                                "psd, bw, rgb, rgba, sgi, ras, tga, icb, vda, vst, webp, wmf, "
                                "emf, xbm, xpm'."),
                        msg_prefix=message)

    def test_cache_index_page(self):
        self.response = self.auth_client.get(reverse('index'))
        post = Post.objects.create(text='Not cached text',
                                   author=self.user)
        self.response = self.auth_client.get(reverse('index'))
        message = 'Index page should be cached'
        self.assertNotContains(self.response, post.text, msg_prefix=message)

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
        post = Post.objects.create(text='Some text',
                                   author=self.user,
                                   group=self.group)
        url = reverse('add_comment', args=[self.user.username, post.id])
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

        url = reverse('post', args=[self.user.username, post.id])
        self.response = self.unauth_client.get(url)
        message = ('Adding comment form should be not showed '
                   'on post page for unauth user')
        self.assertNotContains(self.response,
                               'form id="adding_comment"',
                               msg_prefix=message)
