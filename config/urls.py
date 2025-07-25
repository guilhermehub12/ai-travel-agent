from django.contrib import admin
from django.urls import path, include
from flights.views import AlertsDashboardView
urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', AlertsDashboardView.as_view(), name='dashboard'),
    path('api/v1/', include('flights.urls')),
]
