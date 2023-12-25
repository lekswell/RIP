from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status

from s3.minio import get_minio_presigned_url, upload_image_to_minio

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.hashers import make_password, check_password

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from minio import Minio
from pathlib import Path
import hashlib
import secrets
import requests

from stocks.serializers import UsersSerializer, ReservationsSerializer, EventsSerializer, EventReservationSerializer
from stocks.models import Users, Reservations, Events, Event_Reservation
from stocks.redis_view import (
    set_key,
    get_value,
    delete_value
)

client = Minio(endpoint="localhost:9000",   # адрес сервера
               access_key='minio',          # логин админа
               secret_key='minio124',       # пароль админа
               secure=False)      

"""
АВТОРИЗАЦИЯ ###########################################################################################
"""
def check_authorize(request):
    existing_session = request.COOKIES.get('session_key')
    
    if existing_session and get_value(existing_session):
        user_id = get_value(existing_session)
        try:
            user = Users.objects.get(User_id=user_id)
            return user
        except Users.DoesNotExist:
            pass
    
    return None

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['Email', 'Password', 'Username'],
    properties={
        'Email': openapi.Schema(type=openapi.TYPE_STRING),
        'Password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD),
        'Username': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
    responses={
        201: 'Пользователь успешно создан',
        400: 'Не хватает обязательных полей или пользователь уже существует',
    },
    operation_summary='Регистрация нового пользователя'
)
@api_view(['POST'])
def register(request, format=None):
    required_fields = ['Email', 'Username', 'Password']
    missing_fields = [field for field in required_fields if field not in request.data]

    if missing_fields:
        return Response({'Ошибка': f'Не хватает обязательных полей: {", ".join(missing_fields)}'}, status=status.HTTP_400_BAD_REQUEST)

    if Users.objects.filter(Email=request.data['Email']).exists() or Users.objects.filter(Username=request.data['Username']).exists():
        return Response({'Ошибка': 'Пользователь с таким email или username уже существует'}, status=status.HTTP_400_BAD_REQUEST)

    password_hash = make_password(request.data["Password"])

    Users.objects.create(
        Email=request.data['Email'],
        Username=request.data['Username'],
        Password=password_hash,
        Role='User',
    )
    return Response({'Пользователь успешно зарегистрирован'},status=status.HTTP_201_CREATED)

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['Email', 'Password'],
    properties={
        'Email': openapi.Schema(type=openapi.TYPE_STRING),
        'Password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD),
        },
    ),
    responses={
        200: 'Успешная авторизация', 
        400: 'Неверные параметры запроса или отсутствуют обязательные поля',
        401: 'Неавторизованный доступ',
    },
    operation_summary='Метод для авторизации'
)
@api_view(['POST'])
def login(request, format=None):
    existing_session = request.COOKIES.get('session_key')

    if existing_session and get_value(existing_session):
        return Response({'User_id': get_value(existing_session)})

    email = request.data.get("Email")
    password = request.data.get("Password")
    
    if not email or not password:
        return Response({'error': 'Необходимы почта и пароль'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = Users.objects.get(Email=email)
    except Users.DoesNotExist:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    if check_password(password, user.Password):
        random_part = secrets.token_hex(8)
        session_hash = hashlib.sha256(f'{user.User_id}:{email}:{random_part}'.encode()).hexdigest()
        set_key(session_hash, user.User_id)

        serialize = UsersSerializer(user)
        response = Response(serialize.data)
        response.set_cookie('session_key', session_hash, max_age=86400)
        return response

    return Response(status=status.HTTP_401_UNAUTHORIZED)

@swagger_auto_schema(
    method='get',
    responses={
        200: 'Успешный выход',
        401: 'Неавторизованный доступ',
    },
    operation_summary='Метод для выхода пользователя из системы'
)
@api_view(['GET'])
def logout(request):
    session_key = request.COOKIES.get('session_key')

    if session_key:
        if not get_value(session_key):
            return Response({'error': 'Вы не авторизованы'}, status=status.HTTP_401_UNAUTHORIZED)
        delete_value(session_key)
        response = Response({'message': 'Вы успешно вышли из системы'})
        response.delete_cookie('session_key')
        return response
    else:
        return Response({'error': 'Вы не авторизованы'}, status=status.HTTP_401_UNAUTHORIZED)

"""
УСЛУГИ ###########################################################################################
"""
@swagger_auto_schema(method='get', operation_summary="Возвращает список событий", responses={200: EventsSerializer(many=True)})
@api_view(['GET'])
def get_events(request, format=None):
    """
    Возвращает список событий
    """
    print('get')
    
    search_query = request.GET.get('search', '')  # Получаем параметр "search" из запроса
    status = request.GET.get('status', '')  # Получаем параметр "status" из запроса
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

@swagger_auto_schema(
        method='post', 
        operation_summary="Добавляет новое событие", 
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'Name': openapi.Schema(type=openapi.TYPE_STRING),
                'Start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'End_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'Image': openapi.Schema(type=openapi.TYPE_FILE),
                'Status': openapi.Schema(type=openapi.TYPE_STRING),
                'Info': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['Name', 'Start_date', 'End_date', 'Status', 'Info', 'Image']
    ),
        responses={201: EventsSerializer()})
@api_view(['POST'])
def post_event(request, format=None):
    """
    Добавляет новое событие
    """
    # Проверяем авторизацию и роль "Admin"
    user = check_authorize(request)
    if not (user and user.Role == 'Admin'):
        return Response({'error': 'необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
    
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

@swagger_auto_schema(method='get', operation_summary="Возвращает информацию о событии", responses={200: EventsSerializer()})
@api_view(['GET'])
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

@swagger_auto_schema(
        method='PUT', 
        operation_summary="Обновляет информацию о событии",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'Name': openapi.Schema(type=openapi.TYPE_STRING),
                'Start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'End_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'Image': openapi.Schema(type=openapi.TYPE_FILE),
                'Status': openapi.Schema(type=openapi.TYPE_STRING),
                'Info': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: EventsSerializer(), 400: 'Bad Request'})
@api_view(['PUT'])
def put_event(request, pk, format=None):
    """
    Обновляет информацию о событии
    """
    user = check_authorize(request)
    if not (user and user.Role == 'Admin'):
        return Response({'error': 'необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
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


@swagger_auto_schema(method='DELETE', operation_summary="Удаляет информацию о событии", responses={204: 'No Content'})
@api_view(['DELETE'])
def delete_event(request, pk, format=None):
    """
    Логически удаляет информацию о событии, устанавливая поле 'Status' в 'D'.
    """
    user = check_authorize(request)
    if not (user and user.Role == 'Admin'):
        return Response({'error': 'необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
    
    event = get_object_or_404(Events, pk=pk)
    
    # Установите поле 'Status' в 'D' и сохраните объект
    event.Status = 'D'
    event.save()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

@swagger_auto_schema(
        method='POST', 
        operation_summary="Добавляет услугу в заявку", 
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'Group_info': openapi.Schema(type=openapi.TYPE_STRING),
                'Group_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                'Date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            },
        required=['Group_info', 'Group_size', 'Date']
        ),
        responses={200: 'OK', 404: 'Событие не найдено'})
@api_view(['POST'])
def add_event_to_reservation(request, pk, format=None):
    """
    Создает заявку, если требуется, и добавляет услугу в заявку
    """
    user = check_authorize(request)
    if not (user and user.Role == 'User'):
        return Response({'error': 'необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
    # Проверка наличия активной заявки со статусом 'M' для конкретного пользователя
    try:
        reservation = Reservations.objects.get(Client_id=user, Status='M')
    except Reservations.DoesNotExist:
        # Если активной заявки не существует, создаем новую заявку со статусом 'M'
        reservation = Reservations.objects.create(Client_id=user, Creation_date=timezone.now(), Status='M')
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
@swagger_auto_schema(method='get', operation_summary="Выводит все заявки", 
                     responses={200: ReservationsSerializer(many=True)})
@api_view(['GET'])
def get_reservations(request, format=None):
    """
    Выводит все заявки с данными по событиям
    """
    user = check_authorize(request)
    if not user:
        return Response({'error': 'необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)

    # Получение параметров запроса
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    status = request.query_params.get('status')

    # Проверка роли пользователя
    if user.Role == 'Admin':
        # Возвращаем все заявки, кроме заявок со статусом 'D'
        reservations = Reservations.objects.exclude(Status='D')
    elif user.Role == 'User':
        # Возвращаем заявки только для текущего пользователя со статусом 'M'
        reservations = Reservations.objects.filter(Client_id=user, Status='M')

    # Фильтрация по дате и статусу
    if start_date:
        start_date = parse_date(start_date)
        reservations = reservations.filter(Formation_date__gte=start_date)
    if end_date:
        end_date = parse_date(end_date)
        reservations = reservations.filter(Formation_date__lte=end_date)
    if status:
        reservations = reservations.filter(Status=status)

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


@swagger_auto_schema(method='GET', operation_summary="Выводит все данные по 1ой заявке", 
                     responses={200: ReservationsSerializer()})
@api_view(['GET'])
def get_reservation(request, pk, format=None):
    """
    Выводит все данные по 1ой заявке
    """
    user = check_authorize(request)
    if not user:
        return Response({'error': 'необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)

    # Получаем заявку по указанному идентификатору (pk)
    try:
        reservation = Reservations.objects.get(Reserve_id=pk)
    except Reservations.DoesNotExist:
        return Response({'error': 'Заявка с указанным ID не существует'}, status=status.HTTP_404_NOT_FOUND)

    # Проверка роли пользователя
    if user.Role == 'Admin' or user == reservation.Client_id:
        # Возвращаем данные только для Admin или для пользователя, чья это заявка
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
    else:
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

@swagger_auto_schema(
        method='PUT', 
        operation_summary="Обновляет информацию о заявке", 
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'Moderator_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'Creation_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                'Formation_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                'Completion_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
            },
        ),
        responses={200: 'OK', 201: 'Обновлено'})    
@api_view(['PUT'])
def put_reservation(request, pk, format=None):
    """
    Обновляет информацию о заявке
    """
    user = check_authorize(request)
    if not (user and user.Role == 'Admin'):
        return Response({'error': 'необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
    reservation = get_object_or_404(Reservations, pk=pk)

    if 'Status' in request.data:
        return Response({'error': 'Нельзя изменять статус через это представление'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ReservationsSerializer(reservation, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    


@swagger_auto_schema(
        method='PUT', 
        operation_summary="Обновляет статус заявки (для пользователя)", 
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'Status': openapi.Schema(type=openapi.TYPE_STRING),
            },
        required=['Status']
        ),
        responses={200: 'OK', 403: 'Forbidden', 400: 'Bad Request'})
@api_view(['PUT'])
def put_reservation_user(request, pk, format=None):
    """
    Обновляет статус заявки (для пользователя)
    """
    user = check_authorize(request)
    if not (user and user.Role == 'User'):
        return Response({'error': 'необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
    reservation = get_object_or_404(Reservations, pk=pk)
    if reservation.Client_id != user:
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
    if reservation.Status != 'M':
        return Response({"detail": "Заявка не является черновиком"}, status=status.HTTP_400_BAD_REQUEST)

    new_status = request.data.get("Status")
    if new_status == 'iP':
        reservation.Status = new_status
        reservation.Formation_date = timezone.now()
        reservation.save()
        serializer = ReservationsSerializer(reservation)
        return Response(serializer.data)
    else:
        return Response({"detail": "Новый статус должен быть 'iP'"}, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
        method='PUT', 
        operation_summary="Обновляет статус заявки (для админа)", 
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'Status': openapi.Schema(type=openapi.TYPE_STRING),
            },
        required=['Status']
        ),
        responses={200: 'OK', 403: 'Forbidden', 400: 'Bad Request'})
@api_view(['PUT'])
def put_reservation_admin(request, pk, format=None):
    """
    Обновляет статус заявки (для админа)
    """
    user = check_authorize(request)
    if not (user and user.Role == 'Admin'):
        return Response({'error': 'Необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
    reservation = get_object_or_404(Reservations, pk=pk)
    if reservation.Status != 'iP':
        return Response({"detail": "Заявка не в работе"}, status=status.HTTP_400_BAD_REQUEST)

    new_status = request.data.get("Status")
    if new_status in ['C','Ca']:
        reservation.Status = new_status
        reservation.Completion_date=timezone.now()
        reservation.save()
        serializer = ReservationsSerializer(reservation)
        return Response(serializer.data)
    else:
        return Response({"detail": "Новый статус должен быть 'C' или 'Ca' "}, status=status.HTTP_400_BAD_REQUEST)
    
@swagger_auto_schema(method='DELETE', operation_summary="удаляет информацию о заявке", 
                     responses={204: 'No Content'})
@api_view(['DELETE'])
def delete_reservation(request, pk, format=None):
    """
    Логически удаляет информацию о заявке, устанавливая поле 'Status' в 'D'.
    """
    user = check_authorize(request)
    if not (user and user.Role == 'User'):
        return Response({'error': 'Необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)

    # Получаем объект Reservations или возвращаем 404, если объект не найден
    reservation = get_object_or_404(Reservations, pk=pk)

    # Проверяем, что заявка принадлежит текущему пользователю
    if reservation.Client_id != user:
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

    # Установите поле 'Status' в 'D' и установите Completion_date
    reservation.Status = 'D'
    reservation.Completion_date = timezone.now()
    reservation.save()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

@swagger_auto_schema(method='POST', operation_summary="отправляет id заявки на асинхронный сервер")
@api_view(['POST'])
def send_reserve_id(request, pk):
    key = "P-j8TR9-vxbePac3Du1y"

    data = {
        'pk': pk,
        'key': key
    }

    try:
        response = requests.post('http://localhost:8080/Async/', json=data)

        if response.status_code == 204:
            return Response({'message': 'Запрос успешно отправлен'}, status=204)
        else:
            return Response({'error': 'Не удалось отправить запрос. Статус ответа: {}'.format(response.status_code)}, status=500)
    except Exception as e:
        print("Exception:", str(e))  # Вывести исключение для отладки
        return Response({'error': 'Error: {}'.format(str(e))}, status=500)



@api_view(['PUT'])
def put_reservation_available_field(request, format=None):
    """
    Обновляет информацию о заявке
    """ 
    try:
        result = request.data['result']
        pk = request.data['pk']
    except KeyError:
        return Response({'error': 'Missing "result" field in the request data.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Update the reservation based on the data received asynchronously
        reservation = get_object_or_404(Reservations, pk=pk)
        reservation.Available = result
        reservation.save()

        # Serialize and return the updated reservation data
        serializer = ReservationsSerializer(reservation)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': 'Не удалось обновить заявку. {}'.format(str(e))}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
М-М ###########################################################################################
"""

@swagger_auto_schema(method='DELETE', operation_summary="Удаляет событие из заявки (в М-М)", 
                     responses={200: EventReservationSerializer()})
@api_view(['DELETE'])
def delete_event_from_reserve(request, pk, fk, format=None):
    """
    Удаляет событие из заявки (в М-М)
    """
    user = check_authorize(request)
    if not (user and user.Role == 'User'):
        return Response({'error': 'Необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Получаем заявку по идентификатору
    reservation = get_object_or_404(Reservations, Reserve_id=fk)

    # Проверяем, что заявка принадлежит текущему пользователю
    if reservation.Client_id != user:
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

    # Пытаемся получить связь события и заявки
    event_reservation = get_object_or_404(Event_Reservation, Event_id=pk, Reserve_id=fk)

    # Удаляем связь
    event_reservation.delete()

    # Проверяем, остались ли другие связи для этой заявки
    remaining_event_reservations = Event_Reservation.objects.filter(Reserve_id=fk)
    if not remaining_event_reservations:
        reservation.Status = 'D'
        reservation.save()
        return Response({'message': 'Заявка удалена'})
    
    return Response({'message': 'Событие успешно удалено из заявки'})

@swagger_auto_schema(
        method='PUT', 
        operation_summary="Обновляет информацию о данных заявки", 
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'Group_info': openapi.Schema(type=openapi.TYPE_STRING),
                'Group_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                'Date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            },
        ),
        responses={200: EventReservationSerializer(), 400: 'Bad Request'})
@api_view(['PUT'])
def put_event_reservation(request, pk, fk, format=None):
    """
    Обновляет информацию о данных заявки
    """
    user = check_authorize(request)
    if not (user and user.Role == 'User'):
        return Response({'error': 'Необходима авторизация'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Получаем объект Event_Reservation или возвращаем 404, если объект не найден
    event_reservation = get_object_or_404(Event_Reservation, Event_id=pk, Reserve_id=fk)

    # Проверяем, что заявка принадлежит текущему пользователю
    if event_reservation.Reserve_id.Client_id != user:
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

    # Обновляем информацию о данных заявки
    serializer = EventReservationSerializer(event_reservation, data=request.data, partial=True) 

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



