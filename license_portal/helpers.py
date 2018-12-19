import subprocess
import os

from django.http.response import HttpResponseServerError, HttpResponse
from django.views.decorators.csrf import csrf_exempt


PULL_BATCH_FILE = r'gitpull_linux.sh'
PULL_BATCH_DIR = os.path.join(r'/home', 'appdep', 'license-portal', 'license_portal')

BRANCH_REF = 'refs/heads/production'
print(PULL_BATCH_DIR)

@csrf_exempt
def gitwebhooks(request):
    """
    For linux-based OS -- triggered when someone pushes to the repo on github -- TODO: implement HMAC hash verification
    """

    proc = 'failed'
    if request.method == 'POST':
        try:
            proc = subprocess.check_output([PULL_BATCH_FILE], cwd=PULL_BATCH_DIR, shell=True)
            proc = 'done'
        except Exception as e:
            return HttpResponseServerError(e)

    return HttpResponse(proc, status=200)
