"""
URL configuration for lab3 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from stocks import views
from django.urls import include, path
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),

    path('events/', views.get_events, name='events-list'),
    path('events/add/', views.post_event, name='events-add'),
    path('events/<int:pk>/', views.get_event, name='events-detail'),
    path('events/<int:pk>/edit/', views.put_event, name='events-edit'),
    path('events/<int:pk>/delete/', views.delete_event, name='events-delete'),
    path('events/<int:pk>/reserves/', views.get_reservations_for_event, name='events-reservations'),
    path('events/<int:pk>/add/', views.add_event_to_reservation, name='events-add-to-reservation'),


    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    path('reserves/', views.get_reservations, name='reservations-list'),
    path('reserves/<int:pk>/', views.get_reservation, name='reservations-detail'),
    path('reserves/<int:pk>/edit/', views.put_reservation, name='reservations-edit'),
    path('reserves/<int:pk>/edit_status_user/', views.put_reservation_user, name='reservations-edit-user'),
    path('reserves/<int:pk>/edit_status_admin/', views.put_reservation_admin, name='reservations-edit-admin'),
    path('reserves/<int:pk>/delete/', views.delete_reservation, name='reservations-delete'),

    path('reserves/<int:pk>/<int:fk>/delete/', views.delete_event_from_reserve, name='event-delete-from-reservation'),
    path('reserves/<int:pk>/<int:fk>/edit/', views.put_event_reservation, name='data-event-reservation-edit'),


    path('admin/', admin.site.urls),
]
