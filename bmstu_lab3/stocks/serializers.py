from .models import Users, Reservations, Events, Event_Reservation
from rest_framework import serializers


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['role', 'email', 'username', 'password']

class ReservationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservations
        fields = '__all__'

class EventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Events
        fields = '__all__'

class EventReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event_Reservation
        fields = '__all__'
