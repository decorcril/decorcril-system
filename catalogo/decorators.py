from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps


def group_required(*group_names):
    """Requer que usuário pertença a um dos grupos"""

    def in_groups(u):
        if u.is_authenticated:
            if u.groups.filter(name__in=group_names).exists():
                return True
        return False

    return user_passes_test(in_groups, login_url="login")
