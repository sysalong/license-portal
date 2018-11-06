from datetime import datetime

from django.shortcuts import render, redirect, reverse
from django.http.response import HttpResponseBadRequest

from license_portal.settings import EFILE_URL, MERAS_CLIENT_ID, MERAS_RETURN_URL
from .services import EFileService


def requires_login(func):
    def wrapper(*args, **kwargs):
        request = args[0]

        if not request.session.get('user_id'):
            return redirect(reverse('main:login'))

        return func(*args, **kwargs)

    return wrapper


def load_user_data(request, access_token):
    if not request.session.get('user_username'):
        user_username = EFileService.get_username_by_access_token(access_token)
        request.session['user_username'] = user_username

        if not request.session.get('user_userid'):
            person = EFileService.get_person_by_nid(user_username)

            if person:
                request.session['user_id'] = person['FormalIdentityNumber']
                request.session['user_userid'] = person['UserID']
                request.session['user_firstname'] = person['FirstName']
                request.session['user_secondname'] = person['SecondName']
                request.session['user_thirdname'] = person['ThirdName']
                request.session['user_lastname'] = person['LastName']
                request.session['user_fullname'] = ' '.join([person['FirstName'], person['SecondName'], person['ThirdName'], person['LastName']])
                request.session['user_email'] = person['ContactEmail']
                request.session['user_mobile'] = person['ContactMobile']
                request.session['user_countryid'] = person['CountryID']
                person_birthdate = person['BirthDate']

                if isinstance(person_birthdate, datetime):
                    request.session['user_birthdate'] = str(person_birthdate.date())
                else:
                    request.session['user_birthdate'] = person['BirthDate']

                request.session['user_birthdatehijri'] = person['BirthDateHijri'].strip()

                return True
            else:
                return False


def oauth_return(request):
    access_token = request.GET.get('access_token')
    return_url = request.GET.get('returnUrl')

    if access_token:
        user_authenticated = EFileService.is_authenticated(access_token)
    else:
        return redirect(reverse('main:login'))

    if not user_authenticated:
        return redirect(reverse('main:login'))

    request.session['access_token'] = access_token

    if not load_user_data(request, access_token):
        return HttpResponseBadRequest('Couldn\'t load user data from EFile.')

    return redirect(return_url)


@requires_login
def index(request):
    access_token = request.session.get('access_token')

    if access_token:
        user_authenticated = EFileService.is_authenticated(access_token)
        if user_authenticated:
            return redirect(reverse('main:dashboard'))
        else:
            request.session.flush()
            return redirect(reverse('main:login'))


@requires_login
def dashboard(request):
    access_token = request.session.get('access_token')
    if access_token:
        user_authenticated = EFileService.is_authenticated(access_token)
        if user_authenticated:
            return render(request, 'dashboard.html')
        else:
            request.session.flush()
            return redirect(reverse('main:login'))


def login(request):
    return render(request, 'login.html', {'oauth_url': '{}/account/login?client_id={}&returnUrl={}'.format(EFILE_URL, MERAS_CLIENT_ID, MERAS_RETURN_URL)})


def logout(request):
    access_token = request.session.get('access_token')
    if access_token:
        logged_out = EFileService.logout(access_token)
        if logged_out:
            request.session.flush()

    return redirect(reverse('main:login'))


@requires_login
def terms(request):
    access_token = request.session.get('access_token')
    if access_token:
        print()
    return render(request, 'terms.html')


@requires_login
def choose_type(request):
    return render(request, 'choose_type.html')


@requires_login
def individual_signup(request):
    return render(request, 'individual_signup.html')


@requires_login
def company_signup(request):
    return render(request, 'company_signup.html')
