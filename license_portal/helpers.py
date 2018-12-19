import subprocess
import os


PULL_BATCH_PATH = os.path.join('C:\\', 'Apache24-general', 'htdocs', 'django_apps', 'license_portal', 'license_portal', 'gitpull_windows.bat')
print(PULL_BATCH_PATH)


def gitwebhooks(request):
    proc = subprocess.Popen('', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    res, err = proc.communicate()

    html = """
        <h4>CMD out:</h4>
        %(cmd_out)s
        <hr>
        <h4>CMD error:</h4>
        %(cmd_err)s
        """ % {'cmd_out': format_for_html(res.decode('utf-8')),
               'cmd_err': None if not err else format_for_html(err.decode('utf-8'))}

    # return HttpResponse(html)
    print(html)
