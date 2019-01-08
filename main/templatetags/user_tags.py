from django import template
from main.helpers import sessdata
from main.models import Application, License

register = template.Library()


@register.simple_tag(takes_context=True)
def user_has_application(context):
    request = context['request']
    user_id = sessdata(request, 'user_id')

    if user_id:
        return Application.objects.filter(applicant__id_number=user_id).exists()

    return False


@register.simple_tag(takes_context=True)
def user_has_license(context):
    request = context['request']
    user_id = sessdata(request, 'user_id')

    if user_id:
        return License.objects.filter(application__applicant__id_number=user_id).exists()

    return False
