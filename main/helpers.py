from datetime import datetime

from django.shortcuts import redirect, reverse
from django.contrib.auth.models import User
from django.contrib.auth import logout

from PIL import Image
from PyPDF2 import PdfFileReader
from PyPDF2.utils import PdfReadError

from .services import EFileService
from .models import TargetType, ActionHistoryEntry


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
                request.session['user_phonecodeid'] = person['TelephoneCodeID']
                request.session['user_countryid'] = person['CountryID']
                request.session['user_legalstatus'] = person['LegalStatus']
                request.session['user_persontype'] = person['PersonType']
                request.session['user_gender'] = person['Gender']
                request.session['user_haswaselaccount'] = person['HasWaselAccount']
                person_birthdate = person['BirthDate']

                if isinstance(person_birthdate, datetime):
                    request.session['user_birthdate'] = str(person_birthdate.date())
                else:
                    request.session['user_birthdate'] = person['BirthDate']

                request.session['user_birthdatehijri'] = person['BirthDateHijri'].strip()

                return True
            else:
                return False

    return True


def internal_logout(request):
    if request.user:
        logout(request)

    access_token = request.GET.get('access_token')
    if access_token:
        EFileService.logout(access_token)

    request.session.clear()
    request.session.flush()

    return redirect(reverse('main:login'))


def sessdata(request, key, default=None):
    return request.session.get(key, default)


def verify_image(file):
    try:
        Image.open(file)
        return True
    except:
        return False


def verify_pdf(file):
    try:
        PdfFileReader(file)
        return True
    except PdfReadError:
        return False


def user_has_group(user, groupname):
    return User.objects.filter(pk=user.pk, groups__name=groupname).exists()


def user_has_groups_any(user, grouplist):
    return User.objects.filter(pk=user.pk, groups__name__in=grouplist).exists()


def user_has_groups_all(user, grouplist):
    return User.objects.filter(pk=user.pk, groups__name__in=grouplist).count() == len(grouplist)


def action_history_log(target_obj, invoker_obj, text):
    targettype = TargetType.objects.get(value=getattr(TargetType, target_obj.__class__.__name__.upper()))
    entry = ActionHistoryEntry(text=text, invoker=invoker_obj, target=target_obj.id, target_type=targettype)
    entry.save()
