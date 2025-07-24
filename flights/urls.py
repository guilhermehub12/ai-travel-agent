from django.urls import path
from .views import FlightSearchView, PriceAlertCreateView, CheckAlertsView

urlpatterns = [
    path('search-flights/', FlightSearchView.as_view(), name='search-flights'),
    path('create-alert/', PriceAlertCreateView.as_view(), name='create-alert'),
    path('check-alerts/', CheckAlertsView.as_view(), name='check-alerts'),
]
