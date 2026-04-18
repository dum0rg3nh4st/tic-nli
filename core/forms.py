from django import forms

from .models import Category


class TextClassificationForm(forms.Form):
    content = forms.CharField(
        label="Текст для классификации",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 8,
                "placeholder": "Введите текст от 10 до 5000 символов…",
            }
        ),
        min_length=10,
        max_length=5000,
    )


class HistoryFilterForm(forms.Form):
    category = forms.ModelChoiceField(
        label="Категория",
        queryset=Category.objects.none(),
        required=False,
        empty_label="Все категории",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    date_from = forms.DateField(
        label="Дата с",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    date_to = forms.DateField(
        label="Дата по",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all().order_by("name")


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }
