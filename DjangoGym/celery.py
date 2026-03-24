import os
from celery import Celery

# Imposta il modulo delle impostazioni predefinito di Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoGym.settings')

app = Celery('DjangoGym')

# Legge le configurazioni dal settings.py usando il prefisso CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carica automaticamente i task dai file tasks.py di tutte le app registrate
app.autodiscover_tasks()