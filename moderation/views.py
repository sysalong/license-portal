from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.contrib.messages import get_messages, success, error, SUCCESS, ERROR
from django.core.paginator import Paginator, PageNotAnInteger

from license_portal.settings import EFILE_URL, MERAS_CLIENT_ID
from main.helpers import sessdata, internal_logout, user_has_groups_any, user_has_group, action_history_log
from main.models import Application, ApplicationDocument, ApplicationStatus, OFFICER, MANAGER, PRESIDENT, ApplicantType

from .decorators import moderators_only


# TODO: add has_no_applications decorator to functions before production
def index(request):
    access_token = sessdata(request, 'access_token')

    if access_token:
        # user_authenticated = EFileService.is_authenticated(access_token)
        # if user_authenticated:
        user = User.objects.filter(username=sessdata(request, 'user_username'), email=sessdata(request, 'user_email')).first()
        if not user:
            user = User.objects.create_user(sessdata(request, 'user_username'), sessdata(request, 'user_email'), sessdata(request, 'user_id') + '+' + sessdata(request, 'user_userid'))
            user.first_name = sessdata(request, 'user_firstname')
            user.last_name = sessdata(request, 'user_lastname')
            user.save()

        if not request.user.is_authenticated:
            auth_login(request, user)

        if not user_has_groups_any(user, [OFFICER, MANAGER, PRESIDENT]):
            # internal_logout(request)
            return redirect(reverse('main:index'))

        # TODO: implement filter by application status
        applications = Application.objects.order_by('-created_at', 'status__value')

        if user_has_group(user, 'officer'):
            applications = applications.filter(status__value__in=(ApplicationStatus.NEW, ApplicationStatus.IN_REVISION, ApplicationStatus.RETURNED_REVISION, ApplicationStatus.PENDING_PAYMENT, ApplicationStatus.REJECTED, ApplicationStatus.FINISHED, ApplicationStatus.ON_HOLD, ApplicationStatus.PENDING_PAYMENT_APPROVAL))
        elif user_has_group(user, 'manager'):
            applications = applications.filter(status__value__in=(ApplicationStatus.IN_MANAGER, ApplicationStatus.RETURNED_MANAGER, ApplicationStatus.PENDING_PAYMENT, ApplicationStatus.REJECTED, ApplicationStatus.FINISHED, ApplicationStatus.ON_HOLD))
        elif user_has_group(user, 'president'):
            applications = applications.filter(status__value__in=(ApplicationStatus.IN_PRESIDENT, ApplicationStatus.PENDING_PAYMENT, ApplicationStatus.REJECTED, ApplicationStatus.FINISHED, ApplicationStatus.ON_HOLD))

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

        context = {'applications': applications, 'page': int(page)}

        if storage:
            if msg.level == SUCCESS:
                context['success'] = msg
            elif msg.level == ERROR:
                context['error'] = msg

        return render(request, 'moderation/dashboard.html', context)
    else:
        internal_logout(request)

    return redirect('{}/account/login?client_id={}&returnUrl={}'.format(EFILE_URL, MERAS_CLIENT_ID, reverse('moderation:index')))


def login(request):
    return render(request, 'moderation/login.html')


def admin(request):
    return render(request, 'moderation/login.html')


@moderators_only
def view_application(request, id):
    application = get_object_or_404(Application, pk=id)
    if request.user.is_authenticated:
        if user_has_group(request.user, OFFICER):
            if application.status.value in (ApplicationStatus.NEW, ApplicationStatus.RETURNED):
                application.status = ApplicationStatus.objects.get(value=ApplicationStatus.IN_REVISION)
                application.save()

    applicant = application.applicant
    applicant_type = applicant.type.value

    context = {'application': application,
               'ApplicationDocument': ApplicationDocument,
               'ApplicationStatus': ApplicationStatus,
               'user_role': request.user.groups.first().name,
               'applicant_type': applicant_type,
               'ApplicantType': ApplicantType}

    if applicant_type == ApplicantType.COMPANY:
        context['CR'] = application.commercial_record
        context['applicant_application_cr'] = applicant.applicant_crs.filter(commercial_record=application.commercial_record).first()

    return render(request, 'moderation/view_request.html', context)


@moderators_only
def action_application(request, id):
    if request.method == 'POST':
        action = request.POST.get('_action')
        reason = request.POST.get('reason')
        reason_completely = request.POST.get('reason-completely')

        if action:
            application = get_object_or_404(Application, pk=id)
            if action == 'approve':
                new_status = ''
                log_message = 'N/A'

                if user_has_group(request.user, OFFICER):
                    new_status = ApplicationStatus.IN_MANAGER
                    log_message = 'قام بالموافقة على الطلب ونقله لمدير الأكاديمية للمراجعة'
                elif user_has_group(request.user, 'manager'):
                    new_status = ApplicationStatus.IN_PRESIDENT
                    log_message = 'قام بالموافقة على الطلب ونقله لرئيس الأكاديمية للمراجعة'
                elif user_has_group(request.user, 'president'):
                    new_status = ApplicationStatus.PENDING_PAYMENT
                    log_message = 'قام بالموافقة على الطلب وفي إنتظار اكتمال الدفع للاعتماد'

                application.status = ApplicationStatus.objects.get(value=new_status)
                application.return_reason = None
                application.save()

                action_history_log(application, request.user, log_message)
                success(request, 'تمت العملية بنجاح')
            elif action == 'reject':
                new_status = ''
                if user_has_group(request.user, 'officer'):
                    new_status = ApplicationStatus.RETURNED
                elif user_has_group(request.user, 'manager'):
                    new_status = ApplicationStatus.RETURNED_REVISION
                elif user_has_group(request.user, 'president'):
                    new_status = ApplicationStatus.RETURNED_MANAGER
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
