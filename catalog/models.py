"""
Модели учебной иерархии.

Факультет → Специальность → Курс → Семестр → Предмет.

Предмет принадлежит факультету и может читаться в нескольких семестрах
разных специальностей (например, матанализ у всех трёх специальностей
мехмата) — связь «семестр ↔ предмет» многие-ко-многим. Благодаря этому
материалы и форумная ветка у предмета общие, а новые факультеты и
специальности добавляются просто новыми записями в админке или
в команде seed_portal — без изменения кода.
"""
from django.db import models
from django.urls import reverse


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Faculty(models.Model):
    name = models.CharField("название", max_length=200, unique=True)
    short_name = models.CharField("краткое название", max_length=50, help_text="Например: «Мехмат»")
    slug = models.SlugField("адрес (slug)", max_length=60, unique=True)
    description = models.TextField("описание", blank=True, help_text="Поддерживается Markdown")
    order = models.PositiveSmallIntegerField("порядок", default=0)
    is_active = models.BooleanField("показывать на сайте", default=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "факультет"
        verbose_name_plural = "факультеты"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("catalog:faculty", kwargs={"faculty": self.slug})


class Specialty(models.Model):
    class Degree(models.TextChoices):
        BACHELOR = "bachelor", "Бакалавриат"
        SPECIALIST = "specialist", "Специалитет"
        MASTER = "master", "Магистратура"

    faculty = models.ForeignKey(
        Faculty, verbose_name="факультет", on_delete=models.CASCADE, related_name="specialties"
    )
    name = models.CharField("название", max_length=200)
    short_name = models.CharField("сокращение", max_length=30, blank=True, help_text="Например: ФМиМ")
    slug = models.SlugField("адрес (slug)", max_length=60)
    code = models.CharField("код направления", max_length=20, blank=True)
    degree = models.CharField("уровень", max_length=20, choices=Degree.choices, default=Degree.BACHELOR)
    duration_years = models.PositiveSmallIntegerField("срок обучения, лет", default=4)
    description = models.TextField("описание", blank=True, help_text="Поддерживается Markdown")
    order = models.PositiveSmallIntegerField("порядок", default=0)
    is_active = models.BooleanField("показывать на сайте", default=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "специальность"
        verbose_name_plural = "специальности"
        ordering = ["faculty", "order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["faculty", "slug"], name="unique_specialty_slug_per_faculty"),
        ]

    def __str__(self):
        return f"{self.name} ({self.faculty.short_name})"

    @property
    def display_short(self):
        return self.short_name or self.name

    def get_absolute_url(self):
        return reverse(
            "catalog:specialty", kwargs={"faculty": self.faculty.slug, "specialty": self.slug}
        )

    def ensure_structure(self):
        """
        Создаёт недостающие курсы и семестры по сроку обучения
        (по два семестра на курс). Возвращает число созданных семестров.
        """
        created = 0
        for course_number in range(1, self.duration_years + 1):
            course, _ = Course.objects.get_or_create(specialty=self, number=course_number)
            for semester_number in (course_number * 2 - 1, course_number * 2):
                _, is_new = Semester.objects.get_or_create(course=course, number=semester_number)
                created += int(is_new)
        return created


class Course(models.Model):
    """Курс — год обучения в рамках специальности."""

    specialty = models.ForeignKey(
        Specialty, verbose_name="специальность", on_delete=models.CASCADE, related_name="courses"
    )
    number = models.PositiveSmallIntegerField("номер курса")

    class Meta:
        verbose_name = "курс"
        verbose_name_plural = "курсы"
        ordering = ["specialty", "number"]
        constraints = [
            models.UniqueConstraint(fields=["specialty", "number"], name="unique_course_number"),
        ]

    def __str__(self):
        return f"{self.number} курс — {self.specialty}"

    def get_absolute_url(self):
        return reverse(
            "catalog:course",
            kwargs={
                "faculty": self.specialty.faculty.slug,
                "specialty": self.specialty.slug,
                "course": self.number,
            },
        )


class Semester(models.Model):
    """Семестр. Номер сквозной: у 1 курса семестры 1 и 2, у 2 курса — 3 и 4 и т.д."""

    course = models.ForeignKey(Course, verbose_name="курс", on_delete=models.CASCADE, related_name="semesters")
    number = models.PositiveSmallIntegerField("номер семестра")
    subjects = models.ManyToManyField(
        "Subject", verbose_name="предметы", related_name="semesters", blank=True
    )

    class Meta:
        verbose_name = "семестр"
        verbose_name_plural = "семестры"
        ordering = ["course", "number"]
        constraints = [
            models.UniqueConstraint(fields=["course", "number"], name="unique_semester_number"),
        ]

    def __str__(self):
        return f"{self.number} семестр — {self.course.specialty}"

    @property
    def specialty(self):
        return self.course.specialty

    def get_absolute_url(self):
        specialty = self.course.specialty
        return reverse(
            "catalog:semester",
            kwargs={
                "faculty": specialty.faculty.slug,
                "specialty": specialty.slug,
                "course": self.course.number,
                "semester": self.number,
            },
        )


class Subject(models.Model):
    """Учебный предмет. У каждого предмета — свои материалы и своя ветка форума."""

    faculty = models.ForeignKey(
        Faculty, verbose_name="факультет", on_delete=models.CASCADE, related_name="subjects"
    )
    name = models.CharField("название", max_length=200)
    slug = models.SlugField("адрес (slug)", max_length=80)
    description = models.TextField("описание", blank=True, help_text="Поддерживается Markdown и LaTeX")
    is_active = models.BooleanField("показывать на сайте", default=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = "предмет"
        verbose_name_plural = "предметы"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["faculty", "slug"], name="unique_subject_slug_per_faculty"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("catalog:subject", kwargs={"faculty": self.faculty.slug, "subject": self.slug})

    def get_forum_url(self):
        return reverse("forum:subject", kwargs={"faculty": self.faculty.slug, "subject": self.slug})
