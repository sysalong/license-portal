from django.urls import path

from . import views

app_name = 'main'

urlpatterns = [
    path('login', views.login, name='login'),
    path('register', views.register, name='register'),
    path('reset_password', views.reset_password, name='reset_password'),
    path('choose_type', views.choose_type, name='choose_type'),
    path('individual_signup', views.individual_signup, name='individual_signup'),
]
