from django.shortcuts import render, redirect, reverse
from django.http.response import HttpResponseBadRequest
from django.contrib import messages

from license_portal.settings import EFILE_URL, MERAS_CLIENT_ID, MERAS_RETURN_URL
from .decorators import requires_meras_login, terms_agreed, requires_finished_with_success, user_has_no_applications
from .helpers import load_user_data, internal_logout, sessdata, verify_image, verify_pdf, action_history_log
from .services import EFileService
from .models import *


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

    has_applications = Application.objects.filter(applicant__id_number=sessdata(request, 'user_id')).exists()

    if return_url and return_url == reverse('moderation:index'):  # TODO: remove this line after development is done
        return redirect(reverse('moderation:index'))  # TODO: remove this line after development is done

    if not has_applications:
        if return_url and return_url == reverse('moderation:index'):
            return redirect(reverse('moderation:index'))

        return redirect(reverse('main:terms'))

    return redirect(MERAS_RETURN_URL)


@requires_meras_login
def index(request):
    return redirect(reverse('main:dashboard'))
    # access_token = request.session.get('access_token')
    # print('user_id', request.session.get('user_id'))
    #
    # if access_token:
    #     user_authenticated = EFileService.is_authenticated(access_token)
    #     print('index:user_authenticated -> ', user_authenticated)
    #     if not user_authenticated:
    #         return redirect(reverse('main:dashboard'))
    #     else:
    #         request.session.clear()
    #         request.session.flush()
    #         return redirect(reverse('main:login'))


@requires_meras_login
def dashboard(request):
    access_token = sessdata(request, 'access_token')
    if access_token:
        user_authenticated = EFileService.is_authenticated(access_token)
        if user_authenticated:
            user = Applicant.objects.filter(userid=sessdata(request, 'user_userid')).first()
            if not user:
                return redirect(reverse('main:terms'))
            return render(request, 'dashboard.html', {'applications': user.applications.all(), 'ApplicationStatus': ApplicationStatus})
        else:
            return internal_logout(request)


def login(request):
    if sessdata(request, 'user_userid'):
        return redirect(reverse('main:index'))

    return render(request, 'login.html', {'oauth_url': '{}/account/login?client_id={}&returnUrl={}'.format(EFILE_URL, MERAS_CLIENT_ID, MERAS_RETURN_URL)})


def logout(request):
    access_token = sessdata(request, 'access_token')
    if access_token:
        user_authenticated = EFileService.is_authenticated(access_token)
        print('logout:user_authenticated -> ', user_authenticated)

        if not user_authenticated:
            return internal_logout(request)

        logged_out = EFileService.logout(access_token)
        print('logged_out --->', logged_out)
        if logged_out is True:
            return internal_logout(request)
        else:
            return HttpResponseBadRequest('Error logging out from Meras.')
    else:
        if request.user.is_authenticated:
            internal_logout(request)

    return redirect(reverse('main:login'))


@requires_meras_login
@user_has_no_applications
def terms(request):
    # access_token = request.session.get('access_token')

    if request.method == 'POST':
        agreed = request.POST.get('terms_agree')
        if agreed and agreed == 'on':
            request.session['terms_agreed'] = True
            return redirect(reverse('main:choose_type'))

    return render(request, 'terms.html')


@requires_meras_login
@terms_agreed
@user_has_no_applications
def choose_type(request):
    return render(request, 'choose_type.html')


