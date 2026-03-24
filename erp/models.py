
# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return f"{self.username} ({self.role})"

class Client(models.Model):
    name = models.CharField(max_length=100)
    vat_number = models.CharField(max_length=20, unique=True) # Partita IVA
    email = models.EmailField()

    def __str__(self):
        return self.name


from django.db import models
from django.core.validators import MinValueValidator

class Package(models.Model):
    client = models.ForeignKey('erp.Client', on_delete=models.CASCADE, related_name='packages')
    name = models.CharField(max_length=100)
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        # 1. Difesa lato Python (per i Form e l'Admin)
        validators=[MinValueValidator(0.01)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # 2. Difesa lato Database (L'ultima parola)
            models.CheckConstraint(
                condition=models.Q(total_price__gt=0), # USA 'condition'
                name='total_price_must_be_positive'
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.client.name}"

class Installment(models.Model):
    package = models.ForeignKey('erp.Package', on_delete=models.CASCADE, related_name='installments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField() # Scadenza rata
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Rata da {self.amount} per {self.package.name}"

class Appointment(models.Model):
    client = models.ForeignKey('erp.Client', on_delete=models.CASCADE, related_name='appointments')
    package = models.ForeignKey('erp.Package', on_delete=models.SET_NULL, null=True, related_name='appointments')
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - {self.client.name}"