from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework import viewsets, request, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Client, Package, Installment, Appointment, User
from django.db.models import Sum, Count
from django.utils import timezone
from .serializers import ClientSerializer, PackageSerializer, InstallmentSerializer, AppointmentSerializer, SignupSerializer, ExportCSVSerializer, ChatMessageSerializer, ChatResponseSerializer
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from .permissions import IsManagerOrAdmin
from django_filters.rest_framework import DjangoFilterBackend
from .filters import PackageFilter, ClientFilter
from django.http import HttpResponse
import csv
from celery import shared_task
from .tasks import generate_and_send_csv_task
from groq import Groq
from django.conf import settings
from .chatbot_config import (
    CHATBOT_SYSTEM_PROMPT,
    CHATBOT_MODEL,
    CHATBOT_TEMPERATURE,
    CHATBOT_MAX_TOKENS,
    CHATBOT_MAX_HISTORY_MESSAGES
)

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
    serializer_class = ClientSerializer


    #prende id clienti, selecta pacchetti per quegli id clienti, selecta rate per quei pacchetti
    def get_queryset(self):
        return Client.objects.annotate(
            annotated_packages_count=Count('packages', distinct=True),
            annotated_appointments_count=Count('appointments', distinct=True)
        ).prefetch_related(
            'packages',
            'packages__installments',
            'appointments'
        ).order_by('id')

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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='send_email',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='If true, send the CSV file via email using Celery. If false, download immediately.',
                required=False,
                default=False
            )
        ],
        responses={
            200: OpenApiTypes.BINARY,
            202: {'description': 'Export queued, email will be sent'},
            400: {'description': 'No clients found'}
        }
    )
    @action(detail=False, methods=['get'], url_path='export-csv', permission_classes=[IsAuthenticated])
    def export_csv(self, request):
        # 1. Applichiamo i filtri attivi nella query string (es. ?name=Mario)
        queryset = self.filter_queryset(self.get_queryset())

        # 2. Validazione parametro usando serializer
        serializer = ExportCSVSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        send_email = serializer.validated_data.get('send_email', False)

        if not queryset.exists():
            return Response({"error": "Nessun cliente trovato con i filtri selezionati."},
                            status=status.HTTP_400_BAD_REQUEST)

        if send_email:
            # 3a. Modalità asincrona: inviare via email usando Celery
            customer_ids = list(queryset.values_list('id', flat=True))
            generate_and_send_csv_task.delay(customer_ids, request.user.email)

            return Response({
                "message": "L'esportazione è stata avviata. Riceverai il file via email a breve."
            }, status=status.HTTP_202_ACCEPTED)
        else:
            # 3b. Modalità sincrona: download immediato
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="export_clienti.csv"'

            writer = csv.writer(response)
            writer.writerow(['ID', 'Nome Cliente', 'Partita IVA', 'Email'])

            for client in queryset:
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


class ChatbotView(APIView):
    """
    AI-powered chatbot to guide users through the gym management system.
    Uses Groq's LLM API to provide intelligent assistance.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChatMessageSerializer,
        responses={200: ChatResponseSerializer},
        description="Chat with AI assistant to get help with the gym management system"
    )
    def post(self, request):
        # Validate input
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_message = serializer.validated_data['message']
        conversation_history = serializer.validated_data.get('conversation_history', [])

        try:
            # Initialize Groq client with API key from settings
            client = Groq(api_key=settings.GROQ_API_KEY)

            # Build messages for the API
            messages = [{"role": "system", "content": CHATBOT_SYSTEM_PROMPT}]

            # Add conversation history
            messages.extend(conversation_history)

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Call Groq API with configuration from chatbot_config
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=CHATBOT_MODEL,
                temperature=CHATBOT_TEMPERATURE,
                max_tokens=CHATBOT_MAX_TOKENS,
            )

            # Get assistant response
            assistant_response = chat_completion.choices[0].message.content

            # Update conversation history
            updated_history = conversation_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ]

            # Limit history to configured max messages to avoid token limits
            if len(updated_history) > CHATBOT_MAX_HISTORY_MESSAGES:
                updated_history = updated_history[-CHATBOT_MAX_HISTORY_MESSAGES:]

            response_data = {
                "response": assistant_response,
                "conversation_history": updated_history
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Chatbot error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )