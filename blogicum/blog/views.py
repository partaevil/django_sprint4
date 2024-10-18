from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Post, Category
from django.utils import timezone
from django.http import Http404


# Create your views here.


def index(request):
    # дата публикации — не позже текущего времени.
    context = {
        "post_list": Post.objects.filter(
            Q(is_published__exact=True)
            & Q(category__is_published__exact=True)
            & Q(pub_date__lte=timezone.now())
        )[:5]
    }

    # context = {"posts": reversed(posts)}
    return render(request, "blog/index.html", context)


def post_detail(request, id):
    post = get_object_or_404(Post, pk=id)

    if (
        post.is_published is False
        or post.category.is_published is False
        or post.pub_date >= timezone.now()
    ):
        raise Http404
    context = {"post": post}
    return render(request, "blog/detail.html", context)


def category_posts(request, category_slug):
    category = Category.objects.filter(
        Q(slug__exact=category_slug) & Q(is_published__exact=True)
    )  # get_object_or_404(Category, slug=category_slug)
    if category.exists() is False:
        raise Http404
    context = {
        "post_list": Post.objects.filter(
            Q(category__slug__exact=category_slug)
            & Q(is_published__exact=True)
            & Q(pub_date__lte=timezone.now())
        ),
        "category": category_slug,
    }
    return render(request, "blog/category.html", context)
