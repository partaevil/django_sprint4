from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q, Count
from .models import Post, Category, Comment
from .forms import PostForm, UserProfileForm, CommentForm
from django.views import generic
from django.utils import timezone
from django.http import Http404
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy


# Create your views here.
class CategoryPostsView(generic.ListView):
    template_name = "blog/category.html"
    context_object_name = "post_list"
    paginate_by = 10

    def get_queryset(self):
        self.category = get_object_or_404(
            Category, slug=self.kwargs["category_slug"], is_published=True
        )

        return (
            Post.objects.filter(
                Q(category=self.category)
                & Q(is_published=True)
                & Q(category__is_published=True)
                & Q(pub_date__lte=timezone.now())
            )
            .annotate(comment_count=Count("comments"))
            .order_by("-pub_date")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        return context


class ProfileView(generic.ListView):
    template_name = "blog/profile.html"
    context_object_name = "page_obj"
    paginate_by = 10

    def get_queryset(self):
        self.profile = get_object_or_404(
            User, username=self.kwargs["username"])
        base_query = Post.objects.filter(author=self.profile)

        if self.request.user == self.profile:
            return base_query.annotate(
                comment_count=Count("comments")
            ).order_by(
                "-pub_date"
            )

        return (
            base_query.filter(
                Q(is_published=True)
                & Q(category__is_published=True)
                & Q(pub_date__lte=timezone.now())
            )
            .annotate(comment_count=Count("comments"))
            .order_by("-pub_date")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = self.profile
        return context


class ProfileEditView(LoginRequiredMixin, generic.UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = "blog/user.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy(
            "blog:profile", kwargs={"username": self.request.user.username}
        )


class PostDetailView(generic.DetailView):
    model = Post
    template_name = "blog/detail.html"
    pk_url_kwarg = "post_id"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if (
            not obj.is_published
            or not obj.category.is_published
            or obj.pub_date > timezone.now()
        ):
            if obj.author != self.request.user:
                raise Http404()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = CommentForm()
        context["comments"] = self.object.comments.select_related("author")
        return context


class PostCreateView(LoginRequiredMixin, generic.CreateView):
    model = Post
    form_class = PostForm
    template_name = "blog/create.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "blog:profile", kwargs={"username": self.request.user.username}
        )


class PostEditView(LoginRequiredMixin, generic.UpdateView):
    model = Post
    form_class = PostForm
    template_name = "blog/create.html"
    pk_url_kwarg = "post_id"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.author != self.request.user:
            return None
        return obj

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            # Перенаправляем на страницу деталей поста
            return redirect("blog:post_detail", post_id=kwargs.get("post_id"))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            "blog:post_detail",
            kwargs={"post_id": self.object.id}
        )


class PostDeleteView(LoginRequiredMixin,
                     UserPassesTestMixin,
                     generic.DeleteView):
    model = Post
    template_name = "blog/create.html"
    pk_url_kwarg = "post_id"

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def get_success_url(self):
        return reverse("blog:index")


class PostListView(generic.ListView):
    template_name = "blog/index.html"
    context_object_name = "page_obj"
    paginate_by = 10

    def get_queryset(self):
        return (
            Post.objects.filter(
                Q(is_published=True)
                & Q(category__is_published=True)
                & Q(pub_date__lte=timezone.now())
            )
            .annotate(comment_count=Count("comments"))
            .order_by("-pub_date")
        )


class CommentCreateView(LoginRequiredMixin, generic.CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "includes/comments.html"

    def form_valid(self, form):
        post = get_object_or_404(Post, id=self.kwargs["post_id"])
        form.instance.post = post
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return (
            reverse("blog:post_detail", kwargs={
                    "post_id": self.kwargs["post_id"]})
            + f"#comment{self.object.id}"
        )


class CommentEditView(LoginRequiredMixin,
                      UserPassesTestMixin,
                      generic.UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = "blog/comment.html"
    pk_url_kwarg = "comment_id"

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_success_url(self):
        return (
            reverse("blog:post_detail", kwargs={
                    "post_id": self.object.post.id})
            + f"#comment_{self.object.id}"
        )


class CommentDeleteView(LoginRequiredMixin,
                        UserPassesTestMixin,
                        generic.DeleteView):
    model = Comment
    template_name = "blog/comment.html"
    pk_url_kwarg = "comment_id"

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_success_url(self):
        return reverse(
            "blog:post_detail",
            kwargs={"post_id": self.kwargs["post_id"]}
        )
