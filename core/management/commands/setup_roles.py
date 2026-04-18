from django.core.management.base import BaseCommand

from core.models import Category
from core.permissions import ensure_default_groups


class Command(BaseCommand):
    help = "Создаёт группы ролей и при необходимости демо-категории"

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo-categories",
            action="store_true",
            help="Добавить примеры категорий, если таблица пуста",
        )

    def handle(self, *args, **options):
        ensure_default_groups()
        self.stdout.write(
            self.style.SUCCESS("Groups ready: employee, analyst, management.")
        )

        if options["demo_categories"] and not Category.objects.exists():
            samples = [
                ("Жалоба", "Обращения с негативом или претензией"),
                ("Запрос информации", "Вопросы и просьбы о данных"),
                ("Благодарность", "Позитивная обратная связь"),
                ("Техническая поддержка", "Проблемы с продуктом или сервисом"),
            ]
            for name, desc in samples:
                Category.objects.create(name=name, description=desc)
            self.stdout.write(
                self.style.SUCCESS("Demo categories created: %s" % len(samples))
            )
