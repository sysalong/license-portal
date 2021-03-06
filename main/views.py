from django.shortcuts import render, redirect, reverse
from django.http.response import HttpResponseBadRequest, HttpResponse, HttpResponseNotFound
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import get_template

from license_portal.settings import EFILE_URL, MERAS_CLIENT_ID, MERAS_RETURN_URL
from .decorators import requires_meras_login, terms_agreed, requires_finished_with_success, user_has_no_applications, redirect_moderators, user_has_no_applications_of_type
from .helpers import load_user_data, internal_logout, sessdata, verify_image, verify_pdf, action_history_log, user_has_groups_any
from .services import EFileService, WathiqService
from .models import *

from moderation.views import generate_license_pdf

from license_portal.utils import decrypt_base64decode


@redirect_moderators
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
    request.session['has_applications'] = has_applications

    if not has_applications:
        return redirect(reverse('main:terms'))

    return redirect(MERAS_RETURN_URL)


@redirect_moderators
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


@redirect_moderators
@requires_meras_login
def dashboard(request):
    user = Applicant.objects.filter(userid=sessdata(request, 'user_userid')).first()
    if not user or user and user.applications.count() == 0:
        return redirect(reverse('main:terms'))

    if request.user and request.user.is_authenticated:
        request.session['user_is_moderator'] = user_has_groups_any(request.user, (OFFICER, MANAGER, PRESIDENT, FINANCE))

    return render(request, 'dashboard.html', {'applications': user.applications.all(),
                                              'ApplicationStatus': ApplicationStatus,
                                              'view_statuses': (ApplicationStatus.RETURNED, ApplicationStatus.REJECTED,
                                                                ApplicationStatus.PENDING_PAYMENT_RETURNED),
                                              'active_link': 'applications'})


@redirect_moderators
@requires_meras_login
def licenses(request):
    user = Applicant.objects.filter(userid=sessdata(request, 'user_userid')).first()
    if not user or user and user.licenses.count() == 0:
        return redirect(reverse('main:index'))

    return render(request, 'licenses.html', {'licenses': user.licenses.all(), 'active_link': 'licenses'})


@redirect_moderators
def login(request):
    if sessdata(request, 'user_userid'):
        return redirect(reverse('main:index'))

    return redirect('{}/account/login?client_id={}&referrer=Meras&returnUrl={}'.format(EFILE_URL, MERAS_CLIENT_ID, MERAS_RETURN_URL))
    # return render(request, 'login.html', {'oauth_url': '{}/account/login?client_id={}&returnUrl={}'.format(EFILE_URL, MERAS_CLIENT_ID, MERAS_RETURN_URL)})


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


@redirect_moderators
@requires_meras_login
def terms(request):
    # access_token = request.session.get('access_token')

    if request.method == 'POST':
        agreed = request.POST.get('terms_agree')
        if agreed and agreed == 'on':
            request.session['terms_agreed'] = True
            return redirect(reverse('main:choose_type'))

    return render(request, 'terms.html')


@redirect_moderators
@requires_meras_login
@terms_agreed
def choose_type(request):
    nid = request.session.get('user_id')
    context = {}
    if nid:
        applicant = Applicant.objects.filter(id_number=nid).first()
        if applicant:
            has_indapplication = applicant.applications.filter(type=ApplicationType.INDIVIDUAL).exists()

            if has_indapplication:
                context['ind_disabled'] = True

    return render(request, 'choose_type.html', context)


