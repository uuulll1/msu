"""Тесты регистрации и профиля."""
from django.test import TestCase
from django.urls import reverse

from .models import User


class AccountTests(TestCase):
    def test_signup_and_login(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "newbie",
                "email": "New@Example.com",
                "password1": "very-strong-pass-42",
                "password2": "very-strong-pass-42",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newbie")
        self.assertEqual(user.email, "new@example.com")
        # Пользователь сразу авторизован
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_rejected(self):
        User.objects.create_user("first", "same@example.com", "pass-12345-word")
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "second",
                "email": "SAME@example.com",
                "password1": "very-strong-pass-42",
                "password2": "very-strong-pass-42",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="second").exists())

    def test_logout_requires_post(self):
        user = User.objects.create_user("u", "u@example.com", "pass-12345-word")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_page(self):
        user = User.objects.create_user("u", "u@example.com", "pass-12345-word", bio="**Привет**")
        response = self.client.get(user.get_absolute_url())
        self.assertContains(response, "<strong>Привет</strong>")
