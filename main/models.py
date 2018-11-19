from datetime import datetime

from django.db import models
from django.contrib.auth.models import User


OFFICER = 'officer'
MANAGER = 'manager'
PRESIDENT = 'president'


def application_docs_upload_to(instance, filename):
    today = datetime.today()
    return 'documents/%s/%s/%s/%s/%s' % (today.year, today.month, today.day, instance.application.id, filename)


class ApplicantType(models.Model):
    INDIVIDUAL = 1
    COMPANY = 2

    name = models.CharField(max_length=255)
    value = models.IntegerField(choices=(
        (INDIVIDUAL, 'Individual'),
        (COMPANY, 'Company'),
    ))


class Applicant(models.Model):
    id_number = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255)
    userid = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    second_name = models.CharField(max_length=255, null=True, blank=True)
    third_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20, null=True, blank=True)
    phonecode = models.CharField(max_length=20, null=True, blank=True)
    countryid = models.CharField(max_length=50)
    birthdate = models.DateField()
    birthdatehijri = models.CharField(max_length=255, null=True, blank=True)
    legal_status = models.IntegerField(null=True, blank=True)
    person_type = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10)
    has_wasel_account = models.BooleanField(default=False)

    usertype = models.ForeignKey(ApplicantType, on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def fullname(self):
        return ' '.join((self.first_name.strip(), self.second_name.strip(), self.third_name.strip(), self.last_name.strip()))

    def __str__(self):
        return self.fullname

    @property
    def birthdatehijri_dateformat(self):
        return datetime.strptime(self.birthdatehijri, '%Y-%m-%d')

    @property
    def gender_text(self):
        return 'ذكر' if self.gender == 'M' else 'أنثى'

    @property
    def type_text(self):
        return 'طلب أفراد' if self.usertype.value == ApplicantType.INDIVIDUAL else 'طلب منشآت'


class ApplicationStatus(models.Model):
    NEW = 1
    IN_REVISION = 2
    IN_MANAGER = 3
    IN_PRESIDENT = 4
    RETURNED = 5  # is when an application is commented on by an officer and returned to the applicant
    REJECTED = 6  # completely rejected
    FINISHED = 7  # for after payment
    ON_HOLD = 8  # for when the application is suspended
    PENDING_PAYMENT = 9  # approved but awaiting payment
    RETURNED_REVISION = 10  # is when an application is commented on by a higher employee and returned to the officer

    name = models.CharField(max_length=255)
    value = models.IntegerField(choices=(
        (NEW, 'New'),
        (IN_REVISION, 'In revision'),
        (IN_MANAGER, 'In manager'),
        (IN_PRESIDENT, 'In president'),
        (RETURNED, 'Returned'),
        (REJECTED, 'Rejected'),
        (FINISHED, 'Finished'),
        (ON_HOLD, 'On hold'),
        (PENDING_PAYMENT, 'Pending payment'),
        (RETURNED_REVISION, 'Returned to revision'),
    ), unique=True)


class Service(models.Model):
    NEW = 1
    RENEW = 2

    name = models.CharField(max_length=255)
    type = models.IntegerField(choices=(
        (NEW, 'New'),
        (RENEW, 'Renew'),
    ))


class Application(models.Model):
    NEW_YEARS = 2
    RENEW_YEARS = 5

    serial = models.CharField(max_length=255)
    status = models.ForeignKey(ApplicationStatus, on_delete=models.SET_NULL, null=True)
    applicant = models.ForeignKey(Applicant, on_delete=models.SET_NULL, null=True, related_name='applications')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='applications', default=None)
    return_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_on = models.DateTimeField(null=True)

    @property
    def action_history(self):
        entries = ActionHistoryEntry.objects.filter(target=self.id, target_type=TargetType.objects.get(value=TargetType.APPLICATION))
        return entries.order_by('-created_at').all()


class ApplicationComment(models.Model):
    text = models.TextField()
    poster = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)


class ApplicationDocument(models.Model):
    TYPES = {
        'IMAGE': 1,
        'PDF': 2,
    }

    file = models.FileField(upload_to=application_docs_upload_to)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    description = models.CharField(max_length=255, null=True, blank=True)
    file_type = models.IntegerField(default=0, choices=(
        (TYPES['IMAGE'], 'Image'),
        (TYPES['PDF'], 'PDF'),
    ))
    created_at = models.DateTimeField(auto_now_add=True)


class TargetType(models.Model):
    APPLICATION = 1
    LICENSE = 2

    name = models.CharField(max_length=255)
    value = models.IntegerField(choices=(
        (APPLICATION, "Application"),
        (LICENSE, "License"),
    ))


class ActionHistoryEntry(models.Model):
    text = models.TextField()
    invoker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='action_history_entries')
    target = models.IntegerField(default=0)
    target_type = models.ForeignKey(TargetType, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def get_target(self):
        if self.target_type.value == TargetType.APPLICATION:
            return Application.objects.get(pk=self.target)


# *** example meras user object ***
# {
#     'AdditionalNo': None,
#     'BirthDate': datetime.datetime(1958, 1, 20, 0, 0),
#     'BirthDateHijri': '1377/07/01     ',
#     'BuildingNo': None,
#     'CityID': 1,
#     'CityName': 'الرياض',
#     'CityTelephoneCode': '011',
#     'ContactEmail': 'abdotawfeek@gmail.com',
#     'ContactMobile': '0549160274',
#     'ContactTelephone': '00966549160274',
#     'CountryID': 'sa',
#     'CountryName': 'المملكة العربية السعودية',
#     'DistrictID': 55,
#     'DistrictName': 'الضباط',
#     'ExpiryDate': datetime.datetime(1940, 10, 7, 0, 0),
#     'FirstName': 'خالد',
#     'FormalIdentityNumber': '1024901843',
#     'FullDistrict': None,
#     'Gender': 'M',
#     'HasWaselAccount': False,
#     'InterContactMobile': '00966549160274',
#     'InterContactTelephone': None,
#     'IssueAuthority': None,
#     'IssueDate': datetime.datetime(2018, 11, 4, 14, 40, 40),
#     'IssuePlace': 'احوال الدرعية',
#     'LastName': 'الصافي',
#     'LegalStatus': 0,
#     'NationalityID': None,
#     'NationalityName': None,
#     'POBox': '486',
#     'PersonGUID': '00000000-0000-0000-0000-000000000000',
#     'PersonImage': None,
#     'PersonType': 1,
#     'PostalCode': '11411',
#     'SecondName': 'عبدالله',
#     'StreetName': '<><||',
#     'TelephoneCodeID': '966',
#     'ThirdName': 'شيخ',
#     'UnitNo': None,
#     'UserBlackListedServices': None,
#     'UserID': 'b8aa0a88-c07d-4724-9a10-d759067288ea'
# }
