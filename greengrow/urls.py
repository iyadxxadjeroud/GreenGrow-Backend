# greengew/urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path, include
from django.contrib import admin
from dashboard.views import GreenhouseOverview



urlpatterns = [
    path('admin/', admin.site.urls),
    path('advanced_filters/', include('advanced_filters.urls')),
    # Dashboard app API endpoints
    path('api/', include('dashboard.urls')),
    # DRF auth endpoints (for browsable API)
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # JWT Authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    #path('api/greenhouses/<greenhouse_id>/overview/', GreenhouseOverview.as_view(), name='greenhouse-overview'),
    ]