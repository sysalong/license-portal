from django.urls import path

from . import views


app_name = 'moderation'

urlpatterns = [
    path('', views.index, name='index'),
    path('admin', views.admin, name='admin'),
    path('application/view/<int:id>', views.view_application, name='view_application'),
    path('application/action/<int:id>', views.action_application, name='action_application'),
]