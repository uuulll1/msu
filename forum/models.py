"""
Модели форума.

Ветка форума = предмет (catalog.Subject), поэтому отдельная модель
«раздела» не нужна: появился предмет — появилась и его ветка.
Тема (Topic) содержит сообщения (Post); первое сообщение — текст темы.
"""
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Topic(models.Model):
    subject = models.ForeignKey(
        "catalog.Subject", verbose_name="предмет", on_delete=models.CASCADE, related_name="topics"
    )
    title = models.CharField("заголовок", max_length=200)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор",
        on_delete=models.SET_NULL,
        null=True,
        related_name="forum_topics",
    )
    created_at = models.DateTimeField("создана", default=timezone.now)
    last_activity_at = models.DateTimeField("последняя активность", default=timezone.now, db_index=True)
    is_pinned = models.BooleanField("закреплена", default=False)
    is_locked = models.BooleanField("закрыта для ответов", default=False)
    views_count = models.PositiveIntegerField("просмотров", default=0)

    class Meta:
        verbose_name = "тема"
        verbose_name_plural = "темы"
        ordering = ["-is_pinned", "-last_activity_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("forum:topic", kwargs={"pk": self.pk})

    @property
    def replies_count(self):
        """Число ответов (без стартового сообщения). Можно переопределить аннотацией."""
        count = getattr(self, "posts_total", None)
        if count is None:
            count = self.posts.count()
        return max(count - 1, 0)


class Post(models.Model):
    topic = models.ForeignKey(Topic, verbose_name="тема", on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор",
        on_delete=models.SET_NULL,
        null=True,
        related_name="forum_posts",
    )
    body = models.TextField("текст", max_length=30_000, help_text="Поддерживается Markdown и LaTeX")
    reply_to = models.ForeignKey(
        "self",
        verbose_name="в ответ на",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    created_at = models.DateTimeField("создано", default=timezone.now)
    updated_at = models.DateTimeField("изменено", auto_now=True)
    is_edited = models.BooleanField("отредактировано", default=False)
    is_hidden = models.BooleanField("скрыто модератором", default=False)

    class Meta:
        verbose_name = "сообщение"
        verbose_name_plural = "сообщения"
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"Сообщение #{self.pk} в «{self.topic}»"

    def get_absolute_url(self):
        # Ссылка на страницу темы, где находится сообщение
        position = Post.objects.filter(
            topic_id=self.topic_id, is_hidden=False, created_at__lt=self.created_at
        ).count()
        page = position // POSTS_PER_PAGE + 1
        url = self.topic.get_absolute_url()
        if page > 1:
            url += f"?page={page}"
        return f"{url}#post-{self.pk}"

    def can_edit(self, user):
        return user.is_authenticated and (user.pk == self.author_id or user.is_moderator)


# Число сообщений на странице темы (используется и в представлениях)
POSTS_PER_PAGE = 20
