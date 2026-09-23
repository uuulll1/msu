"""Шаблонные фильтры для Markdown."""
from django import template
from django.utils.safestring import mark_safe

from core.markdown import render_markdown

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(value):
    """
    {{ text|markdown }} — рендер Markdown+LaTeX.

    mark_safe здесь допустим: результат уже прошёл очистку nh3
    по белому списку тегов и атрибутов.
    """
    return mark_safe(render_markdown(value or ""))
