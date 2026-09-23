"""Прочие шаблонные теги и фильтры портала."""
from django import template

register = template.Library()


@register.filter
def filesize(value):
    """Человекочитаемый размер файла."""
    try:
        size = float(value)
    except (TypeError, ValueError):
        return "—"
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024 or unit == "ГБ":
            if unit == "Б":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}".replace(".", ",")
        size /= 1024
    return "—"


@register.filter
def plural_ru(number, forms):
    """
    Склонение по числу: {{ n|plural_ru:"материал,материала,материалов" }}.
    """
    try:
        n = abs(int(number))
    except (TypeError, ValueError):
        return ""
    one, few, many = (forms.split(",") + ["", "", ""])[:3]
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


@register.filter
def initials(user):
    """Инициалы для круглого аватара."""
    if not user:
        return "?"
    name = (user.get_full_name() or user.get_username() or "?").strip()
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper()


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """
    Меняет параметры текущего GET-запроса, сохраняя остальные.
    Используется в пагинации и фильтрах: ?{% query_transform page=2 %}
    """
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()
