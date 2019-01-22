from datetime import datetime
import time
import os

from django.template.loader import get_template
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib.messages import get_messages, success, error, SUCCESS, ERROR
from django.core.paginator import Paginator, PageNotAnInteger

from weasyprint import HTML

from license_portal.settings import EFILE_URL, MERAS_CLIENT_ID, BASE_DIR, MEDIA_ROOT, MEDIA_URL
from main.helpers import sessdata, internal_logout, user_has_groups_any, user_has_group, action_history_log
from main.models import Application, ApplicationDocument, ApplicationStatus, OFFICER, MANAGER, PRESIDENT, FINANCE, \
    ApplicationType, License, LicenseStatus

from .decorators import moderators_only


def generate_license_pdf(_license):
    template = get_template("moderation/pdf/license_pdf_template3.html")
    context = {'license': _license, 'ApplicationType': ApplicationType}
    html = template.render(context)

    filepath = os.path.join(BASE_DIR, 'moderation', 'tmp', '%s.html' % _license.serial)

    filename = '%s.%s.pdf' % (_license.serial, int(time.time() * 100))
    pdffilepath = os.path.join(MEDIA_ROOT, 'licenses', filename)

    with open(filepath, 'w') as f:
        f.write(html)

    try:
        HTML(filepath).write_pdf(pdffilepath)
        return os.path.join(MEDIA_URL, 'licenses', filename)
    except:
        return False


# TODO: add has_no_applications decorator to functions before production
def index(request):
    ##access_token = sessdata(request, 'access_token')

    ##if access_token:
        # user_authenticated = EFileService.is_authenticated(access_token)
        # if user_authenticated:
        ##user = User.objects.filter(username=sessdata(request, 'user_username'), email=sessdata(request, 'user_email')).first()
        ##if not user:
            ##user = User.objects.create_user(sessdata(request, 'user_username'), sessdata(request, 'user_email'), sessdata(request, 'user_id') + '+' + sessdata(request, 'user_userid'))
            ##user.first_name = sessdata(request, 'user_firstname')
            ##user.last_name = sessdata(request, 'user_lastname')
            ##user.save()

    if not request.user or not request.user.is_authenticated:
        ##auth_login(request, user)
        return redirect('/')

    user = request.user

    if not user_has_groups_any(user, (OFFICER, MANAGER, PRESIDENT, FINANCE)):
        # internal_logout(request)
        return redirect(reverse('main:index'))
    else:
        request.session['user_is_moderator'] = True

    # TODO: implement filter by application status
    applications = Application.objects.order_by('-created_at', 'status__value')

    if user_has_group(user, OFFICER):
        applications = applications.filter(status__value__in=(ApplicationStatus.NEW, ApplicationStatus.IN_REVISION, ApplicationStatus.RETURNED_REVISION, ApplicationStatus.PENDING_PAYMENT, ApplicationStatus.REJECTED, ApplicationStatus.FINISHED, ApplicationStatus.ON_HOLD, ApplicationStatus.PENDING_PAYMENT_APPROVAL, ApplicationStatus.PENDING_PAYMENT_RETURNED, ApplicationStatus.PAYMENT_APPROVED))
    elif user_has_group(user, MANAGER):
        applications = applications.filter(status__value__in=(ApplicationStatus.IN_MANAGER, ApplicationStatus.RETURNED_MANAGER, ApplicationStatus.PENDING_PAYMENT, ApplicationStatus.REJECTED, ApplicationStatus.FINISHED, ApplicationStatus.ON_HOLD))
    elif user_has_group(user, PRESIDENT):
        applications = applications.filter(status__value__in=(ApplicationStatus.IN_PRESIDENT, ApplicationStatus.PENDING_PAYMENT, ApplicationStatus.REJECTED, ApplicationStatus.FINISHED, ApplicationStatus.ON_HOLD))
    elif user_has_group(user, FINANCE):
        applications = applications.filter(status__value__in=(ApplicationStatus.PENDING_PAYMENT_APPROVAL, ApplicationStatus.PENDING_PAYMENT_RETURNED))

    page = request.GET.get('page', 1)
    paginator = Paginator(applications, 10)

    try:
        applications = paginator.get_page(page)
    except PageNotAnInteger:
        applications = paginator.get_page(1)

    storage = get_messages(request)
    if storage:
        msg = [msg for msg in storage][0]
    storage.used = True

    context = {'applications': applications, 'page': int(page), 'active_link': 'moderate'}

    if storage:
        if msg.level == SUCCESS:
            context['success'] = msg
        elif msg.level == ERROR:
            context['error'] = msg

    return render(request, 'moderation/dashboard.html', context)
    ##else:
        ##internal_logout(request)

    ##return redirect('{}/account/login?client_id={}&returnUrl={}'.format(EFILE_URL, MERAS_CLIENT_ID, reverse('moderation:index')))


