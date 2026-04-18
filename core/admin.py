from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Category, ClassificationResult, TextRecord

User = get_user_model()

if admin.site.is_registered(User):
    admin.site.unregister(User)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name", "description")


class ClassificationInline(admin.StackedInline):
    model = ClassificationResult
    can_delete = False
    extra = 0
    readonly_fields = (
        "category",
        "user",
        "confidence",
        "model_version",
        "processed_at",
    )


@admin.register(TextRecord)
class TextRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "short_content", "user", "created_at", "has_classification")
    list_filter = ("created_at", "user")
    search_fields = ("content",)
    inlines = [ClassificationInline]
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Текст")
    def short_content(self, obj):
        t = obj.content[:80]
        return t + "…" if len(obj.content) > 80 else t

    @admin.display(description="Классификация", boolean=True)
    def has_classification(self, obj):
        return hasattr(obj, "classification")


@admin.register(ClassificationResult)
class ClassificationResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "text_record",
        "category",
        "user",
        "confidence",
        "model_version",
        "processed_at",
    )
    list_filter = ("category", "model_version", "processed_at")
    search_fields = ("text_record__content",)
    readonly_fields = ("processed_at",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "is_staff",
        "is_superuser",
        "group_list",
    )
    list_filter = ("is_staff", "is_superuser", "groups")

    @admin.display(description="Группы")
    def group_list(self, obj):
        return ", ".join(g.name for g in obj.groups.all())
