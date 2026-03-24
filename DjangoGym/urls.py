from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from erp.views import (
    ClientViewSet,
    PackageViewSet,
    InstallmentViewSet,
    AppointmentViewSet,
    SignupView,
    GlobalStatsView,
    ChatbotView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView, SpectacularYAMLAPIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'packages', PackageViewSet)
router.register(r'installments', InstallmentViewSet)
router.register(r'appointments', AppointmentViewSet)

auth_patterns =  [
    path('signup/', SignupView.as_view(), name='signup'),  # <--- LA TUA VISTA CUSTOM
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/', include(router.urls)),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/auth/', include((auth_patterns, 'auth'))),
    path('api/stats/', GlobalStatsView.as_view(), name='global-stats'),
    path('api/chatbot/', ChatbotView.as_view(), name='chatbot'),
]