@moderators_only
def licenses(request):
    if not request.user.is_authenticated:
        return redirect(reverse('main:index'))
        ##return redirect('{}/account/login?client_id={}&returnUrl={}'.format(EFILE_URL, MERAS_CLIENT_ID, reverse('moderation:index')))

    if not user_has_groups_any(request.user, (OFFICER, MANAGER, PRESIDENT, FINANCE)):
        return redirect(reverse('main:index'))
    else:
        request.session['user_is_moderator'] = True

    # TODO: implement filter by license status
    _licenses = License.objects.order_by('-created_at')

    page = request.GET.get('page', 1)
    paginator = Paginator(_licenses, 10)

    try:
        _licenses = paginator.get_page(page)
    except PageNotAnInteger:
        _licenses = paginator.get_page(1)

    storage = get_messages(request)
    if storage:
        msg = [msg for msg in storage][0]
    storage.used = True

    context = {'licenses': _licenses, 'page': int(page), 'active_link': 'licenses'}

    if storage:
        if msg.level == SUCCESS:
            context['success'] = msg
        elif msg.level == ERROR:
            context['error'] = msg

    return render(request, 'moderation/licenses.html', context)


def login(request):
    if request.user and request.user.is_authenticated:
        return redirect(reverse('main:index'))

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            return redirect('/')

        user = authenticate(request, username=username, password=password)
        if user:
            if user_has_groups_any(user, (OFFICER, MANAGER, PRESIDENT, FINANCE)):
                auth_login(request, user)
                return redirect(reverse('moderation:index'))
            else:
                error(request, 'عفواً، لا تتوفر لديك الصلاحيات اللازمة للدخول')
        else:
            error(request, 'خطأ في اسم المستخدم أو كلمة المرور')

    context = {}
    msgs = get_messages(request)
    if msgs:
        context['error'] = [msg for msg in msgs][0]

    return render(request, 'moderation/login.html', context)


def admin(request):
    return redirect(reverse('moderation:index'))


@moderators_only
def view_application(request, id):
    application = get_object_or_404(Application, pk=id)
    if request.user.is_authenticated:
        if user_has_group(request.user, OFFICER):
            if application.status.value in (ApplicationStatus.NEW, ApplicationStatus.RETURNED):
                application.status = ApplicationStatus.objects.get(value=ApplicationStatus.IN_REVISION)
                application.save()

    applicant = application.applicant
    application_type = application.type.value

    returned_q = application.documents.filter(returned=True)
    returned_docs = list(returned_q.values_list('id', flat=True))
    returned_q.update(returned=False)

    context = {'application': application,
               'ApplicationDocument': ApplicationDocument,
               'ApplicationStatus': ApplicationStatus,
               'user_role': request.user.groups.first().name,
               'application_type': application_type,
               'ApplicationType': ApplicationType,
               'returned_docs': returned_docs}

    if application_type == ApplicationType.COMPANY:
        context['CR'] = application.commercial_record
        context['applicant_application_cr'] = applicant.applicant_crs.filter(commercial_record=application.commercial_record).first()

    return render(request, 'moderation/view_request.html', context)


