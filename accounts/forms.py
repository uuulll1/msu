"""Формы регистрации и редактирования профиля."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from catalog.models import Specialty

from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="Электронная почта", help_text="Не показывается другим пользователям")
    specialty = forms.ModelChoiceField(
        label="Специальность",
        queryset=Specialty.objects.active().select_related("faculty"),
        required=False,
        empty_label="— не указывать —",
    )
    study_year = forms.TypedChoiceField(
        label="Курс",
        choices=[("", "— не указывать —")] + [(i, f"{i} курс") for i in range(1, 7)],
        coerce=int,
        empty_value=None,
        required=False,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "specialty", "study_year")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже зарегистрирован.")
        return email


class LoginForm(AuthenticationForm):
    """Форма входа (переопределена только ради подписей)."""

    username = forms.CharField(label="Имя пользователя", widget=forms.TextInput(attrs={"autofocus": True}))


class ProfileForm(forms.ModelForm):
    study_year = forms.TypedChoiceField(
        label="Курс",
        choices=[("", "— не указывать —")] + [(i, f"{i} курс") for i in range(1, 7)],
        coerce=int,
        empty_value=None,
        required=False,
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "specialty", "study_year", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["specialty"].queryset = Specialty.objects.active().select_related("faculty")
        self.fields["specialty"].empty_label = "— не указывать —"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Эта почта уже используется другим пользователем.")
        return email
