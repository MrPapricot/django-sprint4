"""View-функции и классы приложения blog."""
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic

from .forms import CommentForm, PostForm, UserForm
from .models import Category, Comment, Post

User = get_user_model()

POSTS_PER_PAGE = 10


class SignUpView(generic.CreateView):
    """Страница регистрации пользователя."""

    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')


def get_page_obj(request, queryset):
    """Возвращает объект страницы пагинатора для queryset."""
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    return paginator.get_page(request.GET.get('page'))


def posts_queryset():
    """Опубликованные посты: видны всем посетителям сайта."""
    return (
        Post.objects.select_related('category', 'location', 'author')
        .filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )
        .annotate(comment_count=Count('comments'))
        .order_by('-pub_date')
    )


def index(request):
    """Главная страница: лента последних публикаций."""
    page_obj = get_page_obj(request, posts_queryset())
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'blog/index.html', context)


def profile(request, username):
    """Страница пользователя с его публикациями."""
    profile_user = get_object_or_404(User, username=username)
    post_list = (
        Post.objects.filter(author=profile_user)
        .select_related('category', 'location', 'author')
        .annotate(comment_count=Count('comments'))
        .order_by('-pub_date')
    )
    context = {
        'profile': profile_user,
        'page_obj': get_page_obj(request, post_list),
    }
    return render(request, 'blog/profile.html', context)


def category_posts(request, category_slug):
    """Страница категории с её публикациями."""
    category = get_object_or_404(
        Category,
        is_published=True,
        slug=category_slug,
    )
    post_list = (
        posts_queryset()
        .filter(category=category)
        .order_by('-pub_date')
    )
    context = {
        'category': category,
        'page_obj': get_page_obj(request, post_list),
    }
    return render(request, 'blog/category.html', context)


def post_detail(request, post_id):
    """Страница публикации. Доступна её автору и всем посетителям,
    если публикация снята с публикации, отложена или её категория
    скрыта — только автору публикации."""
    post = get_object_or_404(
        Post.objects.select_related('category', 'location', 'author'),
        pk=post_id,
    )
    if request.user != post.author:
        is_category_published = post.category is None or (
            post.category.is_published
        )
        if not (
            post.is_published
            and post.pub_date <= timezone.now()
            and is_category_published
        ):
            raise Http404('Публикация недоступна')
    comments = post.comments.select_related('author').order_by('created_at')
    context = {
        'post': post,
        'comments': comments,
        'form': CommentForm(),
    }
    return render(request, 'blog/detail.html', context)


@login_required
def create_post(request):
    """Страница создания новой публикации."""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    context = {'form': form}
    return render(request, 'blog/create.html', context)


@login_required
def edit_post(request, post_id):
    """Страница редактирования публикации.
    Доступна только автору публикации."""
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    context = {'form': form}
    return render(request, 'blog/create.html', context)


@login_required
def delete_post(request, post_id):
    """Страница подтверждения удаления публикации.
    Доступна только автору публикации."""
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    context = {'form': PostForm(instance=post)}
    return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, post_id):
    """Добавление комментария к публикации."""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    """Страница редактирования комментария.
    Доступна только автору комментария."""
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=post_id,
    )
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    context = {
        'comment': comment,
        'form': form,
    }
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    """Страница подтверждения удаления комментария.
    Доступна только автору комментария."""
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=post_id,
    )
    if request.method == 'POST':
        if comment.author == request.user:
            comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    context = {'comment': comment}
    return render(request, 'blog/comment.html', context)


@login_required
def edit_profile(request):
    """Страница редактирования профиля пользователя."""
    form = UserForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    context = {'form': form}
    return render(request, 'blog/user.html', context)
