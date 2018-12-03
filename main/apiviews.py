import json
from django.http.response import HttpResponseBadRequest, JsonResponse, HttpResponseNotAllowed

from .helpers import sessdata
from .lookups import ALLOWED_BUSINESSES, ALLOWED_RELATIONS
from .models import Application


def cr_validate(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        cr = body['crno'] if 'crno' in body else None
        crs = sessdata(request, 'crs')

        if not cr or not crs:
            return HttpResponseBadRequest(JsonResponse({'status': 0, 'msg': 'حدث خطأ في الطلب'}))

        hit = None

        for crr in crs:
            if crr['CR'] == cr:
                hit = crr
                break

        if not hit:
            return JsonResponse({'status': 0, 'msg': 'لا يوجد لديك سجل تجاري مسجل بهذا الرقم'})

        not_allowed_msg = ''
        if hit['BusTypeID'] not in ALLOWED_BUSINESSES:
            not_allowed_msg = 'عفواً، لا يحق للمنشآة المسجلة بهذا الرقم الحصول على رخصة'
        elif hit['RelationID'] not in ALLOWED_RELATIONS:
            not_allowed_msg = 'عفواً، لا يحق لك إصدار رخصة لهذه المنشآة'

        if not_allowed_msg:
            return JsonResponse({'status': 0, 'msg': not_allowed_msg})

        if Application.objects.filter(serial='C' + hit['CR']).exists():
            return JsonResponse({'status': 0, 'msg': 'عفواً، هناك طلب سابق بخصوص هذا الرقم'})

        return JsonResponse({'status': 1, 'data': {'cr': hit}})

    return HttpResponseNotAllowed(JsonResponse({'status': 0, 'msg': 'حدث خطأ في الطلب'}))
