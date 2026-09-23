"""Тесты навигации по учебной иерархии."""
import io

from django.core.management import call_command
from django.test import TestCase

from .models import Faculty, Semester, Specialty, Subject


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_portal", "--no-demo", stdout=io.StringIO())

    def test_seed_structure(self):
        self.assertEqual(Faculty.objects.count(), 1)
        self.assertEqual(Specialty.objects.count(), 3)
        fmimf = Specialty.objects.get(slug="fmimf")
        self.assertEqual(fmimf.courses.count(), 6)
        first = Semester.objects.get(course__specialty=fmimf, number=1)
        self.assertIn(Subject.objects.get(slug="analiticheskaya-geometriya"), first.subjects.all())

    def test_seed_is_idempotent(self):
        call_command("seed_portal", "--no-demo", stdout=io.StringIO())
        self.assertEqual(Specialty.objects.count(), 3)
        self.assertEqual(Subject.objects.count(), 9)

    def test_hierarchy_pages(self):
        urls = [
            "/f/",
            "/f/mechmat/",
            "/f/mechmat/matematika/",
            "/f/mechmat/matematika/1/",
            "/f/mechmat/matematika/1/2/",
            "/f/mechmat/subjects/algebra/",
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get("/f/mechmat/matematika/9/").status_code, 404)

    def test_inactive_faculty_hidden(self):
        Faculty.objects.update(is_active=False)
        self.assertEqual(self.client.get("/f/mechmat/").status_code, 404)

    def test_new_faculty_is_just_data(self):
        """Архитектура: новый факультет добавляется без изменения кода."""
        physics = Faculty.objects.create(name="Физический факультет", short_name="Физфак", slug="physics")
        spec = Specialty.objects.create(faculty=physics, name="Физика", slug="fizika", duration_years=4)
        spec.ensure_structure()
        subject = Subject.objects.create(faculty=physics, name="Общая физика", slug="obschaya-fizika")
        Semester.objects.get(course__specialty=spec, number=1).subjects.add(subject)
        self.assertEqual(self.client.get("/f/physics/fizika/1/1/").status_code, 200)
        self.assertContains(self.client.get("/f/physics/subjects/obschaya-fizika/"), "Общая физика")