@moderators_only
def action_application(request, id):
    if request.method == 'POST':
        action = request.POST.get('_action')
        reason = request.POST.get('reason')
        reason_completely = request.POST.get('reason-completely')

        issued = True

        if action:
            application = get_object_or_404(Application, pk=id)
            if action == 'approve':
                new_status = 0
                log_message = 'N/A'

                if user_has_group(request.user, OFFICER):
                    if application.status.value == ApplicationStatus.PAYMENT_APPROVED:
                        issued = issue_license(application)

                        if not issued:
                            error(request, 'حدث خطأ، لم يتم إصدار الترخيص')
                        else:
                            new_status = ApplicationStatus.FINISHED
                            log_message = 'قام بإعتماد الطلب وإصدار الترخيص للمتقدم'
                    else:
                        new_status = ApplicationStatus.IN_MANAGER
                        log_message = 'قام بالموافقة على الطلب ونقله لمدير الأكاديمية للمراجعة'
                elif user_has_group(request.user, MANAGER):
                    new_status = ApplicationStatus.IN_PRESIDENT
                    log_message = 'قام بالموافقة على الطلب ونقله لرئيس الأكاديمية للمراجعة'
                elif user_has_group(request.user, PRESIDENT):
                    new_status = ApplicationStatus.PENDING_PAYMENT
                    log_message = 'قام بالموافقة على الطلب وفي إنتظار اكتمال الدفع للاعتماد'
                elif user_has_group(request.user, FINANCE):
                    new_status = ApplicationStatus.PAYMENT_APPROVED
                    log_message = 'قام بالموافقة على إيصال الدفع المقدم'
                    application.paid_on = datetime.today()

                if issued:
                    application.status = ApplicationStatus.objects.get(value=new_status)
                    application.return_reason = None
                    application.save()

                    action_history_log(application, request.user, log_message)
                    success(request, 'تمت العملية بنجاح')
            elif action == 'reject':
                if user_has_group(request.user, OFFICER):
                    new_status = ApplicationStatus.RETURNED
                    returned_files = request.POST.getlist('returned-files[]')
                    if returned_files != []:
                        application.documents.filter(id__in=returned_files).update(returned=True)
                    else:
                        application.documents.all().update(returned=True)
                elif user_has_group(request.user, MANAGER):
                    new_status = ApplicationStatus.RETURNED_REVISION
                elif user_has_group(request.user, PRESIDENT):
                    new_status = ApplicationStatus.RETURNED_MANAGER
                elif user_has_group(request.user, FINANCE) and application.status.value == ApplicationStatus.PENDING_PAYMENT_APPROVAL:
                    new_status = ApplicationStatus.PENDING_PAYMENT_RETURNED
                else:
                    new_status = ApplicationStatus.RETURNED

                application.status = ApplicationStatus.objects.get(value=new_status)
                application.return_reason = reason
                application.save()
                action_history_log(application, request.user, 'قام برفض الطلب ورده بسبب %s' % reason)
                success(request, 'تمت العملية بنجاح')
            elif action == 'reject-completely':
                new_status = ApplicationStatus.REJECTED

                application.status = ApplicationStatus.objects.get(value=new_status)
                application.return_reason = reason_completely
                application.save()
                action_history_log(application, request.user, 'قام برفض الطلب نهائياً بسبب %s' % reason_completely)
                success(request, 'تمت العملية بنجاح')
            else:
                error(request, 'حدث خطأ ما، لقد فشلت العملية')

    return redirect(reverse('moderation:index'))


def issue_license(application):
    _license = License(serial=application.serial, status=LicenseStatus.objects.get(value=LicenseStatus.VALID),
                       application=application, action_date=datetime.today(), duration=Application.NEW_YEARS)

    _license.save()

    if _license.id:
        return True
    else:
        return False


@moderators_only
def pdf_view(request, doc_id):
    doc = ApplicationDocument.objects.filter(pk=doc_id).first()
    if not doc:
        return redirect(reverse('moderation:index'))
    return render(request, 'moderation/viewer.html', {'file_url': doc.file.url})
