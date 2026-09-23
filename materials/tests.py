"""Тесты материалов: валидация файлов, модерация, поиск, скачивание."""
import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User
from catalog.models import Subject
from core.management.commands.seed_portal import build_demo_pdf

from .models import Material
from .validators import validate_material_file

TEMP_MEDIA = tempfile.mkdtemp()


def make_pdf(name="test.pdf"):
    return SimpleUploadedFile(name, build_demo_pdf("Test", ["line"]), content_type="application/pdf")


def make_png(name="pic.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "navy").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class ValidatorTests(TestCase):
    def assertInvalid(self, uploaded):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            validate_material_file(uploaded)

    def test_valid_files(self):
        validate_material_file(make_pdf())
        validate_material_file(make_png())
        validate_material_file(SimpleUploadedFile("a.md", "# Заголовок $x$".encode()))
        validate_material_file(SimpleUploadedFile("a.tex", b"\\documentclass{article}"))

    def test_bad_extension(self):
        self.assertInvalid(SimpleUploadedFile("evil.exe", b"MZ..."))
        self.assertInvalid(SimpleUploadedFile("image.svg", b"<svg onload=alert(1)>"))
        self.assertInvalid(SimpleUploadedFile("page.html", b"<script></script>"))

    def test_fake_pdf(self):
        self.assertInvalid(SimpleUploadedFile("fake.pdf", b"<html>not a pdf</html>"))

    def test_fake_image(self):
        self.assertInvalid(SimpleUploadedFile("fake.png", b"GIF89a-not-really"))

    def test_image_extension_mismatch(self):
        png = make_png("pic.jpg")
        self.assertInvalid(png)

    def test_binary_text_file(self):
        self.assertInvalid(SimpleUploadedFile("notes.md", b"abc\x00def"))

    def test_non_utf8_text(self):
        self.assertInvalid(SimpleUploadedFile("notes.tex", "Привет".encode("cp1251")))

    @override_settings(MAX_UPLOAD_SIZE=1024)
    def test_too_large(self):
        self.assertInvalid(SimpleUploadedFile("big.md", b"a" * 2048))

    def test_empty(self):
        self.assertInvalid(SimpleUploadedFile("empty.md", b""))


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class MaterialFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_portal", "--no-demo", stdout=io.StringIO())
        cls.student = User.objects.create_user("student", "s@example.com", "pass-12345-word")
        cls.other = User.objects.create_user("other", "o@example.com", "pass-12345-word")
        cls.subject = Subject.objects.get(slug="matematicheskiy-analiz")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def upload(self, **extra):
        data = {
            "title": "Конспект по пределам",
            "subject": self.subject.pk,
            "material_type": Material.Type.LECTURES,
            "teacher": "Иванов И. И.",
            "tags_input": "Пределы, ряды",
            "description": "Описание $x$",
            "file": make_pdf(),
        }
        data.update(extra)
        return self.client.post(reverse("materials:upload"), data)

    def test_upload_requires_login(self):
        response = self.upload()
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertFalse(Material.objects.exists())

    def test_new_material_is_pending_and_hidden(self):
        self.client.force_login(self.student)
        self.upload()
        material = Material.objects.get()
        self.assertEqual(material.status, Material.Status.PENDING)
        self.assertEqual(material.original_filename, "test.pdf")
        self.assertEqual(sorted(material.tags.values_list("name", flat=True)), ["пределы", "ряды"])

        # Автор видит свой материал
        self.assertEqual(self.client.get(material.get_absolute_url()).status_code, 200)
        # Другой пользователь и аноним — нет
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(material.get_absolute_url()).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(material.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(material.get_download_url()).status_code, 404)
        # И в поиске его нет
        self.assertEqual(self.client.get(reverse("materials:search")).context["total"], 0)

    def test_invalid_file_rejected(self):
        self.client.force_login(self.student)
        response = self.upload(file=SimpleUploadedFile("x.pdf", b"not a pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Material.objects.exists())

    def test_approved_material_search_and_download(self):
        self.client.force_login(self.student)
        self.upload()
        material = Material.objects.get()
        material.status = Material.Status.APPROVED
        material.save()

        # Поиск по преподавателю, тегу (в другом регистре) и предмету
        for query in ("иванов", "ПРЕДЕЛЫ", "математический анализ"):
            response = self.client.get(reverse("materials:search"), {"q": query})
            self.assertEqual(response.context["total"], 1, query)
        response = self.client.get(reverse("materials:search"), {"q": "топология"})
        self.assertEqual(response.context["total"], 0)

        response = self.client.get(material.get_download_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        material.refresh_from_db()
        self.assertEqual(material.downloads_count, 1)

        # Встроенный просмотр разрешён во фрейме того же сайта и не считается скачиванием
        response = self.client.get(material.get_view_url())
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        material.refresh_from_db()
        self.assertEqual(material.downloads_count, 1)

    def test_like_toggle(self):
        self.client.force_login(self.student)
        self.upload()
        material = Material.objects.get()
        material.status = Material.Status.APPROVED
        material.save()
        url = reverse("materials:like", args=[material.pk])
        self.client.post(url)
        self.assertEqual(material.likes.count(), 1)
        self.client.post(url)
        self.assertEqual(material.likes.count(), 0)
        # GET не меняет состояние
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_only_author_can_edit(self):
        self.client.force_login(self.student)
        self.upload()
        material = Material.objects.get()
        material.status = Material.Status.APPROVED
        material.save()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("materials:edit", args=[material.pk])).status_code, 403)

    def test_edit_by_author_returns_to_moderation(self):
        self.client.force_login(self.student)
        self.upload()
        material = Material.objects.get()
        material.status = Material.Status.APPROVED
        material.save()
        response = self.client.post(
            reverse("materials:edit", args=[material.pk]),
            {
                "title": "Новое название",
                "subject": self.subject.pk,
                "material_type": Material.Type.LECTURES,
                "tags_input": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        material.refresh_from_db()
        self.assertEqual(material.title, "Новое название")
        self.assertEqual(material.status, Material.Status.PENDING)

    def test_moderator_uploads_are_published(self):
        moderator = User.objects.create_user("mod", "m@example.com", "pass-12345-word", is_staff=True)
        from django.contrib.auth.models import Group

        moderator.groups.add(Group.objects.get(name="Модераторы"))
        self.client.force_login(moderator)
        self.upload(file=make_png())
        self.assertEqual(Material.objects.get().status, Material.Status.APPROVED)
