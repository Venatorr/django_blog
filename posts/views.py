from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page


POST_ON_PAGE = 10


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, POST_ON_PAGE)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context = {'page': page, 'paginator': paginator, 'is_post': False}
    return render(request, 'index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    paginator = Paginator(post_list, POST_ON_PAGE)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context = {'group': group,
               'page': page,
               'paginator': paginator,
               'is_post': False}
    return render(request, 'group.html', context)


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('index')
    context = {'form': form, 'is_create': True, 'post': None}
    return render(request, 'new_post.html', context)


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    user = post.author
    if user != request.user:
        return redirect('post', username=username, post_id=post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('post',
                            username=username,
                            post_id=post_id)
    context = {'form': form, 'is_create': False, 'post': post}
    return render(request, 'new_post.html', context)


def check_following(user, author):
    if not user.is_authenticated:
        return False
    return user.follower.filter(author=author).exists()


def get_follower_count(user):
    return user.follower.count()


def get_following_count(user):
    return user.following.count()


def profile(request, username):
    user = get_object_or_404(User, username=username)
    post_list = user.posts.all()
    paginator = Paginator(post_list, POST_ON_PAGE)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context = {'profile_user': user,
               'following': check_following(request.user, user),
               'page': page,
               'paginator': paginator,
               'is_post': False,
               'follower_count': get_follower_count(user),
               'following_count': get_following_count(user)}
    return render(request, 'profile.html', context)


def post_view(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    user = post.author
    items = post.comments.all()
    comment_form = CommentForm()
    posts_count = user.posts.count()
    context = {'comment_form': comment_form,
               'profile_user': user,
               'following': check_following(request.user, user),
               'post': post,
               'posts_count': posts_count,
               'items': items,
               'is_post': True,
               'follower_count': get_follower_count(user),
               'following_count': get_following_count(user)}
    return render(request, 'post.html', context)


def page_not_found(request, exception):
    return render(
        request,
        'misc/404.html',
        {'path': request.path},
        status=404
    )


def server_error(request):
    return render(request, 'misc/500.html', status=500)


@login_required
def add_comment(request, username, post_id):
    '''
    вызывается только методом POST, поэтому обработка только POST
    '''
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post_id = post_id
        comment.save()
    return redirect('post',
                    username=username,
                    post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(
        author__in=request.user.follower.all().values_list('author')
    )
    paginator = Paginator(post_list, POST_ON_PAGE)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context = {'page': page, 'paginator': paginator, 'is_post': False}
    return render(request, 'follow.html', context)


@login_required
def profile_follow(request, username):
    following_user = get_object_or_404(User, username=username)
    if request.user != following_user:
        Follow.objects.get_or_create(user=request.user, author=following_user)
    return redirect('follow_index')


@login_required
def profile_unfollow(request, username):
    following_user = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=following_user).delete()
    return redirect('follow_index')
