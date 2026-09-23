"""
Безопасный рендер Markdown с поддержкой формул LaTeX.

Алгоритм:
1. Вырезаем формулы ($...$, $$...$$, \\(...\\), \\[...\\]) и заменяем их
   плейсхолдерами — иначе Markdown испортит подчёркивания и звёздочки
   внутри формул (a_1 * b_2 превратился бы в курсив).
2. Прогоняем текст через Python-Markdown.
3. Возвращаем формулы на место, экранировав HTML-спецсимволы.
   Сами формулы рендерит KaTeX (auto-render) в браузере.
4. Очищаем итоговый HTML библиотекой nh3 по белому списку тегов
   и атрибутов — это основная защита от XSS.
"""
import html
import re

import markdown as md
import nh3

# Порядок важен: сначала блочные формулы, потом строчные
_MATH_PATTERNS = [
    re.compile(r"\$\$(.+?)\$\$", re.DOTALL),
    re.compile(r"\\\[(.+?)\\\]", re.DOTALL),
    re.compile(r"\\\((.+?)\\\)", re.DOTALL),
    # Строчная формула: без переноса строк, $ не экранирован и не пустой
    re.compile(r"(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)"),
]

# Плейсхолдер из букв и цифр: Markdown его никак не преобразует
_PLACEHOLDER = "KATEXMATHPLACEHOLDER{}END"
_PLACEHOLDER_RE = re.compile(r"KATEXMATHPLACEHOLDER(\d+)END")

# Код тоже прячем, чтобы не искать формулы внутри ```...``` и `...`
_FENCED_CODE_RE = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1[ \t]*$", re.DOTALL | re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_CODE_PLACEHOLDER = "MDCODEPLACEHOLDER{}END"
_CODE_PLACEHOLDER_RE = re.compile(r"MDCODEPLACEHOLDER(\d+)END")

ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "code", "del", "div", "em", "h1", "h2",
    "h3", "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p", "pre", "s", "span",
    "strong", "sub", "sup", "table", "tbody", "td", "th", "thead", "tr", "ul",
    "dl", "dt", "dd",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "abbr": {"title"},
    "img": {"src", "alt", "title"},
    "span": {"class"},
    "div": {"class"},
    "code": {"class"},
    "th": {"align"},
    "td": {"align"},
}

# Разрешённые классы — только наши служебные (формулы и подсветка языка кода)
_ALLOWED_CLASS_RE = re.compile(r"^(math-inline|math-display|language-[\w+-]+)$")

_MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "sane_lists", "nl2br", "def_list", "abbr"]


def _filter_attribute(tag, attr, value):
    """Дополнительный фильтр атрибутов для nh3: пропускаем только безопасные классы."""
    if attr == "class":
        classes = [c for c in value.split() if _ALLOWED_CLASS_RE.match(c)]
        return " ".join(classes) or None
    return value


def _stash(pattern, text, storage, template):
    def replace(match):
        storage.append(match.group(0))
        return template.format(len(storage) - 1)

    return pattern.sub(replace, text)


def render_markdown(text: str) -> str:
    """Превращает Markdown+LaTeX в безопасный HTML."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n")

    # 1. Прячем код, чтобы формулы внутри него не трогать
    code_blocks: list[str] = []
    text = _stash(_FENCED_CODE_RE, text, code_blocks, _CODE_PLACEHOLDER)
    text = _stash(_INLINE_CODE_RE, text, code_blocks, _CODE_PLACEHOLDER)

    # 2. Прячем формулы
    formulas: list[tuple[str, bool]] = []

    def stash_math(match):
        source = match.group(0)
        is_display = source.startswith("$$") or source.startswith("\\[")
        formulas.append((source, is_display))
        return _PLACEHOLDER.format(len(formulas) - 1)

    for pattern in _MATH_PATTERNS:
        text = pattern.sub(stash_math, text)

    # 3. Возвращаем код (Markdown обработает его как код)
    text = _CODE_PLACEHOLDER_RE.sub(lambda m: code_blocks[int(m.group(1))], text)

    # 4. Markdown → HTML
    rendered = md.markdown(text, extensions=_MARKDOWN_EXTENSIONS, output_format="html")

    # 5. Возвращаем формулы, экранируя HTML
    def restore_math(match):
        index = int(match.group(1))
        if index >= len(formulas):
            return match.group(0)
        source, is_display = formulas[index]
        css_class = "math-display" if is_display else "math-inline"
        return f'<span class="{css_class}">{html.escape(source, quote=False)}</span>'

    rendered = _PLACEHOLDER_RE.sub(restore_math, rendered)

    # 6. Очистка по белому списку
    return nh3.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        attribute_filter=_filter_attribute,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow ugc",
        strip_comments=True,
    )


def quote_markdown(text: str, author: str) -> str:
    """Формирует Markdown-цитату для ответа на форуме."""
    lines = (text or "").strip().splitlines()
    quoted = "\n".join(f"> {line}" if line else ">" for line in lines)
    return f"> **{author}** писал(а):\n>\n{quoted}\n\n"
