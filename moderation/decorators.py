from django.shortcuts import redirect, reverse

from main.helpers import user_has_groups_any
from main.models import OFFICER, MANAGER, PRESIDENT


def moderators_only(func):
    def wrapper(request, *args, **kwargs):
        if request.user and request.user.is_authenticated:
            if user_has_groups_any(request.user, (OFFICER, MANAGER, PRESIDENT)):
                return func(request, *args, **kwargs)

        return redirect(reverse('main:index'))

    return wrapper
