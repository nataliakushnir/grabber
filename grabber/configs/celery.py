import os
import logging

from celery import Celery
from celery.schedules import crontab

from django.conf import settings


error_file_logger = logging.getLogger('error_file')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configs.settings.base')

app = Celery('grabber', broker=settings.BROKER_URL)

app.conf.enable_utc = False # default TZ for Celery is still UTC
app.conf.timezone = 'UTC'

app.config_from_object('django.conf:settings')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'parse_products': {
        'task': 'main.tasks.start_products_retrieve',
        'schedule': crontab(minute=1, hour=00),
        'kwargs': {
        }
    },
}
