from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import  AllowAny, IsAuthenticated
from .permissions import IsAdmin
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from stocks.serializers import UsersSerializer, ReservationsSerializer, EventsSerializer, EventReservationSerializer
from stocks.models import Users, Reservations, Events, Event_Reservation
from django.utils import timezone
from minio import Minio
from pathlib import Path
from django.core.files.uploadedfile import InMemoryUploadedFile
from s3.minio import get_minio_presigned_url, upload_image_to_minio
import logging

logger = logging.getLogger(__name__)

client = Minio(endpoint="localhost:9000",   # адрес сервера
               access_key='minio',          # логин админа
               secret_key='minio124',       # пароль админа
               secure=False)      

"""
АВТОРИЗАЦИЯ ###########################################################################################
"""
@swagger_auto_schema(method='post', operation_summary="User Registration", 
                     request_body=UsersSerializer, responses={201: 'Created', 400: 'Bad Request'})
@api_view(['POST'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([])
@csrf_exempt
def registration(request):
    """
    Регистрация новых пользователей на основе роли
    """
    required_fields = ['role', 'email', 'password', 'username']
    missing_fields = [field for field in required_fields if field not in request.data]

    if missing_fields:
        return Response({'Ошибка': f'Не хватает обязательных полей: {", ".join(missing_fields)}'}, status=status.HTTP_400_BAD_REQUEST)

    if Users.objects.filter(email=request.data['email']).exists() or Users.objects.filter(username=request.data['username']).exists():
        return Response({'Ошибка': 'Пользователь с таким email или username уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    # Хэшируем пароль перед сохранением
    request.data['password'] = make_password(request.data['password'])

    serializer = UsersSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'status': 'Success'}, status=status.HTTP_201_CREATED)
    else:
        return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(method='post', request_body=UsersSerializer,
                     operation_summary="User Login", responses={200: 'OK', 401: 'Unauthorized'})
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@csrf_exempt
def login_view(request):
    try:
        email = request.data.get("email")
        password = request.data.get("password")

        user = Users.objects.get(email=email)
        user = authenticate(request, username=email, password=password)

        if user is not None and user.is_active:
            login(request, user)
            return Response({'status': 'ok'})
        else:
            return Response({'status': 'error', 'error': 'Login failed'}, status=status.HTTP_401_UNAUTHORIZED)

    except Users.DoesNotExist:
        logger.error(f'User with email {email} not found.')
        return Response({'status': 'error', 'error': 'User not found'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.error(f'Error during authentication: {e}')
        return Response({'status': 'error', 'error': 'Authentication failed'}, status=status.HTTP_401_UNAUTHORIZED)


@swagger_auto_schema(method='post', request_body=UsersSerializer,
                     operation_summary="User Logout", responses={200: 'OK'})
@api_view(['POST'])
def logout_view(request):
    logout(request._request)
    return Response({'status': 'Success'})
"""
УСЛУГИ ###########################################################################################
"""
@swagger_auto_schema(method='get', operation_summary="Get Events", responses={200: EventsSerializer(many=True)})
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_events(request, format=None):
    """
    Возвращает список событий
    """
    print('get')
    
    search_query = request.GET.get('search', '')  # Получаем параметр "search" из запроса
    status = request.GET.get('status', '')  # Получаем параметр "status" из запроса

    # Фильтруем события по полю "Status" и исключаем те, где Status = 'D'
    events = Events.objects.exclude(Status='D')

    if status:
        # Если параметр "status" передан, выполним фильтрацию по полю "Status" на основе значения status
        events = events.filter(Status=status)

    if search_query:
        # Если параметр "search" передан, выполним фильтрацию по полю "Name" на основе значения search_query
        events = events.filter(Name__icontains=search_query)

    serialized_events = []
    for event in events:
        # Generate a presigned URL for the event image
        image_url = get_minio_presigned_url(event.Image)
        
        # Добавьте поле "ImageURL" в объект события, указывающее на изображение в MinIO
        serialized_event = EventsSerializer(event).data
        serialized_event['ImageURL'] = image_url
        serialized_events.append(serialized_event)

    return Response(serialized_events)

@swagger_auto_schema(method='post', operation_summary="Create Event", 
                     request_body=EventsSerializer, responses={201: EventsSerializer()})
@api_view(['POST'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAdmin])
def post_event(request, format=None):
    """
    Добавляет новое событие
    """
    serializer = EventsSerializer(data=request.data)

    if serializer.is_valid():
        event = serializer.save()

        # Получаем файл из request.data
        image_file = request.data.get('Image')

        # Загружаем изображение в MinIO
        if isinstance(image_file, InMemoryUploadedFile):
            try:
                # Извлекаем название файла из объекта InMemoryUploadedFile
                file_name = Path(image_file.name).name

                # Создаем уникальный путь к файлу в MinIO
                minio_path = f"{file_name}"

                # Читаем данные с начала файла
                image_file.seek(0)
                # Обновляем поле Image события и загружаем в MinIO
                upload_image_to_minio(image_file, minio_path)
                event.Image = Path(file_name).stem
                event.save()
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': f'Ошибка загрузки изображения: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(method='get', operation_summary="Get Event Detail", responses={200: EventsSerializer()})
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_event(request, pk, format=None):
    event = get_object_or_404(Events, pk=pk)
    
    if request.method == 'GET':
        """
        Возвращает информацию о событии
        """
        image_url = get_minio_presigned_url(event.Image)
        serializer_data = EventsSerializer(event).data
        # Добавьте поле "ImageURL" в объект события, указывающее на изображение в MinIO
        serializer_data['ImageURL'] = image_url
        return Response(serializer_data)

@swagger_auto_schema(method='PUT', operation_summary="Update Event Information",
                      request_body=EventsSerializer, responses={200: EventsSerializer(), 400: 'Bad Request'})
@api_view(['PUT'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAdmin])
def put_event(request, pk, format=None):
    """
    Обновляет информацию о событии
    """
    event = get_object_or_404(Events, pk=pk)
    serializer = EventsSerializer(event, data=request.data, partial=True)  # Use partial=True

    if serializer.is_valid():
        # Если в запросе есть изображение, обновим его в MinIO
        image_file = request.data.get('Image')

        if isinstance(image_file, InMemoryUploadedFile):
            try:
                # Извлекаем название файла из объекта InMemoryUploadedFile
                file_name = Path(image_file.name).name

                # Создаем уникальный путь к файлу в MinIO
                minio_path = f"{file_name}"

                # Читаем данные с начала файла
                image_file.seek(0)

                # Обновляем поле Image события и загружаем в MinIO
                upload_image_to_minio(image_file, minio_path)
                serializer.validated_data['Image'] = Path(file_name).stem
            except Exception as e:
                return Response({'error': f'Ошибка загрузки изображения: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(method='DELETE', operation_summary="Delete Event", responses={204: 'No Content'})
@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAdmin])
def delete_event(request, pk, format=None):
    """
    Логически удаляет информацию о событии, устанавливая поле 'Status' в 'D'.
    """
    event = get_object_or_404(Events, pk=pk)
    
    # Установите поле 'Status' в 'D' и сохраните объект
    event.Status = 'D'
    event.save()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

# @api_view(['GET'])
# def get_reservations_for_event(request, pk, format=None):
#     """
#     Находит все заявки, где есть событие
#     """
#     # Найти все заявки, связанные с указанным event_id
#     event_reservations = Event_Reservation.objects.filter(Event_id=pk)

#     # Получить ID заявок из Event_Reservation
#     reservation_ids = event_reservations.values_list('Reserve_id', flat=True)

#     # Получить данные по заявкам из Reservations
#     reservations = Reservations.objects.filter(Reserve_id__in=reservation_ids)

#     # Сериализовать данные
#     reservation_serializer = ReservationsSerializer(reservations, many=True)
#     event_reservation_serializer = EventReservationSerializer(event_reservations, many=True)

#     # Вернуть данные в ответе
#     response_data = {
#         "reservations": reservation_serializer.data,
#         "event_reservations": event_reservation_serializer.data
#     }

#     return Response(response_data)

@swagger_auto_schema(method='POST', operation_summary="Add Event to Reservation", 
                     request_body=EventReservationSerializer, responses={200: 'OK', 404: 'Event not found'})
@api_view(['POST'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def add_event_to_reservation(request, pk, format=None):
    """
    Создает заявку, если требуется, и добавляет услугу в заявку
    """
    if not request.data:
        return Response({'error': 'Пустой запрос'}, status=status.HTTP_400_BAD_REQUEST)

    # Используйте request.user.id для получения id аутентифицированного пользователя
    user_id = request.user.user_id
    
    # Проверка наличия активной заявки со статусом 'M' для конкретного пользователя
    try:
        client = Users.objects.get(user_id=user_id)
        reservation = Reservations.objects.get(Client_id=client, Status='M')
    except Users.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    except Reservations.DoesNotExist:
        # Если активной заявки не существует, создаем новую заявку со статусом 'M'
        reservation = Reservations.objects.create(Client_id=client, Creation_date=timezone.now(), Status='M')
        reservation.save()

    # Остальной код метода остается без изменений
    try:
        event = Events.objects.get(Event_id=pk)
    except Events.DoesNotExist:
        return Response({'error': 'Событие с указанным ID не существует'}, status=status.HTTP_400_BAD_REQUEST)

    event_reservation = Event_Reservation(
        Event_id=event,
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
@swagger_auto_schema(method='get', operation_summary="Get Reservations", 
                     responses={200: ReservationsSerializer(many=True)})
@api_view(['GET'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_reservations(request, format=None):
    """
    Выводит все заявки с данными по событиям
    """
    # Проверяем роль пользователя
    if request.user.role == 'Admin':
        # Если админ, получаем все заявки
        reservations = Reservations.objects.exclude(Status='D')
    elif request.user.role == 'User':
        # Если обычный пользователь, получаем только свои заявки
        reservations = Reservations.objects.filter(Client_id=request.user.user_id, Status='M').exclude(Status='D')

    response_data = []
    for reservation in reservations:
        # Получаем все связанные заявки на мероприятия для текущей заявки
        event_reservations = Event_Reservation.objects.filter(Reserve_id=reservation)

        # Инициализируем список данных о мероприятиях
        event_data = []

        for event_reservation in event_reservations:
            # Получаем связанные с мероприятием данные
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



@swagger_auto_schema(method='GET', operation_summary="Get Reservation Detail", 
                     responses={200: ReservationsSerializer()})
@api_view(['GET'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def get_reservation(request, pk, format=None):
    """
    Выводит все данные по 1ой заявке
    """
    # Получаем объект заявки или возвращаем 404, если не существует
    reservation = get_object_or_404(Reservations, pk=pk)

    # Проверяем, является ли пользователь владельцем заявки
    if reservation.Client_id.user_id != request.user.user_id:
        return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Получаем все связанные заявки на мероприятия для текущей заявки
    event_reservations = Event_Reservation.objects.filter(Reserve_id=reservation)

    # Инициализируем список данных о мероприятиях
    event_data = []
    for event_reservation in event_reservations:
        # Получаем связанные с мероприятием данные
        event = event_reservation.Event_id
        event_data.append({
            "event_reservation": EventReservationSerializer(event_reservation).data,
            "event": EventsSerializer(event).data
        })

    # Получаем данные о текущей заявке
    reservation_data = ReservationsSerializer(reservation).data

    # Собираем итоговый ответ
    response_data = {
        "reservation": reservation_data,
        "reservation_data": event_data 
    }

    return Response(response_data)

@swagger_auto_schema(method='PUT', operation_summary="Update Reservation Info", 
                     request_body=ReservationsSerializer,responses={200: 'OK', 201: 'Created'})    
@api_view(['PUT'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAdmin])
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


@swagger_auto_schema(method='PUT', operation_summary="Change Status (User)", request_body=ReservationsSerializer,
                     responses={200: 'OK', 403: 'Forbidden', 400: 'Bad Request'})
@api_view(['PUT'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def put_reservation_user(request, pk, format=None):
    """
    Обновляет статус заявки (для пользователя)
    """
    reservation = get_object_or_404(Reservations, pk=pk)

    # Проверяем, является ли пользователь владельцем заявки
    if reservation.Client_id.user_id != request.user.user_id:
        return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    if reservation.Status != 'M':
        return Response({"detail": "Invalid initial status. Must be 'M'."}, status=status.HTTP_400_BAD_REQUEST)

    new_status = request.data.get("Status")
    if new_status == 'iP':
        reservation.Status = new_status
        reservation.Formation_date = timezone.now()
        reservation.save()
        serializer = ReservationsSerializer(reservation)
        return Response(serializer.data)
    else:
        return Response({"detail": "Invalid status. Use 'iP'"}, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(method='PUT', operation_summary="Change Status (Admin)", request_body=ReservationsSerializer,
                     responses={200: 'OK', 403: 'Forbidden', 400: 'Bad Request'})
@api_view(['PUT'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAdmin])
def put_reservation_admin(request, pk, format=None):
    """
    Обновляет статус заявки (для админа)
    """
    reservation = get_object_or_404(Reservations, pk=pk)
    if reservation.Status != 'iP':
        return Response({"detail": "Invalid initial status. Must be 'iP'."}, status=status.HTTP_400_BAD_REQUEST)

    new_status = request.data.get("Status")
    if new_status in ['C','Ca']:
        reservation.Status = new_status
        reservation.Moderator_id.user_id  = request.user.user_id 
        reservation.Completion_date=timezone.now()
        reservation.save()
        serializer = ReservationsSerializer(reservation)
        return Response(serializer.data)
    else:
        return Response({"detail": "Invalid status. Use 'C' or 'Ca' "}, status=status.HTTP_400_BAD_REQUEST)
    
@swagger_auto_schema(method='DELETE', operation_summary="Delete Reservation", 
                     responses={204: 'No Content'})
@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def delete_reservation(request, pk, format=None):
    """
    Логически удаляет информацию о заявке, устанавливая поле 'Status' в 'D'.
    """
    reservation = get_object_or_404(Reservations, pk=pk)
    if reservation.Client_id.user_id != request.user.user_id:
        return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Установите поле 'Status' в 'D' и сохраните объект
    reservation.Status = 'D'
    reservation.Completion_date=timezone.now()
    reservation.save()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

"""
М-М ###########################################################################################
"""

@swagger_auto_schema(method='DELETE', operation_summary="Delete Event from Reservation", 
                     responses={200: EventReservationSerializer()})
@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def delete_event_from_reserve(request, pk, fk, format=None):
    """
    Удаляет событие из заявки (в М-М)
    """
    event_reservations = Event_Reservation.objects.filter(Reserve_id=fk)
    if not event_reservations:
        return Response({'error': 'Нет заявок с таким id'}, status=status.HTTP_404_NOT_FOUND)
    
    if reservation.Client_id.user_id != request.user.user_id:
        return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

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

@swagger_auto_schema(method='PUT', operation_summary="Update Reservation Details", request_body=EventReservationSerializer,
                     responses={200: EventReservationSerializer(), 400: 'Bad Request'})
@api_view(['PUT'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def put_event_reservation(request, pk, fk, format=None):
    """
    Обновляет информацию о данных заявки
    """
    
    event_reservation = Event_Reservation.objects.get(Event_id = pk, Reserve_id = fk)
    if event_reservation.Reserve_id.Client_id.user_id != request.user.user_id:
        return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    serializer = EventReservationSerializer(event_reservation, data=request.data, partial=True) 

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)    




