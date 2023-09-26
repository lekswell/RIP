from django.http import HttpResponse
from django.shortcuts import render
from bmstu.models import Events
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

# Мероприятия музея МГТУ. Услуги - виды проводимых в музее мероприятий, 
# заявки - заявки для групп на данные мероприятия

def GetEvents(request):
    # Получаем ключевое слово из запроса GET
    keyword = request.GET.get('query', '')

    # Фильтруем мероприятия по ключевому слову или по дате
    filtered_events = Events.objects.filter(
        Q(Name__icontains=keyword) | Q(Start_date__icontains=keyword) | Q(End_date__icontains=keyword)
    )

    return render(request, 'events.html', {'data': {
        'current_date': date.today(),
        'events': filtered_events.values('Event_id', 'Name', 'Start_date', 'End_date', 'Image', 'Status'),  
        # Передаем отфильтрованные мероприятия, исключая поле Info
        'keyword': keyword,  # Передаем ключевое слово для отображения на странице
    }})


def GetEvent(request, eventId):
    
    # Event = None
    event = get_object_or_404(Events, Event_id=eventId)
    # for event in events:
    #     if event['id'] == eventId:
    #         Event = event 
    
    return render(request, 'event.html', {'data': {
        'title': event.Name,    # Обратитесь к полю Name модели Events
        'image': event.Image,   # Обратитесь к полю Image модели Events
        'dates': f'{event.Start_date} - {event.End_date}',  # Обратитесь к полям Start_date и End_date
        'info': event.Info,     # Обратитесь к полю Info модели Events
    }})
