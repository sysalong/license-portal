from django.urls import path

from . import views

app_name = 'main'

urlpatterns = [
    path('/OAuth', views.oauth_return, name='oauth_return'),

    path('', views.index, name='index'),

    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('terms', views.terms, name='terms'),
    path('choose_type', views.choose_type, name='choose_type'),
    path('individual_signup', views.individual_signup, name='individual_signup'),
    path('company_signup', views.company_signup, name='company_signup'),
]
