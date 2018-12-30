import datetime

from django_cron import CronJobBase, Schedule

from .models import Application, ApplicationStatus


def delete_expired_applications():
    """
    A cron job that should delete Applications that have passed the 2 months limit with any status other than FINISHED,
    REJECTED or ON_HOLD
    :return: None
    """
    two_months = 2 * 30
    today = datetime.datetime.today()

    apps = Application.objects.exclude(status__value__in=(ApplicationStatus.FINISHED, ApplicationStatus.REJECTED, ApplicationStatus.ON_HOLD))
    for app in apps:
        if app.created_at + datetime.timedelta(days=two_months) < today:
            app.delete()


class DeleteExpiredJob(CronJobBase):
    RUN_EVERY_MINS = 60  # every 1 hour

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'main.cronjobs.DeleteExpiredJob'    # a unique code

    def do(self):
        delete_expired_applications()
