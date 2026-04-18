from django import template

from core.permissions import can_manage_categories as _can_manage_categories

register = template.Library()


@register.filter
def can_manage_categories(user):
    return _can_manage_categories(user)
