import logging

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import CategoryForm, HistoryFilterForm, TextClassificationForm
from .models import Category, ClassificationResult, TextRecord
from .permissions import can_classify, can_manage_categories
from .services import ml_service

logger = logging.getLogger(__name__)


@login_required
def index(request):
    form = TextClassificationForm()
    result = None
    allow_post = can_classify(request.user)

    if request.method == "POST":
        if not allow_post:
            return HttpResponseForbidden(
                "У вас нет права отправлять тексты на классификацию."
            )
        form = TextClassificationForm(request.POST)
        if form.is_valid():
            content = form.cleaned_data["content"]
            categories = list(Category.objects.all())
            if not categories:
                messages.error(
                    request,
                    "Нет категорий в системе. Обратитесь к специалисту по анализу.",
                )
            else:
                try:
                    category, confidence = ml_service.predict(content, categories)
                    model_version = ml_service.get_model_version()
                    with transaction.atomic():
                        text_record = TextRecord.objects.create(
                            content=content,
                            user=request.user,
                        )
                        ClassificationResult.objects.create(
                            text_record=text_record,
                            category=category,
                            user=request.user,
                            confidence=confidence,
                            model_version=model_version,
                        )
                    result = {
                        "category": category,
                        "confidence": confidence,
                        "record_id": text_record.pk,
                    }
                    messages.success(request, "Текст успешно классифицирован.")
                    form = TextClassificationForm()
                except Exception as exc:
                    logger.exception("Сбой классификации: %s", exc)
                    messages.error(
                        request,
                        "Не удалось выполнить классификацию. Попробуйте позже.",
                    )

    return render(
        request,
        "core/index.html",
        {
            "form": form,
            "result": result,
            "can_classify": allow_post,
            "ml_backend": getattr(django_settings, "ML_BACKEND", "zero_shot_nli"),
        },
    )


@login_required
@require_POST
def clear_classification_history(request):
    """Удаляет записи текущего пользователя или всю историю (только для аналитика)."""
    clear_all = request.POST.get("scope") == "all"
    if clear_all and not can_manage_categories(request.user):
        return HttpResponseForbidden(
            "У вас нет права удалять всю историю классификаций."
        )

    if clear_all:
        qs = TextRecord.objects.filter(classification__isnull=False)
        n = qs.count()
        if n:
            qs.delete()
            messages.success(request, f"Из истории удалено записей: {n}.")
        else:
            messages.info(request, "История классификаций уже пуста.")
    else:
        qs = TextRecord.objects.filter(
            user=request.user,
            classification__isnull=False,
        )
        n = qs.count()
        if n:
            qs.delete()
            messages.success(request, f"Удалено записей из вашей истории: {n}.")
        else:
            messages.info(request, "У вас нет записей в истории классификаций.")
    return redirect("core:history")


class TextRecordListView(LoginRequiredMixin, ListView):
    model = TextRecord
    template_name = "core/history.html"
    context_object_name = "records"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            TextRecord.objects.filter(classification__isnull=False)
            .select_related("user", "classification", "classification__category")
            .order_by("-created_at")
        )
        self.filter_form = HistoryFilterForm(self.request.GET or None)
        if self.filter_form.is_valid():
            cat = self.filter_form.cleaned_data.get("category")
            df = self.filter_form.cleaned_data.get("date_from")
            dt = self.filter_form.cleaned_data.get("date_to")
            if cat:
                qs = qs.filter(classification__category=cat)
            if df:
                qs = qs.filter(created_at__date__gte=df)
            if dt:
                qs = qs.filter(created_at__date__lte=dt)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = getattr(self, "filter_form", HistoryFilterForm())
        q = self.request.GET.copy()
        q.pop("page", None)
        ctx["filter_query"] = q.urlencode()
        ctx["can_clear_all_history"] = can_manage_categories(self.request.user)
        return ctx


class TextRecordDetailView(LoginRequiredMixin, DetailView):
    model = TextRecord
    template_name = "core/detail.html"
    context_object_name = "record"

    def get_queryset(self):
        return TextRecord.objects.filter(classification__isnull=False).select_related(
            "user",
            "classification",
            "classification__category",
        )


class StatisticsView(LoginRequiredMixin, ListView):
    model = ClassificationResult
    template_name = "core/statistics.html"
    context_object_name = "rows"

    def get_queryset(self):
        return (
            ClassificationResult.objects.values("category__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        labels = []
        data = []
        for row in ctx["rows"]:
            labels.append(row["category__name"])
            data.append(row["total"])
        ctx["chart_payload"] = {"labels": labels, "data": data}
        ctx["total_classifications"] = sum(data) if data else 0
        return ctx


class AnalystRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return can_manage_categories(self.request.user)


class CategoryListView(LoginRequiredMixin, AnalystRequiredMixin, ListView):
    model = Category
    template_name = "core/category_list.html"
    context_object_name = "categories"


class CategoryCreateView(LoginRequiredMixin, AnalystRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "core/category_form.html"
    success_url = reverse_lazy("core:category_list")


class CategoryUpdateView(LoginRequiredMixin, AnalystRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "core/category_form.html"
    success_url = reverse_lazy("core:category_list")
