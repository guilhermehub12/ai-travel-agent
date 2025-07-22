from django.urls import path
from .views import FlightSearchView

urlpatterns = [
    path('search-flights/', FlightSearchView.as_view(), name='search-flights'),
]
