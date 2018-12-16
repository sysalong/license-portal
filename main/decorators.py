from django.shortcuts import redirect, reverse
from .services import EFileService
from .helpers import internal_logout, sessdata, user_has_groups_any
from .models import Application, OFFICER, MANAGER, PRESIDENT, FINANCE


def requires_meras_login(func):
    def wrapper(*args, **kwargs):
        request = args[0]

        nid = sessdata(request, 'user_id')
        if not nid:
            return redirect(reverse('main:login'))
        else:
            if request.user and request.user.is_authenticated:
                if user_has_groups_any(request.user, ('officer', 'manager', 'president')):
                    request.session['user_is_moderator'] = True
                    return redirect(reverse('moderation:index'))

            access_token = sessdata(request, 'access_token')
            if access_token:
                user_authenticated = EFileService.is_authenticated(access_token)
                if not user_authenticated:
                    return internal_logout(request)
            else:
                return internal_logout(request)

        return func(*args, **kwargs)

    return wrapper


def terms_agreed(func):
    def wrapper(*args, **kwargs):
        request = args[0]

        if not sessdata(request, 'terms_agreed') and request.method != 'POST':
            return redirect(reverse('main:terms'))

        return func(*args, **kwargs)

    return wrapper


def requires_finished_with_success(func):
    def wrapper(*args, **kwargs):
        request = args[0]

        if not sessdata(request, 'finished_with_success'):
            return redirect(reverse('main:index'))

        return func(*args, **kwargs)

    return wrapper


def user_has_no_applications(func):
    def wrapper(*args, **kwargs):
        request = args[0]

        if sessdata(request, 'user_userid') and request.method != 'POST':
            has_applications = Application.objects.filter(applicant__userid=sessdata(request, 'user_userid')).exists()
            if has_applications:
                return redirect(reverse('main:index'))

        return func(*args, **kwargs)

    return wrapper
