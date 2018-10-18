from django.shortcuts import render


def login(request):
    return render(request, 'login.html')


def register(request):
    return render(request, 'register.html')


def reset_password(request):
    return render(request, 'reset_password.html')


def choose_type(request):
    return render(request, 'choose_type.html')


def individual_signup(request):
    return render(request, 'individual_signup.html')
