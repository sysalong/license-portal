import os
from datetime import datetime, timedelta

from django.db import models
from django.contrib.auth.models import User

from .lookups import BUSINESS_TYPE, RELATION_TYPE


OFFICER = 'officer'
MANAGER = 'manager'
PRESIDENT = 'president'
FINANCE = 'finance'


def application_docs_upload_to(instance, filename):
    today = datetime.today()
    return 'documents/%s/%s-%s-%s/%s' % (instance.application.id, today.year, today.month, today.day, filename)


class ApplicationType(models.Model):
    """
    LOOKUP CLASS
    """
    INDIVIDUAL = 1
    COMPANY = 2

    name = models.CharField(max_length=255)
    value = models.IntegerField(choices=(
        (INDIVIDUAL, 'Individual'),
        (COMPANY, 'Company'),
    ))


class CommercialRecord(models.Model):
    number = models.CharField(max_length=20)
    business_type_id = models.IntegerField()

    activities = models.CharField(max_length=255, null=True)
    address = models.CharField(max_length=255, null=True)
    is_main = models.BooleanField(default=False)
    name = models.CharField(max_length=255, default='')
    po_box = models.CharField(max_length=8, null=True)
    phone = models.CharField(max_length=12, null=True)
    status = models.CharField(max_length=20, null=True)
    zipcode = models.CharField(max_length=8, null=True)

    @property
    def business_type_text(self):
        return BUSINESS_TYPE[self.business_type_id]


class ApplicantCommercialRecord(models.Model):
    applicant = models.ForeignKey('Applicant', on_delete=models.CASCADE, related_name='applicant_crs')
    commercial_record = models.ForeignKey(CommercialRecord, on_delete=models.DO_NOTHING)
    relation_id = models.IntegerField()

    @property
    def relation_text(self):
        return RELATION_TYPE[self.relation_id]


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

    commercial_records = models.ManyToManyField(CommercialRecord, related_name='related', through=ApplicantCommercialRecord)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def fullname(self):
        return ' '.join((self.first_name.strip(), self.second_name.strip(), self.third_name.strip(), self.last_name.strip()))

    def __str__(self):
        return self.fullname

    @property
    def birthdatehijri_dateformat(self):
        # return datetime.strptime(self.birthdatehijri, '%Y-%m-%d')
        return self.birthdatehijri

    @property
    def gender_text(self):
        return 'ذكر' if self.gender == 'M' else 'أنثى'

    @property
    def licenses(self):
        return License.objects.filter(application__applicant=self)

    def has_license_of_type(self, _type):
        return self.licenses.filter(application__type=_type).exists()

    def get_licenses_of_type(self, _type):
        return self.licenses.filter(application__type=_type)

    def has_valid_license_of_type(self, _type):
        return list(filter(lambda l: l.is_expired(), self.get_licenses_of_type(_type))) == []


class ApplicationStatus(models.Model):
    """
    LOOKUP CLASS
    Don't forget to update statuses manually in the DB after adding or changing here
    """

    NEW = 1
    IN_REVISION = 2
    IN_MANAGER = 3
    IN_PRESIDENT = 4
    RETURNED = 5  # is when an application is commented on by an officer and returned to the applicant
    REJECTED = 6  # completely rejected
    FINISHED = 7  # for after payment and final approval
    ON_HOLD = 8  # for when the application is suspended
    PENDING_PAYMENT = 9  # approved but awaiting payment
    RETURNED_REVISION = 10  # is when an application is commented on by the manager and returned to the officer
    RETURNED_MANAGER = 11  # is when an application is commented on by the president and returned to the manager
    PENDING_PAYMENT_APPROVAL = 12  # sent to finance department after the user submits the receipt
    PENDING_PAYMENT_RETURNED = 13  # is when returned to applicant by finance department because of payment rejection
    PAYMENT_APPROVED = 14  # is when approved by finance and sent to officer for final approval

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
        (RETURNED_MANAGER, 'Returned to manager'),
        (PENDING_PAYMENT_APPROVAL, 'Pending payment approval'),
        (PENDING_PAYMENT_RETURNED, 'Pending payment returned'),
        (PAYMENT_APPROVED, 'Payment approved'),
    ), unique=True)


