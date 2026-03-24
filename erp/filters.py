import django_filters
from .models import Package, Client

class PackageFilter(django_filters.FilterSet):
    #campo input               tipo filtro   nome campo del modello   espressione
    min_price = django_filters.NumberFilter(field_name="total_price", lookup_expr='gt')
    max_price = django_filters.NumberFilter(field_name="total_price", lookup_expr='lt')

    class Meta:
        model = Package
        fields = ['min_price', 'max_price']


class ClientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Client
        fields = ['name']