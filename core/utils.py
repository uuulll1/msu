"""Вспомогательные функции общего назначения."""
from django.utils.text import slugify

# Таблица транслитерации для человекочитаемых латинских slug'ов
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def transliterate(text: str) -> str:
    """Переводит кириллицу в латиницу (упрощённая схема)."""
    result = []
    for char in text:
        lower = char.lower()
        if lower in _TRANSLIT:
            latin = _TRANSLIT[lower]
            result.append(latin.capitalize() if char.isupper() and latin else latin)
        else:
            result.append(char)
    return "".join(result)


def make_slug(text: str, max_length: int = 80) -> str:
    """Создаёт латинский slug из произвольной (в т.ч. русской) строки."""
    slug = slugify(transliterate(text))[:max_length].strip("-")
    return slug or "item"


def unique_slug(model, text: str, field: str = "slug", max_length: int = 80, **scope) -> str:
    """Подбирает уникальный slug для модели (с учётом дополнительных полей-ограничений)."""
    base = make_slug(text, max_length=max_length - 6)
    slug = base
    counter = 2
    while model.objects.filter(**{field: slug}, **scope).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def normalize_search_text(*parts) -> str:
    """
    Готовит строку для поиска: нижний регистр и «ё» → «е».

    SQLite не умеет регистронезависимый поиск по кириллице, поэтому
    храним заранее нормализованную строку и ищем по ней через contains.
    """
    text = " ".join(str(p) for p in parts if p)
    return text.lower().replace("ё", "е")
