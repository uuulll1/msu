"""Сигналы: поддерживаем поисковый индекс и чистим файлы."""
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver

from .models import Material


@receiver(m2m_changed, sender=Material.tags.through)
def update_search_text_on_tags_change(sender, instance, action, **kwargs):
    """После изменения тегов пересобираем поисковую строку материала."""
    if action in {"post_add", "post_remove", "post_clear"} and isinstance(instance, Material):
        instance.rebuild_search_text(save=True)


@receiver(post_delete, sender=Material)
def delete_file_with_material(sender, instance, **kwargs):
    """Удаляем файл с диска вместе с записью о материале."""
    if instance.file:
        instance.file.delete(save=False)
