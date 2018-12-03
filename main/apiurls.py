from django.urls import path
from . import apiviews


app_name = 'api'

urlpatterns = [
    path('cr-validate', apiviews.cr_validate, name="cr_validate"),
]
