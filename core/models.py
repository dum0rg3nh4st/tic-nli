from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField("Название", max_length=255, unique=True)
    description = models.TextField("Описание", blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class TextRecord(models.Model):
    content = models.TextField("Текст")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.PROTECT,
        related_name="text_records",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Запись текста"
        verbose_name_plural = "Записи текстов"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} — {self.content[:50]}…" if len(self.content) > 50 else f"#{self.pk} — {self.content}"


class ClassificationResult(models.Model):
    text_record = models.OneToOneField(
        TextRecord,
        verbose_name="Запись текста",
        on_delete=models.CASCADE,
        related_name="classification",
    )
    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        on_delete=models.PROTECT,
        related_name="classifications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.PROTECT,
        related_name="classification_results",
    )
    confidence = models.FloatField("Уверенность")
    model_version = models.CharField("Версия модели", max_length=255)
    processed_at = models.DateTimeField("Обработано", auto_now_add=True)

    class Meta:
        verbose_name = "Результат классификации"
        verbose_name_plural = "Результаты классификации"
        ordering = ["-processed_at"]

    def __str__(self):
        return f"{self.category.name} ({self.confidence:.2%})"
