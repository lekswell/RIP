from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from bmstu.models import Events
from django.db.models import Q
from django.db import connection
import psycopg2

# Мероприятия музея МГТУ. Услуги - виды проводимых в музее мероприятий, 
# заявки - заявки для групп на данные мероприятия

def GetEvents(request):
    # Получаем ключевое слово из запроса GET
    keyword = request.GET.get('query', '')

    # Фильтруем мероприятия по ключевому слову и статусу "Удалено"
    filtered_events = Events.objects.filter(
        ~Q(Status='D'),  # Исключаем события со статусом "Удалено"
        Q(Name__icontains=keyword) | Q(Start_date__icontains=keyword) | Q(End_date__icontains=keyword)
    )  

    return render(request, 'events.html', {'data': {
        'events': filtered_events,  
        'keyword': keyword,
    }})

def GetEvent(request, eventId):
    # Получите событие по Event_id
    event = get_object_or_404(Events, Event_id=eventId)

    return render(request, 'event.html', {'event': event})



def change_event_status(event_id, new_status):
    try:
        # Создание курсора
        cursor = connection.cursor()

        # Изменение статуса события в базе данных
        cursor.execute(
                'UPDATE bmstu_events SET "Status" = %s WHERE "Event_id" = %s',
                [new_status, event_id]
            )
        connection.commit()

    except Exception as e:
        # Обработка ошибок, если не удалось выполнить запрос
        print(f"Ошибка при обновлении статуса события: {str(e)}")
        connection.rollback()
    finally:
        # Закрытие курсора и соединения
        cursor.close()
        connection.close()

def DeleteEvent(request, eventId):
    # Получаем событие по eventId
    event = get_object_or_404(Events, Event_id=eventId)

    # Проверяем, что метод запроса - POST
    if request.method == 'POST':
        # Изменяем статус на "Удалено" в базе данных
        change_event_status(event.Event_id, 'D')

    # После изменения статуса события выполняем редирект на страницу с событиями
    return redirect('events_url')

