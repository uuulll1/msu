"""
Проверка загружаемых файлов.

Проверяем не только расширение, но и реальное содержимое:
PDF должен начинаться с сигнатуры %PDF, изображение — открываться Pillow,
текстовые файлы (.tex, .md) — быть корректным UTF-8 без бинарного мусора.
"""
import codecs
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat

# Разрешённые расширения и их «вид» для отображения на сайте.
# SVG сознательно не разрешён: в нём может быть JavaScript.
ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".tex": "text",
    ".md": "text",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".webp": "image",
}

# Какие форматы Pillow соответствуют расширениям изображений
_IMAGE_FORMATS = {
    ".png": {"PNG"},
    ".jpg": {"JPEG", "MPO"},
    ".jpeg": {"JPEG", "MPO"},
    ".gif": {"GIF"},
    ".webp": {"WEBP"},
}


def get_extension(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def validate_file_size(uploaded):
    limit = getattr(settings, "MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    if uploaded.size > limit:
        raise ValidationError(
            f"Файл слишком большой ({filesizeformat(uploaded.size)}). "
            f"Максимум — {filesizeformat(limit)}."
        )
    if uploaded.size == 0:
        raise ValidationError("Файл пустой.")


def validate_file_extension(uploaded):
    ext = get_extension(uploaded.name)
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValidationError(f"Недопустимый тип файла «{ext or 'без расширения'}». Разрешены: {allowed}.")


def _read_head(uploaded, size=8192) -> bytes:
    uploaded.seek(0)
    head = uploaded.read(size)
    uploaded.seek(0)
    return head


def validate_file_content(uploaded):
    """Проверяет, что содержимое файла соответствует расширению."""
    ext = get_extension(uploaded.name)
    kind = ALLOWED_EXTENSIONS.get(ext)

    if kind == "pdf":
        head = _read_head(uploaded, 1024)
        # Сигнатура может быть не в самом начале, но в первых 1024 байтах
        if b"%PDF-" not in head:
            raise ValidationError("Файл не похож на PDF-документ.")

    elif kind == "image":
        from PIL import Image, UnidentifiedImageError

        try:
            uploaded.seek(0)
            with Image.open(uploaded) as image:
                image_format = image.format
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            raise ValidationError("Файл повреждён или не является изображением.")
        finally:
            uploaded.seek(0)
        if image_format not in _IMAGE_FORMATS[ext]:
            raise ValidationError("Расширение файла не соответствует формату изображения.")

    elif kind == "text":
        # Инкрементальный декодер корректно обрабатывает символы,
        # разрезанные границей чанков
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        uploaded.seek(0)
        try:
            for chunk in uploaded.chunks():
                if b"\x00" in chunk:
                    raise ValidationError("Текстовый файл содержит двоичные данные.")
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            raise ValidationError("Текстовый файл должен быть в кодировке UTF-8.")
        finally:
            uploaded.seek(0)


def validate_material_file(uploaded):
    """Полная проверка файла: расширение, размер, содержимое."""
    validate_file_extension(uploaded)
    validate_file_size(uploaded)
    validate_file_content(uploaded)
