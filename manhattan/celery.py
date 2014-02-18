from __future__ import absolute_import
import os

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'manhattan.settings')
app = Celery('manhattan')
app.config_from_object('django.conf:settings')
app.conf.update(
    BROKER_URL='redis://127.0.0.1:6379/2',
    CELERY_IGNORE_RESULT=False,
    CELERYBEAT_SCHEDULER='djcelery.schedulers.DatabaseScheduler',
    CELERY_ACCEPT_CONTENT=['pickle', 'json'],
    CELERY_TASK_SERIALIZER='pickle',
)
app.autodiscover_tasks(settings.INSTALLED_APPS, related_name='tasks')