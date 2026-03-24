from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Client, Package, Installment, Appointment, User
from django.db.models import Sum, Count
from django.utils import timezone
from .serializers import ClientSerializer, PackageSerializer, InstallmentSerializer, AppointmentSerializer, SignupSerializer
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from .permissions import IsManagerOrAdmin
from django_filters.rest_framework import DjangoFilterBackend
from .filters import PackageFilter, ClientFilter
from django.http import HttpResponse
import csv

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'limit' # Permette al frontend di decidere (es: ?limit=50)
    max_page_size = 100             # Limite massimo per evitare abusi

class GlobalStatsView(APIView):
    # Solo gli amministratori e manager dovrebbero vedere i dati sensibili dell'azienda
    permission_classes = [IsManagerOrAdmin]

    def get(self, request):
        today = timezone.now()
        first_day_month = today.replace(day=1, hour=0, minute=0, second=0)

        # 1. Metriche Finanziarie
        total_revenue_ever = Installment.objects.filter(is_paid=True).aggregate(Sum('amount'))['amount__sum'] or 0

        # Incasso previsto questo mese (rate che scadono questo mese)
        expected_this_month = Installment.objects.filter(
            due_date__month=today.month,
            due_date__year=today.year
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # Incasso reale questo mese (rate pagate questo mese)
        # Nota: servirebbe un campo 'payment_date' nel modello per essere precisi,
        # qui usiamo la due_date come approssimazione
        collected_this_month = Installment.objects.filter(
            due_date__month=today.month,
            due_date__year=today.year,
            is_paid=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # 2. Metriche Operative
        total_clients = Client.objects.count()
        active_packages = Package.objects.count()

        # Appuntamenti oggi
        appointments_today = Appointment.objects.filter(
            start_time__date=today.date()
        ).count()

        # 3. Analisi Morosità (Rate scadute e non pagate)
        overdue_installments = Installment.objects.filter(
            due_date__lt=today.date(),
            is_paid=False
        )
        total_overdue_amount = overdue_installments.aggregate(Sum('amount'))['amount__sum'] or 0

        return Response({
            "financial": {
                "total_revenue_ever": total_revenue_ever,
                "expected_this_month": expected_this_month,
                "collected_this_month": collected_this_month,
                "total_overdue_amount": total_overdue_amount,
            },
            "operational": {
                "total_clients": total_clients,
                "active_packages": active_packages,
                "appointments_today": appointments_today,
            },
            "kpi": {
                "collection_rate": (collected_this_month / expected_this_month * 100) if expected_this_month > 0 else 0
            }
        })

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny] # Chiunque può registrarsi
    serializer_class = SignupSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    pagination_class = StandardResultsSetPagination  # Sovrascrive il default di settings.py
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend]
    filterset_class = ClientFilter

    @action(detail=True, methods=['get'], permission_classes=[IsManagerOrAdmin]) # <-- PROTEZIONE)
    def summary(self, request, pk=None):
        client = self.get_object()

        # 1. Calcolo del debito totale (Somma rate non pagate)
        # Accediamo a tutte le rate attraverso la relazione: client -> packages -> installments
        total_debt = Installment.objects.filter(
            package__client=client,
            is_paid=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0.00

        # 2. Prossimo appuntamento (Il primo nel futuro)
        next_app = client.appointments.filter(
            start_time__gte=timezone.now()
        ).order_by('start_time').first()

        # 3. ULTIMO Appuntamento (il più recente nel passato)
        last_app = client.appointments.filter(
            start_time__lt=timezone.now()
        ).order_by('-start_time').first()  # Il segno '-' indica ordine decrescente

        # 4. Conteggio pacchetti attivi
        active_packages = client.packages.count()

        return Response({
            "client_name": client.name,
            "total_debt": total_debt,
            "active_packages_count": active_packages,
            "next_appointment": next_app.start_time if next_app else None,
            "next_appointment_title": next_app.title if next_app else "Nessuno",
            "last_appointment": last_app.start_time if last_app else None,
            "last_appointment_title": last_app.title if last_app else "Nessuno",
        })

    @action(detail=False, methods=['get'], url_path='export-csv', permission_classes=[IsAuthenticated])
    def export_csv(self, queryset):
        data = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export_clienti.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Nome Cliente', 'P. IVA', 'Email'])

        for client in data:
            writer.writerow([client.id, client.name, client.vat_number, client.email])


        return response


class PackageViewSet(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [IsAuthenticated]

    # Aggiungiamo il backend e la classe di filtro
    filter_backends = [DjangoFilterBackend]
    filterset_class = PackageFilter

class InstallmentViewSet(viewsets.ModelViewSet):
    queryset = Installment.objects.all()
    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated]

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]