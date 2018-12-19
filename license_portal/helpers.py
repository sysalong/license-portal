import subprocess
import os

from django.http.response import HttpResponseServerError, HttpResponse


PULL_BATCH_FILE = r'gitpull_windows.bat'
PULL_BATCH_DIR = os.path.join('C:\\', 'Apache24-general', 'htdocs', 'django_apps', 'license_portal', 'license_portal')


def gitwebhooks(request):
    """
    For windows OS
    """
    try:
        proc = subprocess.check_output([PULL_BATCH_FILE], cwd=PULL_BATCH_DIR, shell=True)
    except Exception as e:
        return HttpResponseServerError(e)

    # res, err = proc.communicate()

    # if err:
    #     return HttpResponseServerError(err)

    return HttpResponse(proc, status=200)
