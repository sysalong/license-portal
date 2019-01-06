from django.urls import path, include

from . import views


app_name = 'main'

urlpatterns = [
    path('OAuth', views.oauth_return, name='oauth_return'),

    path('', views.index, name='index'),

    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('licenses', views.licenses, name='licenses'),
    path('terms', views.terms, name='terms'),
    path('choose-type', views.choose_type, name='choose_type'),
    path('individual-signup', views.individual_signup, name='individual_signup'),
    path('company-signup', views.company_signup, name='company_signup'),
    path('success', views.success, name='success'),
    path('application/view/<int:id>', views.view_application, name='view_application'),
    path('application/payment/<int:id>', views.payment_directions, name='payment_directions'),

    path('license/<int:id>', views.download_license, name='download_license'),

    path('preview/<int:id>', views.preview_file, name='preview_file'),

    path('api/', include('main.apiurls')),
]
