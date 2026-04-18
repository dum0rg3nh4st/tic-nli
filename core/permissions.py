from django.contrib.auth.models import Group

GROUP_EMPLOYEE = "employee"
GROUP_ANALYST = "analyst"
GROUP_MANAGEMENT = "management"


def user_in_group(user, name: str) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=name).exists()


def can_classify(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if user_in_group(user, GROUP_MANAGEMENT):
        return False
    return (
        user_in_group(user, GROUP_EMPLOYEE)
        or user_in_group(user, GROUP_ANALYST)
        or not user.groups.exists()
    )


def can_manage_categories(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user_in_group(user, GROUP_ANALYST)


def ensure_default_groups():
    for name in (GROUP_EMPLOYEE, GROUP_ANALYST, GROUP_MANAGEMENT):
        Group.objects.get_or_create(name=name)
