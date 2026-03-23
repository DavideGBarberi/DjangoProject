from rest_framework import serializers
from .models import Client, Package, Installment, Appointment, User
from datetime import date, timedelta

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='staff')

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']

    def create(self, validated_data):
        role = validated_data.pop('role', 'staff')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=role
        )
        return user

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'

    def validate(self, data):
        client = data['client']

        # Logica: Controlliamo se il cliente ha almeno un pacchetto
        # Nota: volendo potresti controllare se ha rate pagate o se il pacchetto non è scaduto
        if not client.packages.exists():
            raise serializers.ValidationError(
                {"client": "Impossibile programmare: il cliente non ha alcun pacchetto attivo."}
            )

        # Validazione temporale base: l'appuntamento non può finire prima di iniziare
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError(
                {"end_time": "L'ora di fine deve essere successiva all'ora di inizio."}
            )

        # Controllo sovrapposizione:
        # Cerchiamo appuntamenti che iniziano prima della fine del nuovo
        # E finiscono dopo l'inizio del nuovo per lo STESSO cliente.
        overlap = Appointment.objects.filter(
            client=data['client'],
            start_time__lt=data['end_time'],
            end_time__gt=data['start_time']
        ).exists()

        if overlap:
            raise serializers.ValidationError(
                "Il cliente ha già un altro impegno programmato in questo intervallo di tempo."
            )

        return data

class InstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = '__all__'

class PackageSerializer(serializers.ModelSerializer):
    # Campo aggiuntivo solo per la POST (non salvato nel DB)
    number_of_installments = serializers.IntegerField(write_only=True, min_value=1)
    installments = InstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = Package
        fields = ['id', 'client', 'name', 'total_price', 'number_of_installments', 'installments']

    def create(self, validated_data):
        # 1. Estraiamo il numero di rate e le rimuoviamo dai dati del pacchetto
        num_rate = validated_data.pop('number_of_installments')

        # 2. Creiamo il pacchetto normalmente
        package = Package.objects.create(**validated_data)

        # 3. Logica di generazione rate: dividiamo il prezzo totale
        amount_per_installment = package.total_price / num_rate

        for i in range(num_rate):
            Installment.objects.create(
                package=package,
                amount=amount_per_installment,
                # Scadenza: oggi + 30 giorni per ogni rata
                due_date=date.today() + timedelta(days=30 * (i + 1)),
                is_paid=False
            )

        return package

class ClientSerializer(serializers.ModelSerializer):
    # Mostriamo i pacchetti all'interno del cliente (Nested)
    packages = PackageSerializer(many=True, read_only=True)
    packages_count = serializers.IntegerField(source='packages.count', read_only=True)

    appointments = AppointmentSerializer(many=True, read_only=True)
    appointments_count = serializers.IntegerField(source='appointments.count', read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'name', 'vat_number', 'email', 'packages_count', 'packages', 'appointments_count', 'appointments']


