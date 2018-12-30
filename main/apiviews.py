import json
from django.http.response import HttpResponseBadRequest, JsonResponse, HttpResponseNotAllowed

from .helpers import sessdata
from .lookups import ALLOWED_BUSINESSES, ALLOWED_RELATIONS
from .models import Application
from .services import WathiqService


def check_if_manager_has_license(cr):
    pass


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


def cr_data(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        cr = body['crno'] if 'crno' in body else None
        crs = sessdata(request, 'crs')

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

        if not cr or not crs:
            return HttpResponseBadRequest(JsonResponse({'status': 0, 'msg': 'حدث خطأ في الطلب'}))

        hit = None

        for crr in crs:
            if crr['CR'] == cr:
                hit = crr
                break

        if not hit:
            return JsonResponse({'status': 0, 'msg': 'لا يوجد لديك سجل تجاري مسجل بهذا الرقم'})

        crdata = WathiqService.get_cr_data_by_cr(hit['CR'])

        crdata = {  # TODO: DEV ONLY
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

        if not crdata:
            return JsonResponse({'status': 0, 'msg': 'حدث خطأ في خدمة استرجاع البيانات'})

        return JsonResponse({'status': 1, 'data': {'crdata': dict(crdata), 'cr': hit}})
