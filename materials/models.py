"""Модели учебных материалов, тегов, лайков и комментариев."""
import os
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.utils import make_slug, normalize_search_text

from .validators import ALLOWED_EXTENSIONS, get_extension


def material_upload_to(instance, filename):
    """
    Путь хранения файла: materials/ГГГГ/ММ/<uuid>.<ext>.
    Исходное имя не используется в пути — это исключает подмену путей
    и коллизии; оригинальное имя сохраняется в поле original_filename.
    """
    ext = get_extension(filename)
    now = timezone.now()
    return f"materials/{now:%Y/%m}/{uuid.uuid4().hex}{ext}"


class Tag(models.Model):
    name = models.CharField("название", max_length=50, unique=True)
    slug = models.SlugField("адрес (slug)", max_length=60, unique=True)

    class Meta:
        verbose_name = "тег"
        verbose_name_plural = "теги"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = make_slug(self.name, max_length=50)
            slug, counter = base, 2
            while Tag.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("materials:search") + f"?tag={self.slug}"


class MaterialQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(status=Material.Status.APPROVED)

    def pending(self):
        return self.filter(status=Material.Status.PENDING)

    def visible_to(self, user):
        """Одобренные материалы плюс собственные (для автора) или все (для модератора)."""
        if user.is_authenticated and getattr(user, "is_moderator", False):
            return self
        if user.is_authenticated:
            return self.filter(models.Q(status=Material.Status.APPROVED) | models.Q(author=user))
        return self.approved()

    def with_counts(self):
        return self.annotate(
            likes_total=models.Count("likes", distinct=True),
            comments_total=models.Count(
                "comments", filter=models.Q(comments__is_hidden=False), distinct=True
            ),
        )


class Material(models.Model):
    class Type(models.TextChoices):
        LECTURES = "lectures", "Конспект лекций"
        SEMINARS = "seminars", "Семинары"
        EXAM_TICKETS = "tickets", "Билеты"
        CHEATSHEET = "cheatsheet", "Шпаргалка"
        PROBLEMS = "problems", "Задачи"
        OTHER = "other", "Другое"

    class Status(models.TextChoices):
        PENDING = "pending", "На проверке"
        APPROVED = "approved", "Одобрен"
        REJECTED = "rejected", "Отклонён"

    title = models.CharField("название", max_length=200)
    subject = models.ForeignKey(
        "catalog.Subject", verbose_name="предмет", on_delete=models.PROTECT, related_name="materials"
    )
    semester = models.ForeignKey(
        "catalog.Semester",
        verbose_name="семестр",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
    )
    teacher = models.CharField("преподаватель", max_length=150, blank=True)
    material_type = models.CharField("тип", max_length=20, choices=Type.choices, default=Type.LECTURES)
    academic_year = models.CharField(
        "учебный год", max_length=9, blank=True, help_text="Например: 2025/2026"
    )
    description = models.TextField("описание", blank=True, help_text="Поддерживается Markdown и LaTeX")
    file = models.FileField("файл", upload_to=material_upload_to, max_length=255)
    original_filename = models.CharField("исходное имя файла", max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField("размер, байт", default=0)
    tags = models.ManyToManyField(Tag, verbose_name="теги", blank=True, related_name="materials")

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор загрузки",
        on_delete=models.SET_NULL,
        null=True,
        related_name="materials",
    )
    created_at = models.DateTimeField("загружен", default=timezone.now, db_index=True)
    updated_at = models.DateTimeField("изменён", auto_now=True)
    downloads_count = models.PositiveIntegerField("скачиваний", default=0)

    status = models.CharField(
        "статус", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    moderation_note = models.TextField(
        "комментарий модератора", blank=True, help_text="Виден автору, например причина отклонения"
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="модератор",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_materials",
    )
    moderated_at = models.DateTimeField("дата модерации", null=True, blank=True)

    # Нормализованный текст для поиска (название, предмет, преподаватель, теги)
    search_text = models.TextField("поисковый индекс", blank=True, editable=False)

    objects = MaterialQuerySet.as_manager()

    class Meta:
        verbose_name = "материал"
        verbose_name_plural = "материалы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["status", "-downloads_count"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("materials:detail", kwargs={"pk": self.pk})

    def get_download_url(self):
        return reverse("materials:download", kwargs={"pk": self.pk})

    def get_view_url(self):
        return reverse("materials:view_file", kwargs={"pk": self.pk})

    # --- Файл ---

    @property
    def extension(self):
        return get_extension(self.original_filename or self.file.name)

    @property
    def file_kind(self):
        """pdf / image / text — определяет способ встроенного просмотра."""
        return ALLOWED_EXTENSIONS.get(self.extension, "other")

    @property
    def is_pdf(self):
        return self.file_kind == "pdf"

    @property
    def is_image(self):
        return self.file_kind == "image"

    @property
    def is_text(self):
        return self.file_kind == "text"

    def read_text_preview(self, limit=200_000):
        """Содержимое .tex/.md для показа на странице (с ограничением размера)."""
        if not self.is_text:
            return ""
        try:
            with self.file.open("rb") as fh:
                data = fh.read(limit)
        except (FileNotFoundError, OSError):
            return ""
        return data.decode("utf-8", errors="replace")

    @property
    def download_filename(self):
        name = self.original_filename or os.path.basename(self.file.name)
        return name

    # --- Статусы ---

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    def can_edit(self, user):
        return user.is_authenticated and (user.pk == self.author_id or user.is_moderator)

    def rebuild_search_text(self, save=True):
        """Пересобирает поисковый индекс; теги учитываются, только если объект уже сохранён."""
        tags = list(self.tags.values_list("name", flat=True)) if self.pk else []
        self.search_text = normalize_search_text(
            self.title,
            self.subject.name if self.subject_id else "",
            self.teacher,
            " ".join(tags),
            self.get_material_type_display(),
        )
        if save and self.pk:
            Material.objects.filter(pk=self.pk).update(search_text=self.search_text)

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)
        try:
            if self.file:
                self.file_size = self.file.size
        except (FileNotFoundError, OSError):
            pass
        self.rebuild_search_text(save=False)
        super().save(*args, **kwargs)


class MaterialLike(models.Model):
    """Оценка «нравится» — один пользователь может отметить материал один раз."""

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="material_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "оценка"
        verbose_name_plural = "оценки"
        constraints = [
            models.UniqueConstraint(fields=["material", "user"], name="unique_material_like"),
        ]

    def __str__(self):
        return f"{self.user} → {self.material}"


class Comment(models.Model):
    material = models.ForeignKey(
        Material, verbose_name="материал", on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор",
        on_delete=models.CASCADE,
        related_name="material_comments",
    )
    body = models.TextField("текст", max_length=10_000, help_text="Поддерживается Markdown и LaTeX")
    created_at = models.DateTimeField("создан", auto_now_add=True)
    is_hidden = models.BooleanField("скрыт модератором", default=False)

    class Meta:
        verbose_name = "комментарий"
        verbose_name_plural = "комментарии"
        ordering = ["created_at"]

    def __str__(self):
        return f"Комментарий {self.author} к «{self.material}»"