@requires_meras_login
@terms_agreed
@user_has_no_applications
def individual_signup(request):
    updating = request.POST.get('_updating', 'false') == 'true'

    if request.method == 'POST':
        doc_id = request.FILES.get('doc-id')
        doc_graduation = request.FILES.get('doc-graduation')
        doc_expertise_list = request.FILES.getlist('doc-expertise')
        doc_resume = request.FILES.get('doc-resume')
        doc_additional = request.FILES.get('doc-additional')

        all_valid = True

        if not doc_id or not doc_graduation or not doc_expertise_list or not doc_resume:
            messages.error(request, message='برجاء ملئ جميع الحقول المطلوبة')
            all_valid = False
        else:
            if not verify_image(doc_id):
                messages.error(request, message='صورة الهوية ليست في صيغة صحيحة')
                all_valid = False
            else:
                if not verify_image(doc_graduation):
                    messages.error(request, message='صورة المؤهل الأكاديمي ليست في صيغة صحيحة')
                    all_valid = False
                else:
                    doc_expertise_valid = True
                    for file in doc_expertise_list:
                        if not verify_pdf(file):
                            doc_expertise_valid = False
                            break

                    if not doc_expertise_valid:
                        messages.error(request, message='ملف شهادات الخبرة ليس في صيغة صحيحة')
                        all_valid = False
                    else:
                        if not verify_pdf(doc_resume):
                            messages.error(request, message='ملف السيرة الذاتية ليس في صيغة صحيحة')
                            all_valid = False
                        else:
                            if doc_additional:
                                if not verify_pdf(doc_additional):
                                    messages.error(request, message='ملف المستندات الإضافية ليس في صيغة صحيحة')
                                    all_valid = False

        if all_valid:
            if updating:
                applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()
            else:
                applicant = Applicant(id_number=sessdata(request, 'user_id'),
                                      username=sessdata(request, 'user_username'),
                                      userid=sessdata(request, 'user_userid'),
                                      first_name=sessdata(request, 'user_firstname'),
                                      second_name=sessdata(request, 'user_secondname'),
                                      third_name=sessdata(request, 'user_thirdname'),
                                      last_name=sessdata(request, 'user_lastname'),
                                      email=sessdata(request, 'user_email'),
                                      mobile=sessdata(request, 'user_mobile'),
                                      phonecode=sessdata(request, 'user_phonecodeid'),
                                      countryid=sessdata(request, 'user_countryid'),
                                      birthdate=sessdata(request, 'user_birthdate'),
                                      birthdatehijri=sessdata(request, 'user_birthdatehijri').replace('/', '-'),
                                      legal_status=sessdata(request, 'user_legalstatus'),
                                      person_type=sessdata(request, 'user_persontype'),
                                      gender=sessdata(request, 'user_gender'),
                                      has_wasel_account=sessdata(request, 'HasWaselAccount') if sessdata(request,
                                                                                                         'HasWaselAccount') else False,
                                      usertype=ApplicantType.objects.get(value=ApplicantType.INDIVIDUAL),
                                      )
                applicant.save()
            if not applicant.id:
                messages.error(request, message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
            else:
                if updating:
                    application = Application.objects.filter(serial='A' + applicant.id_number).order_by('created_at').last()
                else:
                    application_serial = 'A' + applicant.id_number
                    application = Application(serial=application_serial, status=ApplicationStatus.objects.get(value=ApplicationStatus.NEW),
                                              applicant=applicant, service=Service.objects.get(type=Service.NEW))
                    application.save()
                if not application.id:
                    messages.error(request, message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                    applicant.delete()
                else:
                    if updating:
                        application.documents.all().delete()

                    doc_id_obj = ApplicationDocument(file=doc_id, application=application,
                                                     description='صورة الهوية', file_type=ApplicationDocument.TYPES['IMAGE'])
                    doc_id_obj.save()
                    if not doc_id_obj.id:
                        messages.error(request, message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                        application.delete()
                        applicant.delete()
                    else:
                        doc_graduation_obj = ApplicationDocument(file=doc_graduation, application=application,
                                                         description='صورة المؤهل الأكاديمي', file_type=ApplicationDocument.TYPES['IMAGE'])
                        doc_graduation_obj.save()
                        if not doc_graduation_obj.id:
                            messages.error(request,
                                           message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                            doc_id_obj.delete()
                            application.delete()
                            applicant.delete()
                        else:
                            doc_resume_obj = ApplicationDocument(file=doc_resume, application=application,
                                                                     description='السيرة الذاتية', file_type=ApplicationDocument.TYPES['PDF'])
                            doc_resume_obj.save()
                            if not doc_resume_obj.id:
                                messages.error(request,
                                               message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                doc_graduation_obj.delete()
                                doc_id_obj.delete()
                                application.delete()
                                applicant.delete()
                            else:
                                success_upload = []
                                for file in doc_expertise_list:
                                    file_obj = ApplicationDocument(file=file, application=application,
                                                             description='شهادات الخبرات', file_type=ApplicationDocument.TYPES['PDF'])
                                    file_obj.save()
                                    if not file_obj.id:
                                        messages.error(request,
                                                       message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                        for f in success_upload:
                                            f.delete()
                                        doc_resume_obj.delete()
                                        doc_graduation_obj.delete()
                                        doc_id_obj.delete()
                                        application.delete()
                                        applicant.delete()
                                        break
                                    else:
                                        success_upload.append(file)

                                if doc_additional:
                                    doc_additional_obj = ApplicationDocument(file=doc_additional, application=application,
                                                                             description='مستندات إضافية', file_type=ApplicationDocument.TYPES['PDF'])
                                    doc_additional_obj.save()
                                    if not doc_additional_obj.id:
                                        messages.error(request,
                                                       message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                        for f in success_upload:
                                            f.delete()
                                        doc_resume_obj.delete()
                                        doc_graduation_obj.delete()
                                        doc_id_obj.delete()
                                        application.delete()
                                        applicant.delete()

                                request.session['finished_with_success'] = ApplicantType.INDIVIDUAL
                                if updating:
                                    application.return_reason = None
                                    application.status = ApplicationStatus.objects.get(value=ApplicationStatus.IN_REVISION)
                                    application.save()
                                    action_history_log(application, None, 'قام بتحديث طلبه')

                                return redirect(reverse('main:success'))

    storage = messages.get_messages(request)
    msgs = [msg for msg in storage]
    storage.used = True

    template_name = 'individual_signup.html'
    if updating:
        template_name = 'individual_view.html'

    return render(request, template_name, {'error': msgs[0] if msgs else None})


@requires_meras_login
@terms_agreed
@user_has_no_applications
def company_signup(request):
    if request.method == 'POST':
        return redirect(reverse('main:review'))

    return render(request, 'company_signup.html')


@requires_meras_login
@requires_finished_with_success
def success(request):
    applicant_type = request.session.get('finished_with_success')
    request.session['finished_with_success'] = None
    return render(request, 'request_success.html', {'applicant_type': applicant_type, 'ApplicantType': ApplicantType})


@requires_meras_login
def view_application(request, id):
    application = Application.objects.filter(id=id, applicant=Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()).first()
    if not application or application and application.status.value != ApplicationStatus.RETURNED:
        return redirect(reverse('main:index'))

    return render(request, 'individual_view.html', {'application': application})
