import subprocess
import os

from django.http.response import HttpResponseServerError, HttpResponse


PULL_BATCH_FILE = 'gitpull_windows.bat'
PULL_BATCH_DIR = os.path.join('C:\\', 'Apache24-general', 'htdocs', 'django_apps', 'license_portal', 'license_portal')


def gitwebhooks(request):
    proc = subprocess.Popen([PULL_BATCH_FILE], cwd=PULL_BATCH_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    res, err = proc.communicate()

    if err:
        return HttpResponseServerError(err)

    return HttpResponse(status=200)
