"""Формы форума."""
from django import forms

from .models import Post, Topic

BODY_WIDGET = forms.Textarea(
    attrs={
        "rows": 8,
        "placeholder": "Поддерживаются Markdown и LaTeX: $\\int_0^1 x^2\\,dx = \\frac13$",
    }
)


class TopicForm(forms.ModelForm):
    body = forms.CharField(label="Сообщение", widget=BODY_WIDGET, max_length=30_000)

    class Meta:
        model = Topic
        fields = ("title",)
        labels = {"title": "Заголовок темы"}


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("body",)
        labels = {"body": "Ответ"}
        widgets = {"body": BODY_WIDGET}
