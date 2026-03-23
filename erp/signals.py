from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Package, Installment
from datetime import date, timedelta


@receiver(post_save, sender=Package)
def create_installments(sender, instance, created, **kwargs):
    """
    Automatically creates installments when a new Package is created.
    The number of installments is stored temporarily in instance._number_of_installments
    """
    if created and hasattr(instance, '_number_of_installments'):
        num_installments = instance._number_of_installments
        amount_per_installment = instance.total_price / num_installments
        
        for i in range(num_installments):
            Installment.objects.create(
                package=instance,
                amount=amount_per_installment,
                due_date=date.today() + timedelta(days=30 * (i + 1)),
                is_paid=False
            )
