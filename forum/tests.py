"""Тесты форума."""
import io

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from catalog.models import Subject

from .models import Post, Topic


class ForumTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_portal", "--no-demo", stdout=io.StringIO())
        cls.user = User.objects.create_user("anna", "a@example.com", "pass-12345-word")
        cls.other = User.objects.create_user("boris", "b@example.com", "pass-12345-word")
        cls.subject = Subject.objects.get(slug="algebra")

    def create_topic(self):
        self.client.force_login(self.user)
        url = reverse("forum:new_topic", kwargs={"faculty": "mechmat", "subject": "algebra"})
        return self.client.post(url, {"title": "Вопрос про группы", "body": "Почему $|G| = |H|\\,[G:H]$?"})

    def test_create_topic(self):
        response = self.create_topic()
        topic = Topic.objects.get()
        self.assertRedirects(response, topic.get_absolute_url())
        self.assertEqual(topic.posts.count(), 1)
        self.assertEqual(topic.subject, self.subject)

    def test_anonymous_cannot_post(self):
        self.create_topic()
        topic = Topic.objects.get()
        self.client.logout()
        response = self.client.post(topic.get_absolute_url(), {"body": "спам"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(topic.posts.count(), 1)

    def test_reply_quote_and_preview(self):
        self.create_topic()
        topic = Topic.objects.get()
        first = topic.posts.get()

        self.client.force_login(self.other)
        response = self.client.get(topic.get_absolute_url(), {"quote": first.pk})
        self.assertContains(response, "&gt; **anna** писал(а):")

        response = self.client.post(topic.get_absolute_url(), {"body": "Теорема Лагранжа", "preview": "1"})
        self.assertContains(response, "Предпросмотр")
        self.assertEqual(topic.posts.count(), 1)

        response = self.client.post(
            topic.get_absolute_url(), {"body": "Теорема Лагранжа", "reply_to": first.pk}
        )
        self.assertEqual(response.status_code, 302)
        reply = topic.posts.latest("created_at")
        self.assertEqual(reply.reply_to, first)

    def test_locked_topic(self):
        self.create_topic()
        topic = Topic.objects.get()
        topic.is_locked = True
        topic.save()
        self.client.force_login(self.other)
        self.client.post(topic.get_absolute_url(), {"body": "ответ"})
        self.assertEqual(topic.posts.count(), 1)

    def test_only_author_edits_post(self):
        self.create_topic()
        post = Post.objects.get()
        self.client.force_login(self.other)
        response = self.client.post(reverse("forum:edit_post", args=[post.pk]), {"body": "взлом"})
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.user)
        self.client.post(reverse("forum:edit_post", args=[post.pk]), {"body": "исправлено"})
        post.refresh_from_db()
        self.assertEqual(post.body, "исправлено")
        self.assertTrue(post.is_edited)

    def test_xss_in_post(self):
        self.client.force_login(self.user)
        url = reverse("forum:new_topic", kwargs={"faculty": "mechmat", "subject": "algebra"})
        self.client.post(url, {"title": "<b>t</b>", "body": '<img src=x onerror="alert(1)">'})
        response = self.client.get(Topic.objects.get().get_absolute_url())
        self.assertNotContains(response, "onerror")
        self.assertContains(response, "&lt;b&gt;t&lt;/b&gt;")
