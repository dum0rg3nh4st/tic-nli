import logging
import re
from typing import Iterable, List, Tuple

import torch
import torch.nn.functional as F
from django.conf import settings
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger("core.ml")

_tokenizer = None
_model = None
_device = None
_zero_shot_classifier = None
_model_version: str = ""


def _normalize_backend(name: str) -> str:
    n = (name or "").strip().lower().replace("-", "_")
    if n in ("zero_shot", "zero_shot_nli", "nli", "zeroshot"):
        return "zero_shot_nli"
    if n in ("embedding", "rubert", "similarity", "cosine"):
        return "embedding"
    return "zero_shot_nli"


def _get_device():
    global _device
    if _device is None:
        _device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
    return _device


def _pipeline_device_arg():
    return 0 if torch.cuda.is_available() else -1


def warmup():
    """Загружает выбранный бэкенд один раз (NLI или RuBERT), не оба сразу."""
    global _tokenizer, _model, _zero_shot_classifier, _model_version

    backend = _normalize_backend(getattr(settings, "ML_BACKEND", "zero_shot_nli"))

    if backend == "zero_shot_nli":
        if _zero_shot_classifier is not None:
            return
        model_name = getattr(
            settings,
            "NLI_ZERO_SHOT_MODEL",
            "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
        )
        from transformers import pipeline

        _zero_shot_classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=_pipeline_device_arg(),
        )
        _model_version = f"zero_shot_nli:{model_name}"
        return

    if _model is not None and _tokenizer is not None:
        return
    _ensure_rubert_loaded(set_version=True)


def _ensure_rubert_loaded(set_version: bool = False):
    """Поднимает только энкодер RuBERT (для режима embedding), без NLI."""
    global _tokenizer, _model, _model_version
    if _tokenizer is not None and _model is not None:
        return
    model_name = getattr(settings, "RUBERT_MODEL", "cointegrated/rubert-tiny")
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    _model = AutoModel.from_pretrained(model_name)
    _model.eval()
    _model.to(_get_device())
    if set_version:
        _model_version = f"embedding:{model_name}"


def _lower_case_enabled() -> bool:
    explicit = getattr(settings, "ML_PREPROCESS_LOWER_CASE", None)
    if explicit is not None:
        return bool(explicit)
    model = getattr(settings, "RUBERT_MODEL", "").lower()
    if "uncased" in model:
        return True
    if "cased" in model and "uncased" not in model:
        return False
    return True


def preprocess_text(raw: str) -> str:
    text = (raw or "").strip()
    if _lower_case_enabled():
        text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\-.,!?;:()«»\"'%]+", " ", text, flags=re.UNICODE)
    return text.strip()


def preprocess_nli(raw: str) -> str:
    """Минимальная нормализация: NLI лучше на естественной пунктуации и регистре."""
    text = re.sub(r"\s+", " ", (raw or "").strip())
    return text.strip()


def _mean_pool(last_hidden: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
    summed = torch.sum(last_hidden * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


def _encode_batch(texts: List[str]) -> torch.Tensor:
    _ensure_rubert_loaded(set_version=False)
    device = _get_device()
    encoded = _tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    encoded = {k: v.to(device) for k, v in encoded.items()}
    with torch.no_grad():
        outputs = _model(**encoded)
        last = outputs.last_hidden_state
        mask = encoded["attention_mask"]
        mean_p = _mean_pool(last, mask)
        cls = last[:, 0]
        pooled = F.normalize(0.5 * cls + 0.5 * mean_p, p=2, dim=1)
    return pooled


def _category_label_embedding(name: str, description: str) -> str:
    name = name.strip()
    desc = (description or "").strip()
    if desc:
        return (
            f'Классифицируемый фрагмент относится к теме «{name}». '
            f"Признаки этой темы: {desc}"
        )
    return f'Классифицируемый фрагмент относится к теме «{name}».'


def _zero_shot_candidate_label(cat) -> str:
    name = cat.name.strip()
    desc = (cat.description or "").strip()
    if not desc:
        return name
    if len(desc) > 450:
        desc = desc[:447] + "..."
    return f"{name}. {desc}"


def _predict_embedding(text: str, cats: list) -> Tuple[object, float]:
    cleaned = preprocess_text(text)
    if len(cleaned) < 3:
        cleaned = preprocess_text(text) or text[:512]

    cat_texts = [_category_label_embedding(c.name, c.description or "") for c in cats]
    text_vec = _encode_batch([f"Текст для классификации: {cleaned}"])
    cat_vecs = _encode_batch(cat_texts)
    sim = torch.matmul(text_vec, cat_vecs.T).squeeze(0)
    probs = torch.softmax(sim, dim=0)
    best_idx = int(torch.argmax(probs).item())
    confidence = float(probs[best_idx].item())
    return cats[best_idx], confidence


def _predict_zero_shot(text: str, cats: list) -> Tuple[object, float]:
    cleaned = preprocess_nli(text)
    if len(cleaned) < 3:
        cleaned = (text or "").strip()[:2048]

    labels = [_zero_shot_candidate_label(c) for c in cats]
    template = getattr(
        settings,
        "NLI_HYPOTHESIS_TEMPLATE",
        "Этот текст в основном относится к следующей теме: {}.",
    )
    out = _zero_shot_classifier(
        cleaned,
        candidate_labels=labels,
        hypothesis_template=template,
        multi_label=False,
    )
    best = out["labels"][0]
    score = float(out["scores"][0])
    idx = labels.index(best)
    return cats[idx], score


def predict(text: str, categories: Iterable) -> Tuple[object, float]:
    """
    Классифицирует текст по категориям из БД.

    Режим ``zero_shot_nli`` (по умолчанию): мультиязычный NLI, удобен для
    сценариев вроде «жалоба / информационный запрос».

    Режим ``embedding``: эмбеддинги RuBERT + softmax по косинусу (легче по памяти).
    """
    cats = list(categories)
    if not cats:
        raise ValueError("Нет ни одной категории для классификации")

    backend = _normalize_backend(getattr(settings, "ML_BACKEND", "zero_shot_nli"))
    try:
        warmup()
        if backend == "zero_shot_nli":
            return _predict_zero_shot(text, cats)
        return _predict_embedding(text, cats)
    except Exception:
        logger.exception("Ошибка при классификации текста")
        raise


def get_model_version() -> str:
    if _model_version:
        return _model_version
    backend = _normalize_backend(getattr(settings, "ML_BACKEND", "zero_shot_nli"))
    if backend == "zero_shot_nli":
        return getattr(
            settings,
            "NLI_ZERO_SHOT_MODEL",
            "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
        )
    return getattr(settings, "RUBERT_MODEL", "cointegrated/rubert-tiny")