@redirect_moderators
@requires_meras_login
@terms_agreed
@user_has_no_applications
@user_has_no_applications_of_type(applicationtype=ApplicationType.INDIVIDUAL)
def individual_signup(request):
    updating = request.POST.get('_updating', 'false') == 'true'

    if request.method == 'POST':
        ## doc_id = request.FILES.get('doc-id')
        doc_graduation = request.FILES.get('doc-graduation')
        doc_expertise_list = request.FILES.getlist('doc-expertise')
        doc_resume = request.FILES.get('doc-resume')
        doc_additional = request.FILES.get('doc-additional')

        all_valid = True

        if not updating:
            if not doc_graduation or not doc_expertise_list or not doc_resume:
                messages.error(request, message='برجاء ملئ جميع الحقول المطلوبة')
                all_valid = False
            else:
                if not verify_image(doc_graduation) and not verify_pdf(doc_graduation):
                    messages.error(request, message='ملف المؤهل الأكاديمي ليس في صيغة صحيحة')
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
                                              applicant=applicant, service=Service.objects.get(type=Service.NEW),
                                              type=ApplicationType.objects.get(value=ApplicationType.INDIVIDUAL),)
                    application.save()
                if not application.id:
                    all_valid = False
                    messages.error(request, message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                    if not updating:
                        applicant.delete()
                else:
                    if updating:
                        returned_files_ids = request.POST.getlist('returned-files[]')

                        if returned_files_ids != []:
                            for id in returned_files_ids:
                                fileblob = request.FILES.get('returned-file-' + id)
                                try:
                                    filetype = int(request.POST.get('returned-file-type-' + id, 0))
                                except ValueError:
                                    filetype = 0

                                fileobj = application.documents.filter(id=id).first()
                                if fileblob:
                                    if not filetype or filetype not in tuple(ApplicationDocument.TYPES.values()) or filetype != fileobj.file_type:
                                        all_valid = False
                                        break
                                    else:
                                        if filetype == ApplicationDocument.TYPES['IMAGE'] and not verify_image(fileblob) or filetype == ApplicationDocument.TYPES['PDF'] and not verify_pdf(fileblob) or filetype == ApplicationDocument.TYPES['HYBRID'] and not verify_pdf(fileblob) and not verify_image(fileblob):
                                            all_valid = False
                                            break
                                        else:
                                            if fileobj:
                                                fileobj.file = fileblob
                                                # fileobj.returned = False
                                                fileobj.save()
                                            else:
                                                all_valid = False
                                                break
                                else:
                                    if not fileobj or fileobj and fileobj.is_required:
                                        all_valid = False
                                        break
                                    else:
                                        fileobj.returned = False
                                        fileobj.save()
                        else:
                            all_valid = False

                        if not all_valid:
                            messages.error(request,
                                           message='حدث خطأ أثناء عملية رفع الملفات، يرجى التأكد من صحة الملفات والمحاولة مرة أخرى')
                        # application.documents.all().delete()
                    else:
                        doc_graduation_obj = ApplicationDocument(file=doc_graduation, application=application,
                                                         description='المؤهل الأكاديمي', file_type=ApplicationDocument.TYPES['HYBRID'])
                        doc_graduation_obj.save()
                        if not doc_graduation_obj.id:
                            all_valid = False
                            messages.error(request,
                                           message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
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
                                        application.delete()
                                        applicant.delete()

                    if all_valid:
                        request.session['finished_with_success'] = ApplicationType.INDIVIDUAL
                        if updating:
                            application.return_reason = None
                            if application.paid_on and application.status == ApplicationStatus.objects.get(value=ApplicationStatus.RETURNED):
                                application.status = ApplicationStatus.objects.get(value=ApplicationStatus.PAYMENT_APPROVED)
                            else:
                                application.status = ApplicationStatus.objects.get(value=ApplicationStatus.IN_REVISION)
                            application.save()
                            action_history_log(application, None, 'قام بتحديث طلبه')

                        try:
                            subject = 'التراخيص الاحصائية | تم استلام طلبك'
                            sender = 'support@email.com'
                            # receiver = [applicant.email]  # for after dev
                            receiver = ['oyounis@stats.gov.sa']  # for test purposes TODO: remove in production -- and staging when asked
                            email_context = {'applicant': applicant, 'request_host': request.get_host()}

                            message = get_template('email/new_request.html').render(email_context)
                            send_mail(subject, message, sender, receiver, fail_silently=False, html_message=message)
                        except:
                            pass

                        return redirect(reverse('main:success'))

    if updating and not all_valid and application:
        return redirect('main:view_application', id=application.id)
        # template_name = 'individual_view.html'

    storage = messages.get_messages(request)
    msgs = [msg for msg in storage]

    template_name = 'individual_signup.html'

    return render(request, template_name, {'error': msgs[0] if msgs else None})


@redirect_moderators
@requires_meras_login
@terms_agreed
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

    nid = request.session.get('user_id')

    if not crs:
        if nid:
            has_cr = WathiqService.has_cr_by_id(nid)
            print('company_signup:has_cr -> ', has_cr)
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
        ## doc_cr = request.FILES.get('doc-cr')
        doc_est = request.FILES.get('doc-est')
        doc_saudiation = request.FILES.get('doc-saudiation')
        doc_manhierarchy = request.FILES.get('doc-manhierarchy')
        doc_prevproj = request.FILES.get('doc-prevproj')
        doc_income = request.FILES.get('doc-income')
        doc_additional = request.FILES.get('doc-additional')

        crno = request.POST.get('_crno')
        cr_info = verify_cr(crno)

        all_valid = True

        cr_data = WathiqService.get_cr_data_by_cr(crno)
        if not cr_data:
            all_valid = False
            has_cr = False
            crs = []

        all_valid = True  # TODO: DEV ONLY
        has_cr = True  # TODO: DEV ONLY

        cr_info = {  # TODO: DEV ONLY
            'BusType': 'تــــوصية بســـيطة',
            'BusTypeID': 201,
            'CR': '5950011517',
            'ID': '1024901843',
            'RelationID': 3,
            'RelationName': 'شريك متضامن'
        }
        cr_data = {  # TODO: DEV ONLY
            'Activities': 'تجـارة الجمله والتجزئـه في الكفـرات والأسـاتك والشـنابر ,,,,,,,',
            'Address': 'نجران - العريسة - شارع الملك عبدالعزيز',
            'BusType': 'تــــوصية بســـيطة',
            'BusTypeID': 201,
            'CR': '5950011517',
            'CRLocation': 'نجران',
            'CRLocationID': 5950,
            'CRNationalNO': None,
            'Capital': 10001600.0,
            'CreationDate': '14280126',
            'ExpiredDate': '14400126',
            'Fax': '0174727753',
            'IsMain': False,
            'Name': 'فرع شركة خالد عبدالله الصافي واخوانة',
            'POBOX': '000505',
            'PhoneNumber': '0174727750',
            'Status': 'ACTIVE',
            'ZipCode': '11421'
        }

        if not crno or not cr_info:
            messages.error(request, message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
            all_valid = False
        else:
            if not updating:
                if not doc_est or not doc_saudiation or not doc_manhierarchy or not doc_prevproj or not doc_income:
                    messages.error(request, message='برجاء ملئ جميع الحقول المطلوبة')
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
                                              applicant=applicant, service=Service.objects.get(type=Service.NEW),
                                              type=ApplicationType.objects.get(value=ApplicationType.COMPANY),)
                    application.save()
                if not application.id:
                    all_valid = False
                    messages.error(request, message='حدث خطأ أثناء عملية التسجيل، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                    if not updating:
                        applicant.delete()
                else:
                    if updating:
                        returned_files_ids = request.POST.getlist('returned-files[]')

                        if returned_files_ids != []:
                            for id in returned_files_ids:
                                fileblob = request.FILES.get('returned-file-' + id)
                                try:
                                    filetype = int(request.POST.get('returned-file-type-' + id, 0))
                                except ValueError:
                                    filetype = 0

                                fileobj = application.documents.filter(id=id).first()
                                if fileblob:
                                    if not filetype or filetype not in tuple(ApplicationDocument.TYPES.values()) or filetype != fileobj.file_type:
                                        all_valid = False
                                        break
                                    else:
                                        if filetype == ApplicationDocument.TYPES['IMAGE'] and not verify_image(fileblob) or filetype == ApplicationDocument.TYPES['PDF'] and not verify_pdf(fileblob):
                                            all_valid = False
                                            break
                                        else:
                                            if fileobj:
                                                fileobj.file = fileblob
                                                # fileobj.returned = False
                                                fileobj.save()
                                            else:
                                                all_valid = False
                                                break
                                else:
                                    if not fileobj or fileobj and fileobj.is_required:
                                        all_valid = False
                                        break
                                    else:
                                        fileobj.returned = False
                                        fileobj.save()
                        else:
                            all_valid = False

                        if not all_valid:
                            messages.error(request,
                                           message='حدث خطأ أثناء عملية رفع الملفات، يرجى التأكد من صحة الملفات والمحاولة مرة أخرى')
                        # application.documents.all().delete()
                    else:
                        doc_est_obj = ApplicationDocument(file=doc_est, application=application,
                                                          description='صورة عقد التأسيس',
                                                          file_type=ApplicationDocument.TYPES['IMAGE'])
                        doc_est_obj.save()
                        if not doc_est_obj.id:
                            all_valid = False
                            messages.error(request,
                                           message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')

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
                                                application.delete()
                                                applicant.delete()

                                    if all_valid:
                                        if not updating:
                                            cr = CommercialRecord.objects.filter(number=crno).first()
                                            if not cr:
                                                cr = CommercialRecord(number=cr_info['CR'], business_type_id=cr_info['BusTypeID'],
                                                                      activities=cr_data['Activities'], address=cr_data['Address'],
                                                                      is_main=cr_data['IsMain'], name=cr_data['Name'],
                                                                      po_box=cr_data['POBOX'], phone=cr_data['PhoneNumber'],
                                                                      status=cr_data['Status'], zipcode=cr_data['ZipCode'])
                                                cr.save()

                                            if not cr.id:
                                                all_valid = False
                                                messages.error(request,
                                                               message='حدث خطأ أثناء عملية الحفظ، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
                                                application.documents.all().delete()
                                                application.delete()
                                                applicant.delete()
                                            else:
                                                # updating cr data in case it changed
                                                cr.business_type_id = cr_data['BusTypeID']
                                                cr.activities = cr_data['Activities']
                                                cr.address = cr_data['Address']
                                                cr.is_main = cr_data['IsMain']
                                                cr.name = cr_data['Name']
                                                cr.po_box = cr_data['POBOX']
                                                cr.phone = cr_data['PhoneNumber']
                                                cr.status = cr_data['Status']
                                                cr.zipcode = cr_data['ZipCode']
                                                cr.save()
                                                # end update

                                                # TODO: fix the company signup to check for if the cr's general manager has a license or not and if not show error and dont complete the registration -- or if the applicant themselves have a license and if not dont proceed -- thats it cant remember anything else right now :D

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
                        request.session['finished_with_success'] = ApplicationType.COMPANY
                        if updating:
                            application.return_reason = None
                            if application.paid_on and application.status == ApplicationStatus.objects.get(value=ApplicationStatus.RETURNED):
                                application.status = ApplicationStatus.objects.get(value=ApplicationStatus.PAYMENT_APPROVED)
                            else:
                                application.status = ApplicationStatus.objects.get(value=ApplicationStatus.IN_REVISION)
                            application.save()
                            action_history_log(application, None, 'قام بتحديث طلبه')

                        try:
                            subject = 'التراخيص الاحصائية | تم استلام طلبك'
                            sender = 'support@email.com'
                            # receiver = [applicant.email]  # for after dev
                            receiver = ['oyounis@stats.gov.sa']  # for test purposes TODO: remove in production -- and staging when asked
                            email_context = {'applicant': applicant, 'request_host': request.get_host()}

                            message = get_template('email/new_request.html').render(email_context)
                            send_mail(subject, message, sender, receiver, fail_silently=False, html_message=message)
                        except:
                            pass

                        return redirect(reverse('main:success'))

    if updating and not all_valid and application:
        return redirect('main:view_application', id=application.id)

    storage = messages.get_messages(request)
    msgs = [msg for msg in storage]
    storage.used = True

    all_valid = True  # TODO: DEV ONLY
    has_cr = True  # TODO: DEV ONLY
    crs = [  # TODO: DEV ONLY
        {
            'BusType': 'تــــوصية بســـيطة',
            'BusTypeID': 201,
            'CR': '5950011517',
            'ID': '1024901843',
            'RelationID': 3,
            'RelationName': 'شريك متضامن'
        },
        {
            'BusType': 'تــــوصية بســـdيطة',
            'BusTypeID': 201,
            'CR': '5951111517',
            'ID': '1024901843',
            'RelationID': 3,
            'RelationName': 'شريك متضامن'
        }
    ]
    cr_info = {  # TODO: DEV ONLY
        'BusType': 'تــــوصية بســـيطة',
        'BusTypeID': 201,
        'CR': '5950011517',
        'ID': '1024901843',
        'RelationID': 3,
        'RelationName': 'شريك متضامن'
    }
    cr_data = {  # TODO: DEV ONLY
        'Activities': 'تجـارة الجمله والتجزئـه في الكفـرات والأسـاتك والشـنابر ,,,,,,,',
        'Address': 'نجران - العريسة - شارع الملك عبدالعزيز',
        'BusType': 'تــــوصية بســـيطة',
        'BusTypeID': 201,
        'CR': '5950011517',
        'CRLocation': 'نجران',
        'CRLocationID': 5950,
        'CRNationalNO': None,
        'Capital': 10001600.0,
        'CreationDate': '14280126',
        'ExpiredDate': '14400126',
        'Fax': '0174727753',
        'IsMain': False,
        'Name': 'فرع شركة خالد عبدالله الصافي واخوانة',
        'POBOX': '000505',
        'PhoneNumber': '0174727750',
        'Status': 'ACTIVE',
        'ZipCode': '11421'
    }

    context = {'has_cr': has_cr, 'crs': crs, 'error': msgs[0] if msgs else None, 'has_indlicense': False}

    template_name = 'company_signup.html'
    if updating:
        template_name = 'company_view.html'
    else:
        if nid:
            applicant = Applicant.objects.filter(id_number=nid).first()
            has_indlicense = False
            if applicant:
                has_indlicense = applicant.has_license_of_type(ApplicationType.INDIVIDUAL)
                context['has_indlicense'] = has_indlicense

            if not applicant or not has_indlicense or not applicant.has_valid_license_of_type(ApplicationType.INDIVIDUAL):
                context['msg'] = 'لتتمكن من التقدم لطلب إصدار ترخيص منشآت يجب أن يتوفر لديك رخصة أفراد سارية أولاً.'

    return render(request, template_name, context)


@redirect_moderators
@requires_meras_login
@requires_finished_with_success
def success(request):
    application_type = request.session.get('finished_with_success')
    request.session['finished_with_success'] = None
    return render(request, 'request_success.html', {'application_type': application_type, 'ApplicationType': ApplicationType})


@redirect_moderators
@requires_meras_login
def view_application(request, id):
    applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()
    application = Application.objects.filter(id=id, applicant=applicant).first()

    if not application or application and application.status.value not in (ApplicationStatus.RETURNED, ApplicationStatus.REJECTED,
                                                                           ApplicationStatus.PENDING_PAYMENT_RETURNED):
        return redirect(reverse('main:index'))

    application_type = application.type.value

    storage = messages.get_messages(request)
    msgs = [msg for msg in storage]

    context = {'application': application, 'ApplicationStatus': ApplicationStatus, 'error': msgs[0] if msgs else None}

    if application_type == ApplicationType.COMPANY:
        context['CR'] = application.commercial_record
        context['applicant_application_cr'] = applicant.applicant_crs.filter(
            commercial_record=application.commercial_record).first()

    if application.status.value == ApplicationStatus.PENDING_PAYMENT_RETURNED:
        price = PRICES[application.service.type][application.type.value]
        context['price'] = price
        return render(request, 'payment_view.html', context)
    elif application.status.value == ApplicationStatus.RETURNED:
        docs = application.documents.filter(returned=True)
        context['docs'] = docs
        context['TYPES'] = ApplicationDocument.TYPES

    if application_type == ApplicationType.INDIVIDUAL:
        return render(request, 'individual_view.html', context)
    elif application_type == ApplicationType.COMPANY:
        return render(request, 'company_view.html', context)


@redirect_moderators
@requires_meras_login
def payment_directions(request, id):
    applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()
    application = Application.objects.filter(id=id, applicant=applicant).first()

    if not application or application and application.status.value not in (ApplicationStatus.PENDING_PAYMENT,
                                                                           ApplicationStatus.PENDING_PAYMENT_RETURNED):
        return redirect(reverse('main:index'))

    application_type = application.type.value

    updating = request.POST.get('_updating', 'false') == 'true'

    if request.method == 'POST':
        doc_receipt = request.FILES.get('doc-receipt')

        all_valid = True

        if not doc_receipt:
            messages.error(request, message='برجاء ملئ جميع الحقول المطلوبة')
            all_valid = False
        else:
            if not verify_image(doc_receipt):
                messages.error(request, message='صورة الإيصال ليست في صيغة صحيحة')
                all_valid = False

        if all_valid:
            if updating:
                doc_receipt_obj = ApplicationDocument.objects.filter(application=application, file_type=ApplicationDocument.TYPES['IMAGE'],
                                                                      description='صورة إيصال الدفع').first()
                if doc_receipt_obj:
                    doc_receipt_obj.file = doc_receipt
                    doc_receipt_obj.returned = True
                    # existing_receipt.delete()
            else:
                doc_receipt_obj = ApplicationDocument(file=doc_receipt, application=application,
                                             description='صورة إيصال الدفع', file_type=ApplicationDocument.TYPES['IMAGE'])
            doc_receipt_obj.save()
            if not doc_receipt_obj.id:
                all_valid = False
                messages.error(request, message='حدث خطأ أثناء عملية رفع المستندات، يرجى إعادة تسجيل الدخول والمحاولة مرة أخرى')
            else:
                request.session['finished_with_success'] = application_type

                application.return_reason = None
                application.status = ApplicationStatus.objects.get(value=ApplicationStatus.PENDING_PAYMENT_APPROVAL)

                application.save()

                if updating:
                    action_history_log(application, None, 'قام بتحديث صورة إيصال الدفع')
                else:
                    action_history_log(application, None, 'قام برفع صورة من إيصال الدفع')

                return redirect(reverse('main:success'))

    storage = messages.get_messages(request)
    msgs = [msg for msg in storage]
    storage.used = True

    price = PRICES[application.service.type][application.type.value]

    template_name = 'payment_directions.html'

    if updating:
        template_name = 'payment_view.html'

    return render(request, template_name, {'application': application, 'price': price, 'error': msgs[0] if msgs else None})


@redirect_moderators
@requires_meras_login
def download_license(request, id):
    applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()

    _license = License.objects.filter(id=id, application__applicant=applicant).first()

    if not _license:
        return redirect(reverse('main:index'))

    # context = {'license': _license, 'ApplicationType': ApplicationType}
    # return render(request, 'moderation/pdf/license_pdf_template3.html', context)

    filepath = generate_license_pdf(_license, request)

    if filepath:
        _license.filepath = filepath
        _license.save()
    else:
        return HttpResponseBadRequest('فشلت العملية')

    return redirect(filepath)


@requires_meras_login
def preview_file(request, id):
    applicant = Applicant.objects.filter(id_number=sessdata(request, 'user_id')).first()

    if not applicant:
        return HttpResponseBadRequest()

    doc = ApplicationDocument.objects.filter(id=id, application__applicant=applicant).first()

    if not doc:
        return HttpResponseBadRequest()

    response = HttpResponse(doc.file, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(doc.file.name)

    return response


def qrcode_details(request, serial_encrypted):
    try:
        serial = decrypt_base64decode(serial_encrypted)
    except:
        return redirect(reverse('main:index'))

    _license = License.objects.filter(serial=serial).first()
    if not _license:
        return HttpResponseNotFound('Wrong license serial. License not found!')

    return render(request, 'license_verify.html', {'license': _license})
