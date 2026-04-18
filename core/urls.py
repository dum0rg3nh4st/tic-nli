from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path("history/", views.TextRecordListView.as_view(), name="history"),
    path("record/<int:pk>/", views.TextRecordDetailView.as_view(), name="detail"),
    path("statistics/", views.StatisticsView.as_view(), name="statistics"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path(
        "categories/add/",
        views.CategoryCreateView.as_view(),
        name="category_add",
    ),
    path(
        "categories/<int:pk>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category_edit",
    ),
]
