import logging
import os
from pathlib import Path

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Классификация текстов"

    def ready(self):
        import sys

        logs_dir = Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        if any(cmd in sys.argv for cmd in ("migrate", "makemigrations", "test")):
            return
        if os.environ.get("SKIP_ML_WARMUP", "").lower() in ("1", "true", "yes"):
            return

        try:
            from core.services import ml_service

            ml_service.warmup()
        except Exception:
            logger.exception("Не удалось прогреть ML-модель при старте")
