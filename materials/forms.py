"""Формы загрузки материалов и комментариев."""
import re

from django import forms

from catalog.models import Semester, Subject

from .models import Comment, Material, Tag
from .validators import ALLOWED_EXTENSIONS, validate_material_file

MAX_TAGS = 10


class SubjectChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} · {obj.faculty.short_name}"


class SemesterChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        specialty = obj.course.specialty
        return f"{obj.number} семестр ({obj.course.number} курс) · {specialty.display_short}"


class MaterialForm(forms.ModelForm):
    subject = SubjectChoiceField(label="Предмет", queryset=Subject.objects.none())
    semester = SemesterChoiceField(
        label="Семестр",
        queryset=Semester.objects.none(),
        required=False,
        empty_label="— не указан —",
    )
    tags_input = forms.CharField(
        label="Теги",
        required=False,
        help_text="Через запятую, например: пределы, ряды, коллоквиум",
        max_length=500,
    )

    class Meta:
        model = Material
        fields = (
            "title",
            "subject",
            "semester",
            "material_type",
            "teacher",
            "academic_year",
            "description",
            "file",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 7}),
            "teacher": forms.TextInput(attrs={"list": "teacher-suggestions", "autocomplete": "off"}),
            "academic_year": forms.TextInput(attrs={"placeholder": "2025/2026"}),
            "file": forms.ClearableFileInput(attrs={"accept": ",".join(sorted(ALLOWED_EXTENSIONS))}),
        }
        help_texts = {
            "file": "PDF, TeX, Markdown или изображение (PNG, JPG, GIF, WebP), до 50 МБ",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject"].queryset = Subject.objects.active().select_related("faculty").order_by(
            "faculty__order", "name"
        )
        self.fields["semester"].queryset = Semester.objects.select_related(
            "course__specialty__faculty"
        ).order_by("course__specialty__faculty__order", "course__specialty__order", "number")
        if self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(self.instance.tags.values_list("name", flat=True))
            # При редактировании файл можно не перезагружать
            self.fields["file"].required = False

    def clean_file(self):
        uploaded = self.cleaned_data.get("file")
        # Новый загруженный файл проверяем полностью; уже сохранённый — нет
        if uploaded and hasattr(uploaded, "content_type"):
            validate_material_file(uploaded)
        return uploaded

    def clean_academic_year(self):
        value = self.cleaned_data.get("academic_year", "").strip()
        if value:
            match = re.fullmatch(r"(\d{4})\s*[/-]\s*(\d{4})", value)
            if not match or int(match.group(2)) != int(match.group(1)) + 1:
                raise forms.ValidationError("Укажите учебный год в формате 2025/2026.")
            value = f"{match.group(1)}/{match.group(2)}"
        return value

    def clean_tags_input(self):
        raw = self.cleaned_data.get("tags_input", "")
        names = []
        for part in raw.split(","):
            name = " ".join(part.split()).lower()[:50]
            if name and name not in names:
                names.append(name)
        if len(names) > MAX_TAGS:
            raise forms.ValidationError(f"Не больше {MAX_TAGS} тегов.")
        return names

    def clean(self):
        cleaned = super().clean()
        subject = cleaned.get("subject")
        semester = cleaned.get("semester")
        if subject and semester and semester.course.specialty.faculty_id != subject.faculty_id:
            self.add_error("semester", "Семестр относится к другому факультету.")
        return cleaned

    def save_tags(self, material):
        tags = [Tag.objects.get_or_create(name=name)[0] for name in self.cleaned_data["tags_input"]]
        material.tags.set(tags)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        labels = {"body": "Комментарий"}
        widgets = {
            "body": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Markdown и формулы: $e^{i\\pi}+1=0$"}
            )
        }


class SearchForm(forms.Form):
    """Форма поиска и фильтров (все поля необязательные)."""

    SORT_CHOICES = [
        ("new", "Сначала новые"),
        ("popular", "По скачиваниям"),
        ("likes", "По оценкам"),
        ("title", "По названию"),
    ]

    q = forms.CharField(label="Запрос", required=False, max_length=200)
    faculty = forms.CharField(required=False)
    specialty = forms.CharField(required=False)
    subject = forms.CharField(required=False)
    type = forms.ChoiceField(
        label="Тип", required=False, choices=[("", "Все типы")] + list(Material.Type.choices)
    )
    semester = forms.TypedChoiceField(
        label="Семестр",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "Любой")] + [(i, f"{i} семестр") for i in range(1, 13)],
    )
    tag = forms.CharField(required=False, max_length=60)
    sort = forms.ChoiceField(label="Сортировка", required=False, choices=SORT_CHOICES)
