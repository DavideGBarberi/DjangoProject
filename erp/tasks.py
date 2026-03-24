import csv
from io import StringIO
from celery import shared_task
from django.core.mail import EmailMessage
from .models import Client


@shared_task
def generate_and_send_csv_task(customer_ids, user_email):
    # 1. Recupero dati
    queryset = Client.objects.filter(id__in=customer_ids)

    # 2. Generazione CSV in memoria (StringIO)
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['ID', 'Nome Cliente', 'Partita IVA', 'Email'])

    for client in queryset:
        writer.writerow([client.id, client.name, client.vat_number, client.email])

    # 3. Preparazione Email
    subject = 'Il tuo export clienti è pronto'
    body = 'In allegato trovi il file CSV con i dati richiesti dal gestionale palestre.'
    email = EmailMessage(subject, body, 'davideg1.dgb@gmail.com', [user_email])

    # 4. Allegato: trasformiamo il buffer di testo in byte per l'invio
    email.attach('export_clienti.csv', csv_buffer.getvalue(), 'text/csv')

    # 5. Invio
    email.send()

    return f"Email inviata a {user_email}"