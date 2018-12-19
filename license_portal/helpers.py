import subprocess
import os

from django.http.response import HttpResponseServerError, HttpResponse


PULL_BATCH_PATH = os.path.join('C:\\', 'Apache24-general', 'htdocs', 'django_apps', 'license_portal', 'license_portal', 'gitpull_windows.bat')


def gitwebhooks(request):
    proc = subprocess.Popen([PULL_BATCH_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    res, err = proc.communicate()

    if err:
        return HttpResponseServerError(err)

    return HttpResponse(status=200)
