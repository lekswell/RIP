from django.contrib import admin
from stocks import views
from django.urls import include, path
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import routers

router = routers.DefaultRouter()

schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('', include(router.urls)),

    path('events/', views.get_events, name='events-list'),
    path('events/add/', views.post_event, name='events-add'),
    path('events/<int:pk>/', views.get_event, name='events-detail'),
    path('events/<int:pk>/edit/', views.put_event, name='events-edit'),
    path('events/<int:pk>/delete/', views.delete_event, name='events-delete'),
   #path('events/<int:pk>/reserves/', views.get_reservations_for_event, name='events-reservations'),
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

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('admin/', admin.site.urls),

    path('auth/register',  views.registration, name='register'),
    path('auth/login',  views.login_view, name='login'),
    path('auth/logout', views.logout_view, name='logout'),
   #  path('users/registration/', views.registration, name='registration'),
   #  path('users/login/', views.login_view, name='login'),
   #  path('users/logout/', views.logout_view, name='logout'),
]
