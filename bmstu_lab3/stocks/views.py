from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from stocks.serializers import UsersSerializer, ReservationsSerializer, EventsSerializer, EventReservationSerializer
from stocks.models import Users, Reservations, Events, Event_Reservation
from rest_framework.decorators import api_view
from django.utils import timezone

"""
УСЛУГИ ###########################################################################################
"""
@api_view(['GET'])
def get_events(request, format=None):
    """
    Возвращает список событий
    """
    print('get')
    
    search_query = request.GET.get('search', '')  # Получаем параметр "search" из запроса

    # Фильтруем события по полю "Status" и исключаем те, где Status = 'D'
    events = Events.objects.exclude(Status='D')

    if search_query:
        # Если параметр "search" передан, выполним фильтрацию по полю "Name" на основе значения search_query
        events = events.filter(Name__icontains=search_query)

    serializer = EventsSerializer(events, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def post_event(request, format=None):    
    """
    Добавляет новое событие
    """
    print('post')
    serializer = EventsSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        if 'Status' in serializer.errors:
            # Если поле 'Status' не прошло валидацию, вернем список доступных статусов
            available_statuses = [
                '{}({})'.format(status[0], status[1]) for status in Events.STATUS_CHOICE
            ]
            return Response(
                {'error': 'Недопустимый статус. Доступные статусы: {}'.format(', '.join(available_statuses))},
                status=status.HTTP_400_BAD_REQUEST
            )
    
@api_view(['GET'])
def get_event(request, pk, format=None):
    stock = get_object_or_404(Events, pk=pk)
    if request.method == 'GET':
        """
        Возвращает информацию о событии
        """
        serializer = EventsSerializer(stock)
        return Response(serializer.data)

@api_view(['PUT'])
def put_event(request, pk, format=None):
    """
    Обновляет информацию о событии
    """
    event = get_object_or_404(Events, pk=pk)
    serializer = EventsSerializer(event, data=request.data, partial=True)  # Use partial=True

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        if 'Status' in serializer.errors:
            # Если поле 'Status' не прошло валидацию, вернем список доступных статусов
            available_statuses = [
                '{}({})'.format(status[0], status[1]) for status in Events.STATUS_CHOICE
            ]
            return Response(
                {'error': 'Недопустимый статус. Доступные статусы: {}'.format(', '.join(available_statuses))},
                status=status.HTTP_400_BAD_REQUEST
            )

@api_view(['DELETE'])
def delete_event(request, pk, format=None):
    """
    Логически удаляет информацию о событии, устанавливая поле 'Status' в 'D'.
    """
    event = get_object_or_404(Events, pk=pk)
    
    # Установите поле 'Status' в 'D' и сохраните объект
    event.Status = 'D'
    event.save()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def get_reservations_for_event(request, pk, format=None):
    """
    Находит все заявки, где есть событие
    """
    # Найти все заявки, связанные с указанным event_id
    event_reservations = Event_Reservation.objects.filter(Event_id=pk)

    # Получить ID заявок из Event_Reservation
    reservation_ids = event_reservations.values_list('Reserve_id', flat=True)

    # Получить данные по заявкам из Reservations
    reservations = Reservations.objects.filter(Reserve_id__in=reservation_ids)

    # Сериализовать данные
    reservation_serializer = ReservationsSerializer(reservations, many=True)
    event_reservation_serializer = EventReservationSerializer(event_reservations, many=True)

    # Вернуть данные в ответе
    response_data = {
        "reservations": reservation_serializer.data,
        "event_reservations": event_reservation_serializer.data
    }

    return Response(response_data)

@api_view(['POST'])
def add_event_to_reservation(request, pk, format=None):
    """
    Создает заявку, если требуется, и добавляет услугу в заявку
    """
    if not request.data:
        return Response({'error': 'Пустой запрос'}, status=status.HTTP_400_BAD_REQUEST)
    client = Users.objects.get(User_id=2)
    # Проверка наличия активной заявки со статусом 'M' для конкретного пользователя
    try:
        reservation = Reservations.objects.get(Client_id=client, Status='M')
    except Reservations.DoesNotExist:
        # Если активной заявки не существует, создаем новую заявку со статусом 'M'
        reservation = Reservations.objects.create(Client_id=client, Creation_date=timezone.now(), Status='M')
        reservation.save()

    # Получаем экземпляр события по его идентификатору (pk)
    try:
        event = Events.objects.get(Event_id=pk)
    except Events.DoesNotExist:
        # Обработка случая, если события с указанным ID не существует
        return Response({'error': 'Событие с указанным ID не существует'}, status=status.HTTP_400_BAD_REQUEST)

    # Добавление услуги в заявку
    event_reservation = Event_Reservation(
        Event_id=event,  # Используем экземпляр события
        Reserve_id=reservation,
        Group_info=request.data.get('Group_info'),
        Group_size=request.data.get('Group_size'),
        Date=request.data.get('Date')
    )
    event_reservation.save()

    serializer = EventReservationSerializer(event_reservation)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

"""
ЗАЯВКИ ###########################################################################################
"""

@api_view(['GET'])
def get_reservations(request, format=None):
    """
    Выводит все заявки с данными по событиям
    """
    # Получаем все заявки, которые не были удалены ('D')
    reservations = Reservations.objects.exclude(Status='D')

    # Инициализируем пустой список для хранения конечных данных ответа
    response_data = []

    for reservation in reservations:
        # Получить все связанные заявки на мероприятия для текущей заявки
        event_reservations = Event_Reservation.objects.filter(Reserve_id=reservation)

        # Инициализируем список данных о мероприятиях
        event_data = []

        for event_reservation in event_reservations:
            # Получить связанные с мероприятием данные
            event = event_reservation.Event_id
            event_data.append({
                "event_reservation": EventReservationSerializer(event_reservation).data,
                "event": EventsSerializer(event).data
            })

        reservation_data = ReservationsSerializer(reservation).data
        response_data.append({
            "reservation": reservation_data,
            "reservation_data": event_data
        })

    return Response(response_data)

@api_view(['GET'])
def get_reservation(request, pk, format=None):
    """
    Выводит все данные по 1ой заявке
    """
    reservation = get_object_or_404(Reservations, pk=pk)
    # Находим связанные данные из таблицы Event_Reservation
    response_data = []


    # Получить все связанные заявки на мероприятия для текущей заявки
    event_reservations = Event_Reservation.objects.filter(Reserve_id=reservation)

    # Инициализируем список данных о мероприятиях
    event_data = []
    for event_reservation in event_reservations:
        # Получить связанные с мероприятием данные
        event = event_reservation.Event_id
        event_data.append({
            "event_reservation": EventReservationSerializer(event_reservation).data,
            "event": EventsSerializer(event).data
        })

        reservation_data = ReservationsSerializer(reservation).data
        response_data.append({
            "reservation": reservation_data,
            "reservation_data": event_data 
        })

    return Response(response_data)
    
@api_view(['PUT'])
def put_reservation(request, pk, format=None):
    """
    Обновляет информацию о заявке
    """
    reservation = get_object_or_404(Reservations, pk=pk)

    if 'Status' in request.data:
        return Response({'error': 'Нельзя изменять статус через это представление'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ReservationsSerializer(reservation, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    

@api_view(['PUT'])
def put_reservation_user(request, pk, format=None):
    """
    Обновляет статус заявки (для пользователя)
    """
    reservation = get_object_or_404(Reservations, pk=pk)

    # Получите новое значение статуса из запроса
    new_status = request.data.get("Status")

    # Проверьте, что новый статус допустим (равен 'C' или 'D')
    if new_status in ['M']:
        reservation.Status = new_status
        reservation.save()
        serializer = ReservationsSerializer(reservation)
        return Response(serializer.data)
    else:
        return Response({"detail": "Invalid status. Use 'M'"}, status=status.HTTP_400_BAD_REQUEST) 

@api_view(['PUT'])
def put_reservation_admin(request, pk, format=None):
    """
    Обновляет статус заявки (для админа)
    """
    reservation = get_object_or_404(Reservations, pk=pk)

    # Получите новое значение статуса из запроса
    new_status = request.data.get("Status")

    if new_status in ['iP', 'Ca', 'C']:
        reservation.Status = new_status
        reservation.save()
        serializer = ReservationsSerializer(reservation)
        return Response(serializer.data)
    else:
        return Response({"detail": "Invalid status. Use 'iP' or 'Ca' or 'C'"}, status=status.HTTP_400_BAD_REQUEST)  
    

@api_view(['DELETE'])
def delete_reservation(pk, format=None):
    """
    Логически удаляет информацию о событии, устанавливая поле 'Status' в 'D'.
    """
    reservation = get_object_or_404(Reservations, pk=pk)
    
    # Установите поле 'Status' в 'D' и сохраните объект
    reservation.Status = 'D'
    reservation.save()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

"""
М-М ###########################################################################################
"""
@api_view(['DELETE'])
def delete_event_from_reserve(request, pk, fk, format=None):
    """
    Удаляет событие из заявки (в М-М)
    """
    event_reservations = Event_Reservation.objects.filter(Reserve_id=fk)
    if not event_reservations:
        return Response({'error': 'Нет заявок с таким id'}, status=status.HTTP_404_NOT_FOUND)

    try:
        event_reservation = Event_Reservation.objects.get(Event_id=pk, Reserve_id=fk)
    except Event_Reservation.DoesNotExist:
        return Response({'error': 'Событие не найдено в заявке'}, status=status.HTTP_404_NOT_FOUND)

    # Удаляем связь
    event_reservation.delete()

    # Проверяем, остались ли другие связи для этой заявки
    remaining_event_reservations = Event_Reservation.objects.filter(Reserve_id=fk)
    if not remaining_event_reservations:
        reservation = Reservations.objects.get(Reserve_id=fk)
        reservation.Status = 'D'
        reservation.save()
        return Response({'message': 'Заявка удалена'})

    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['PUT'])
def put_event_reservation(request, pk, fk, format=None):
    """
    Обновляет информацию о данных заявки
    """
    event_reservation = Event_Reservation.objects.get(Event_id = pk, Reserve_id = fk)
    serializer = EventReservationSerializer(event_reservation, data=request.data, partial=True) 

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)    




