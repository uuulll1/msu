"""Тесты рендера Markdown и защиты от XSS."""
from django.test import SimpleTestCase

from core.markdown import quote_markdown, render_markdown
from core.utils import make_slug, normalize_search_text


class MarkdownRenderTests(SimpleTestCase):
    def test_basic_markdown(self):
        html = render_markdown("**жирный** и *курсив*")
        self.assertIn("<strong>жирный</strong>", html)
        self.assertIn("<em>курсив</em>", html)

    def test_script_is_removed(self):
        html = render_markdown("<script>alert(1)</script>Текст")
        self.assertNotIn("<script", html)
        self.assertIn("Текст", html)

    def test_event_handlers_removed(self):
        html = render_markdown('<img src="x.png" onerror="alert(1)">')
        self.assertNotIn("onerror", html)

    def test_javascript_links_removed(self):
        html = render_markdown("[клик](javascript:alert(1))")
        self.assertNotIn("javascript:", html)

    def test_links_get_rel(self):
        html = render_markdown("[сайт](https://example.com)")
        self.assertIn('rel="noopener noreferrer nofollow ugc"', html)

    def test_inline_math_not_mangled_by_markdown(self):
        # Без защиты формул a_1 * b_2 * c_3 превратилось бы в курсив
        html = render_markdown("Формула $a_1 * b_2 * c_3$ в тексте")
        self.assertIn('<span class="math-inline">$a_1 * b_2 * c_3$</span>', html)
        self.assertNotIn("<em>", html)

    def test_display_math(self):
        html = render_markdown("$$\\sum_{n=1}^\\infty \\frac{1}{n^2} = \\frac{\\pi^2}{6}$$")
        self.assertIn('class="math-display"', html)
        self.assertIn("\\sum_{n=1}^\\infty", html)

    def test_html_inside_math_is_escaped(self):
        html = render_markdown("$a < b <script>alert(1)</script>$")
        self.assertNotIn("<script", html)
        self.assertIn("&lt;", html)

    def test_math_inside_code_is_left_alone(self):
        html = render_markdown("`$x_1$`")
        self.assertIn("<code>$x_1$</code>", html)

    def test_dollar_prices_are_not_math(self):
        html = render_markdown("Стоит $5 и $10")
        self.assertNotIn("math-inline", html)

    def test_foreign_class_attribute_removed(self):
        html = render_markdown('<span class="evil math-inline">x</span>')
        self.assertIn('class="math-inline"', html)
        self.assertNotIn("evil", html)

    def test_quote(self):
        self.assertEqual(quote_markdown("строка 1\nстрока 2", "anna"), "> **anna** писал(а):\n>\n> строка 1\n> строка 2\n\n")


class UtilsTests(SimpleTestCase):
    def test_make_slug_transliterates(self):
        self.assertEqual(make_slug("Математический анализ"), "matematicheskiy-analiz")

    def test_normalize_search_text(self):
        self.assertEqual(normalize_search_text("Королёв", "АЛГЕБРА"), "королев алгебра")
