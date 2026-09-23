"""Навигация по учебной иерархии."""
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, render

from forum.models import Topic
from materials.models import Material

from .models import Course, Faculty, Semester, Specialty, Subject

# Считаем только одобренные материалы
APPROVED_MATERIALS = Count("materials", filter=Q(materials__status=Material.Status.APPROVED), distinct=True)


def faculty_list(request):
    faculties = Faculty.objects.active().prefetch_related(
        Prefetch("specialties", queryset=Specialty.objects.active())
    )
    return render(request, "catalog/faculty_list.html", {"faculties": faculties})


def faculty_detail(request, faculty):
    faculty = get_object_or_404(Faculty.objects.active(), slug=faculty)
    specialties = faculty.specialties.active().annotate(courses_total=Count("courses"))
    subjects = faculty.subjects.active().annotate(materials_total=APPROVED_MATERIALS).order_by("name")
    return render(
        request,
        "catalog/faculty_detail.html",
        {"faculty": faculty, "specialties": specialties, "subjects": subjects},
    )


def _get_specialty(faculty_slug, specialty_slug):
    return get_object_or_404(
        Specialty.objects.active().select_related("faculty").filter(faculty__is_active=True),
        faculty__slug=faculty_slug,
        slug=specialty_slug,
    )


def specialty_detail(request, faculty, specialty):
    specialty = _get_specialty(faculty, specialty)
    courses = specialty.courses.prefetch_related(
        Prefetch("semesters", queryset=Semester.objects.annotate(subjects_total=Count("subjects")))
    )
    latest = (
        Material.objects.approved()
        .filter(semester__course__specialty=specialty)
        .select_related("subject__faculty", "semester")
        .order_by("-created_at")[:6]
    )
    return render(
        request,
        "catalog/specialty_detail.html",
        {"specialty": specialty, "faculty": specialty.faculty, "courses": courses, "latest": latest},
    )


def course_detail(request, faculty, specialty, course):
    specialty = _get_specialty(faculty, specialty)
    course = get_object_or_404(Course, specialty=specialty, number=course)
    semesters = course.semesters.prefetch_related(
        Prefetch(
            "subjects",
            queryset=Subject.objects.active().annotate(materials_total=APPROVED_MATERIALS).order_by("name"),
        )
    )
    return render(
        request,
        "catalog/course_detail.html",
        {"specialty": specialty, "faculty": specialty.faculty, "course": course, "semesters": semesters},
    )


def semester_detail(request, faculty, specialty, course, semester):
    specialty = _get_specialty(faculty, specialty)
    semester = get_object_or_404(
        Semester.objects.select_related("course"),
        course__specialty=specialty,
        course__number=course,
        number=semester,
    )
    subjects = semester.subjects.active().annotate(
        materials_total=APPROVED_MATERIALS, topics_total=Count("topics", distinct=True)
    ).order_by("name")
    latest = (
        Material.objects.approved()
        .filter(semester=semester)
        .select_related("subject__faculty", "semester")
        .order_by("-created_at")[:6]
    )
    return render(
        request,
        "catalog/semester_detail.html",
        {
            "specialty": specialty,
            "faculty": specialty.faculty,
            "course": semester.course,
            "semester": semester,
            "subjects": subjects,
            "latest": latest,
        },
    )


def subject_detail(request, faculty, subject):
    subject = get_object_or_404(
        Subject.objects.active().select_related("faculty"), faculty__slug=faculty, slug=subject
    )

    # Контекст семестра (если пришли со страницы семестра) — для хлебных крошек и фильтра
    semester_ctx = None
    sem_id = request.GET.get("sem")
    if sem_id and sem_id.isdigit():
        semester_ctx = (
            subject.semesters.select_related("course__specialty__faculty").filter(pk=sem_id).first()
        )

    materials = (
        Material.objects.approved()
        .filter(subject=subject)
        .select_related("subject__faculty", "semester__course__specialty", "author")
        .prefetch_related("tags")
        .with_counts()
    )
    if semester_ctx and request.GET.get("only") == "sem":
        materials = materials.filter(semester__number=semester_ctx.number)

    active_type = request.GET.get("type", "")
    type_counts = dict(
        Material.objects.approved()
        .filter(subject=subject)
        .values_list("material_type")
        .annotate(total=Count("pk"))
    )
    if active_type in Material.Type.values:
        materials = materials.filter(material_type=active_type)
    else:
        active_type = ""

    sort = request.GET.get("sort", "new")
    materials = materials.order_by(
        {"popular": "-downloads_count", "likes": "-likes_total"}.get(sort, "-created_at"), "-created_at"
    )
    page = Paginator(materials, 12).get_page(request.GET.get("page"))

    type_tabs = [
        (value, label, type_counts.get(value, 0)) for value, label in Material.Type.choices
    ]
    topics = (
        Topic.objects.filter(subject=subject)
        .select_related("author")
        .annotate(posts_total=Count("posts", filter=Q(posts__is_hidden=False)))
        .order_by("-is_pinned", "-last_activity_at")[:5]
    )
    taught_in = subject.semesters.select_related("course__specialty__faculty").order_by(
        "course__specialty__order", "number"
    )
    return render(
        request,
        "catalog/subject_detail.html",
        {
            "subject": subject,
            "faculty": subject.faculty,
            "semester_ctx": semester_ctx,
            "page_obj": page,
            "type_tabs": type_tabs,
            "active_type": active_type,
            "total_count": sum(type_counts.values()),
            "sort": sort,
            "topics": topics,
            "taught_in": taught_in,
        },
    )