class Service(models.Model):
    """
    LOOKUP CLASS
    """
    NEW = 1
    RENEW = 2

    name = models.CharField(max_length=255)
    type = models.IntegerField(choices=(
        (NEW, 'New'),
        (RENEW, 'Renew'),
    ))

    def __str__(self):
        return self.name


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

    type = models.ForeignKey(ApplicationType, on_delete=models.SET_NULL, null=True)

    commercial_record = models.ForeignKey(CommercialRecord, on_delete=models.CASCADE, null=True)

    @property
    def action_history(self):
        entries = ActionHistoryEntry.objects.filter(target=self.id, target_type=TargetType.objects.get(value=TargetType.APPLICATION))
        return entries.order_by('-created_at').all()

    @property
    def duration_text(self):
        if self.service.type == Service.NEW:
            return 'سنتين'
        elif self.service.type == Service.RENEW:
            return 'خمس سنوات'

    @property
    def expiration_date(self):
        two_months = 2 * 30
        return self.created_at + timedelta(days=two_months)

    @property
    def type_text(self):
        return 'طلب أفراد' if self.type.value == ApplicationType.INDIVIDUAL else 'طلب منشآت'


class ApplicationComment(models.Model):
    text = models.TextField()
    poster = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)


class ApplicationDocument(models.Model):
    TYPES = {
        'IMAGE': 1,
        'PDF': 2,
        'HYBRID': 3,
    }

    file = models.FileField(upload_to=application_docs_upload_to)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    description = models.CharField(max_length=255, null=True, blank=True)
    file_type = models.IntegerField(default=0, choices=(
        (TYPES['IMAGE'], 'Image'),
        (TYPES['PDF'], 'PDF'),
        (TYPES['HYBRID'], 'PDF or Image'),
    ))
    returned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def file_extension(self):
        name, extension = os.path.splitext(self.file.name)
        return extension.lower()[1:]

    @property
    def is_required(self):
        return self.description != 'مستندات إضافية'

    @property
    def input_field_name(self):
        if self.description == 'صورة الهوية':
            return 'id'
        elif self.description == 'المؤهل الأكاديمي':
            return 'graduation'
        elif self.description == 'السيرة الذاتية':
            return 'resume'
        elif self.description == 'شهادات الخبرات':
            return 'expertise'
        elif self.description == 'مستندات إضافية':
            return 'additional'

    @property
    def basename(self):
        return os.path.basename(self.file.name)


class TargetType(models.Model):
    """
    LOOKUP CLASS
    """
    APPLICATION = 1  # has to be of the same name as the model for the action_log helper to work
    LICENSE = 2  # has to be of the same name as the model for the action_log helper to work

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


class LicenseStatus(models.Model):
    """
    LOOKUP CLASS
    """
    VALID = 1
    SUSPENDED = 2

    name = models.CharField(max_length=255)
    value = models.IntegerField(choices=(
        (VALID, 'Valid'),
        (SUSPENDED, 'Suspended'),
    ), unique=True)


class License(models.Model):
    serial = models.CharField(max_length=255)
    status = models.ForeignKey(LicenseStatus, on_delete=models.SET_NULL, null=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='licenses')
    created_at = models.DateTimeField(auto_now_add=True)

    action_date = models.DateTimeField()  # the date on which the license was issued or renewed
    duration = models.IntegerField(choices=(
        (Application.NEW_YEARS, 'New'),
        (Application.RENEW_YEARS, 'Renew'),
    ))

    filepath = models.FilePathField(null=True)

    @property
    def expiration_date(self):
        years_in_days = self.duration * 365
        return self.action_date + timedelta(days=years_in_days)

    def is_expired(self):
        return self.expiration_date < datetime.today()

    @property
    def expired(self):
        return self.expiration_date < datetime.today()


PRICES = {
    Service.NEW: {
        ApplicationType.INDIVIDUAL: 200,
        ApplicationType.COMPANY: 1000,
    },

    Service.RENEW: {
        ApplicationType.INDIVIDUAL: 500,
        ApplicationType.COMPANY: 2000,
    },
}

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
