from django.shortcuts import render, redirect, reverse
from django.http.response import HttpResponseBadRequest
from django.contrib import messages

from license_portal.settings import EFILE_URL, MERAS_CLIENT_ID, MERAS_RETURN_URL
from .decorators import requires_meras_login, terms_agreed, requires_finished_with_success, user_has_no_applications
from .helpers import load_user_data, internal_logout, sessdata, verify_image, verify_pdf, action_history_log
from .services import EFileService, WathiqService
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
            if not user or user and user.applications.count() == 0:
                return redirect(reverse('main:terms'))
            return render(request, 'dashboard.html', {'applications': user.applications.all(),
                                                      'ApplicationStatus': ApplicationStatus,
                                                      'view_statuses': (ApplicationStatus.RETURNED, ApplicationStatus.REJECTED)})
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
def choose_type(request):
    return render(request, 'choose_type.html')


@requires_meras_login
@terms_agreed
@user_has_no_applications
def individual_signup(request):
    # TODO: ask:: should the application go into in_revision state right after the applicant updates the docs or only when the officer role views it
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
            applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()
            if not applicant:
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
                                      type=ApplicantType.objects.get(value=ApplicantType.INDIVIDUAL),
                                      )
                applicant.save()
            if not applicant.id:
                all_valid = False
                messages.error(request, message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
            else:
                if updating:
                    application = Application.objects.filter(serial='A' + applicant.id_number).first()
                else:
                    application_serial = 'A' + applicant.id_number
                    application = Application(serial=application_serial, status=ApplicationStatus.objects.get(value=ApplicationStatus.NEW),
                                              applicant=applicant, service=Service.objects.get(type=Service.NEW))
                    application.save()
                if not application.id:
                    all_valid = False
                    messages.error(request, message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                    applicant.delete()
                else:
                    if updating:
                        application.documents.all().delete()

                    doc_id_obj = ApplicationDocument(file=doc_id, application=application,
                                                     description='صورة الهوية', file_type=ApplicationDocument.TYPES['IMAGE'])
                    doc_id_obj.save()
                    if not doc_id_obj.id:
                        all_valid = False
                        messages.error(request, message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                        application.delete()
                        applicant.delete()
                    else:
                        doc_graduation_obj = ApplicationDocument(file=doc_graduation, application=application,
                                                         description='صورة المؤهل الأكاديمي', file_type=ApplicationDocument.TYPES['IMAGE'])
                        doc_graduation_obj.save()
                        if not doc_graduation_obj.id:
                            all_valid = False
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
                                all_valid = False
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
                                        all_valid = False
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
                                        all_valid = False
                                        messages.error(request,
                                                       message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                        for f in success_upload:
                                            f.delete()
                                        doc_resume_obj.delete()
                                        doc_graduation_obj.delete()
                                        doc_id_obj.delete()
                                        application.delete()
                                        applicant.delete()

                                if all_valid:
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
    def verify_cr(cr):
        crs = sessdata(request, 'crs')

        if not crs:
            return False

        for crr in crs:
            if crr['CR'] == cr:
                return crr

        return False

    updating = request.POST.get('_updating', 'false') == 'true'

    crs = sessdata(request, 'crs')
    has_cr = False

    if not crs:
        nid = request.session.get('user_id')
        if nid:
            has_cr = WathiqService.has_cr_by_id(nid)
            request.session['has_cr'] = has_cr

            if has_cr is True:
                crs = WathiqService.get_crs_by_id(nid)

                if crs:
                    request.session['crs'] = crs
                else:
                    crs = False
            else:
                has_cr = False
                crs = False
        else:
            return internal_logout(request)
    else:
        has_cr = True

    if request.method == 'POST':
        doc_cr = request.FILES.get('doc-cr')
        doc_est = request.FILES.get('doc-est')
        doc_saudiation = request.FILES.get('doc-saudiation')
        doc_manhierarchy = request.FILES.get('doc-manhierarchy')
        doc_prevproj = request.FILES.get('doc-prevproj')
        doc_income = request.FILES.get('doc-income')
        doc_additional = request.FILES.get('doc-additional')

        crno = request.POST.get('_crno')
        cr_info = verify_cr(crno)

        all_valid = True

        if not crno or not cr_info or not doc_cr or not doc_est or not doc_saudiation or not doc_manhierarchy or not doc_prevproj or not doc_income:
            messages.error(request, message='برجاء ملئ جميع الحقول المطلوبة')
            all_valid = False
        else:
            if not verify_image(doc_cr):
                messages.error(request, message='صورة السجل التجاري ليست في صيغة صحيحة')
                all_valid = False
            else:
                if not verify_image(doc_est):
                    messages.error(request, message='صورة عقد التأسيس ليست في صيغة صحيحة')
                    all_valid = False
                else:
                    if not verify_image(doc_saudiation):
                        messages.error(request, message='صورة شهادة السعودة ليست في صيغة صحيحة')
                        all_valid = False
                    else:
                        if not verify_image(doc_manhierarchy):
                            messages.error(request, message='صورة الهيكل التنظيمي ليست في صيغة صحيحة')
                            all_valid = False
                        else:
                            if not verify_image(doc_prevproj):
                                messages.error(request, message='ملف بالمشاريع السابقة ليس في صيغة صحيحة')
                                all_valid = False
                            else:
                                if not verify_image(doc_income):
                                    messages.error(request, message='صورة شهادة من الزكاة والدخل ليست في صيغة صحيحة')
                                    all_valid = False
                                else:
                                    if doc_additional:
                                        if not verify_pdf(doc_additional):
                                            messages.error(request, message='ملف المستندات الإضافية ليس في صيغة صحيحة')
                                            all_valid = False

        if all_valid:
            applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()
            if not applicant:
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
                                      type=ApplicantType.objects.get(value=ApplicantType.COMPANY),
                                      )
                applicant.save()
            if not applicant.id:
                all_valid = False
                messages.error(request,
                               message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
            else:
                if updating:
                    app_id = request.POST.get('_id')
                    if not app_id:
                        return HttpResponseBadRequest()
                    application = Application.objects.filter(id=app_id, serial='C' + crno).first()
                    if application and application.status.value != ApplicationStatus.RETURNED:
                        return redirect(reverse('main:index'))
                else:
                    application_serial = 'C' + crno
                    application = Application(serial=application_serial, status=ApplicationStatus.objects.get(value=ApplicationStatus.NEW),
                                              applicant=applicant, service=Service.objects.get(type=Service.NEW))
                    application.save()
                if not application.id:
                    all_valid = False
                    messages.error(request, message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                    applicant.delete()
                else:
                    if updating:
                        application.documents.all().delete()

                    doc_cr_obj = ApplicationDocument(file=doc_cr, application=application,
                                                     description='صورة السجل التجاري',
                                                     file_type=ApplicationDocument.TYPES['IMAGE'])
                    doc_cr_obj.save()
                    if not doc_cr_obj.id:
                        all_valid = False
                        messages.error(request,
                                       message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                        application.delete()
                        applicant.delete()
                    else:
                        doc_est_obj = ApplicationDocument(file=doc_est, application=application,
                                                         description='صورة عقد التأسيس',
                                                         file_type=ApplicationDocument.TYPES['IMAGE'])
                        doc_est_obj.save()
                        if not doc_est_obj.id:
                            all_valid = False
                            messages.error(request,
                                           message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                            doc_cr_obj.delete()
                            application.delete()
                            applicant.delete()
                        else:
                            doc_saudiation_obj = ApplicationDocument(file=doc_saudiation, application=application, description='صورة شهادة السعودة', file_type=ApplicationDocument.TYPES['IMAGE'])
                            doc_saudiation_obj.save()
                            if not doc_saudiation_obj.id:
                                all_valid = False
                                messages.error(request,
                                               message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                doc_est_obj.delete()
                                doc_cr_obj.delete()
                                application.delete()
                                applicant.delete()
                            else:
                                doc_manhierarchy_obj = ApplicationDocument(file=doc_manhierarchy, application=application, description='صورة الهيكل التنظيمي', file_type=ApplicationDocument.TYPES['IMAGE'])
                                doc_manhierarchy_obj.save()
                                if not doc_manhierarchy_obj.id:
                                    all_valid = False
                                    messages.error(request,
                                                   message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                    doc_saudiation_obj.delete()
                                    doc_est_obj.delete()
                                    doc_cr_obj.delete()
                                    application.delete()
                                    applicant.delete()
                                else:
                                    doc_prevproj_obj = ApplicationDocument(file=doc_prevproj, application=application, description='مستند بالمشاريع السابقة', file_type=ApplicationDocument.TYPES['IMAGE'])
                                    doc_prevproj_obj.save()
                                    if not doc_prevproj_obj.id:
                                        all_valid = False
                                        messages.error(request,
                                                       message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                        doc_manhierarchy_obj.delete()
                                        doc_est_obj.delete()
                                        doc_cr_obj.delete()
                                        application.delete()
                                        applicant.delete()
                                    else:
                                        doc_income_obj = ApplicationDocument(file=doc_income, application=application, description='صورة شهادة من الزكاة والدخل', file_type=ApplicationDocument.TYPES['IMAGE'])
                                        doc_income_obj.save()
                                        if not doc_income_obj.id:
                                            all_valid = False
                                            messages.error(request,
                                                           message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                            doc_prevproj_obj.delete()
                                            doc_manhierarchy_obj.delete()
                                            doc_est_obj.delete()
                                            doc_cr_obj.delete()
                                            application.delete()
                                            applicant.delete()

                                        if doc_additional:
                                            doc_additional_obj = ApplicationDocument(file=doc_additional, application=application, description='مستندات إضافية', file_type=ApplicationDocument.TYPES['PDF'])
                                            doc_additional_obj.save()
                                            if not doc_additional_obj.id:
                                                all_valid = False
                                                messages.error(request, message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                                doc_income_obj.delete()
                                                doc_prevproj_obj.delete()
                                                doc_manhierarchy_obj.delete()
                                                doc_est_obj.delete()
                                                doc_cr_obj.delete()
                                                application.delete()
                                                applicant.delete()

                                        if all_valid:
                                            if not updating:
                                                cr = CommercialRecord.objects.filter(number=crno).first()
                                                if not cr:
                                                    cr = CommercialRecord(number=cr_info['CR'], business_type_id=cr_info['BusTypeID'])
                                                    cr.save()

                                                if not cr.id:
                                                    all_valid = False
                                                    messages.error(request,
                                                                   message='حدث خطأ أثناء عملية الحفظ، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                                    application.documents.all().delete()
                                                    application.delete()
                                                    applicant.delete()
                                                else:
                                                    acr = ApplicantCommercialRecord.objects.filter(applicant=applicant,
                                                                                             commercial_record=cr).first()
                                                    if acr:
                                                        acr.relation_id = cr_info['RelationID']
                                                        acr.save()
                                                    else:
                                                        acr = ApplicantCommercialRecord.objects.create(applicant=applicant,
                                                                                             commercial_record=cr,
                                                                                             relation_id=cr_info[
                                                                                                 'RelationID'])
                                                    if not acr.id:
                                                        all_valid = False
                                                        messages.error(request,
                                                                       message='حدث خطأ أثناء عملية الحفظ، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                                        application.documents.all().delete()
                                                        application.delete()
                                                        applicant.delete()
                                                    else:
                                                        application.commercial_record = cr
                                                        application.save()

                                        if all_valid:
                                            request.session['finished_with_success'] = ApplicantType.COMPANY
                                            if updating:
                                                application.return_reason = None
                                                application.status = ApplicationStatus.objects.get(
                                                    value=ApplicationStatus.IN_REVISION)
                                                application.save()
                                                action_history_log(application, None, 'قام بتحديث طلبه')

                                            return redirect(reverse('main:success'))

    storage = messages.get_messages(request)
    msgs = [msg for msg in storage]
    storage.used = True

    template_name = 'company_signup.html'
    if updating:
        template_name = 'company_view.html'

    return render(request, template_name, {'has_cr': has_cr, 'crs': crs, 'error': msgs[0] if msgs else None})


@requires_meras_login
@requires_finished_with_success
def success(request):
    applicant_type = request.session.get('finished_with_success')
    request.session['finished_with_success'] = None
    return render(request, 'request_success.html', {'applicant_type': applicant_type, 'ApplicantType': ApplicantType})


@requires_meras_login
def view_application(request, id):
    applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()
    application = Application.objects.filter(id=id, applicant=applicant).first()

    if not application or application and application.status.value not in (ApplicationStatus.RETURNED, ApplicationStatus.REJECTED):
        return redirect(reverse('main:index'))

    applicant_type = applicant.type.value

    context = {'application': application, 'ApplicationStatus': ApplicationStatus}

    if applicant_type == ApplicantType.COMPANY:
        context['CR'] = application.commercial_record
        context['applicant_application_cr'] = applicant.applicant_crs.filter(
            commercial_record=application.commercial_record).first()

    if applicant_type == ApplicantType.INDIVIDUAL:
        return render(request, 'individual_view.html', context)
    elif applicant_type == ApplicantType.COMPANY:
        return render(request, 'company_view.html', context)


def payment_directions(request, id):
    applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()
    application = Application.objects.filter(id=id, applicant=applicant).first()

    if not application or application and application.status.value != ApplicationStatus.PENDING_PAYMENT:
        return redirect(reverse('main:index'))

    applicant_type = applicant.type.value

    return render(request, 'payment_directions.html', {'application': application})
