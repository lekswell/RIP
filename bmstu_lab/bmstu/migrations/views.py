from django.http import HttpResponse
from django.shortcuts import render
from datetime import date

# Мероприятия музея МГТУ. Услуги - виды проводимых в музее мероприятий, 
# заявки - заявки для групп на данные мероприятия

# def hello(request):
#     return render(request, 'index.html', { 'data' : {
#         'current_date': date.today(),
#         'list': ['python', 'django', 'html']
#     }})

# def GetOrders(request):
#     return render(request, 'orders.html', {'data' : {
#         'current_date': date.today(),
#         'orders': [
#             {'title': 'Книга с картинками', 'id': 1},
#             {'title': 'Бутылка с водой', 'id': 2},
#             {'title': 'Коврик для мышки', 'id': 3},
#         ]
#     }})

# def GetOrder(request, id):
#     return render(request, 'order.html', {'data' : {
#         'current_date': date.today(),
#         'id': id
#     }})

from datetime import datetime

def GetEvents(request):
    events = [
        {'title': 'В.И.Гриневецкий', 'id': 1, 'image': 'static/images/event1.jpg', 'dates': '10-15 сентября 2023'},
        {'title': 'Лыжная одиссея', 'id': 2, 'image': 'static/images/event2.jpg', 'dates': '15-20 сентября 2023'},
        {'title': 'В.П.Бармин', 'id': 3, 'image': 'static/images/event3.jpg', 'dates': '20-25 сентября 2023'},
        {'title': 'Воспитательный дом', 'id': 4, 'image': 'static/images/event4.jpg', 'dates': '25-30 сентября 2023'}
    ]
    
    # Получаем ключевое слово из запроса GET
    keyword = request.GET.get('query', '')

    # Фильтруем мероприятия по ключевому слову или по дате
    filtered_events = []

    for event in events:
        if keyword.lower() in event['title'].lower() or keyword.lower() in event['dates'].lower():
            filtered_events.append(event)

    return render(request, 'events.html', {'data': {
        'current_date': date.today(),
        'events': filtered_events,  # Передаем отфильтрованные мероприятия
        'keyword': keyword,  # Передаем ключевое слово для отображения на странице
    }})



def GetEvent(request, eventId):
    events = [
        {'title': 'В.И.Гриневецкий', 'id': 1, 'image': '/static/images/event1.jpg', 'dates': '10-15 сентября 2023'},
        {'title': 'Лыжная одиссея', 'id': 2, 'image': '/static/images/event2.jpg', 'dates': '15-20 сентября 2023'},
        {'title': 'В.П.Бармин', 'id': 3, 'image': '/static/images/event3.jpg', 'dates': '20-25 сентября 2023'},
        {'title': 'Воспитательный дом', 'id': 4, 'image': '/static/images/event4.jpg', 'dates': '25-30 сентября 2023'}
    ]
    
    Event = None
    
    for event in events:
        if event['id'] == eventId:
            Event = event 
            break
    if Event is None:
        return HttpResponse('Информация не найдена')
    print (Event)
    return render(request, 'event.html', {'data': {
    'title': Event['title'],  # Обратитесь к данным через ключ 'title'
    'image': Event['image'],  # Обратитесь к данным через ключ 'image'
    'dates': Event['dates'],  # Обратитесь к данным через ключ 'dates'
}})



def sendText(request):
    input_text = request.POST['text']
    ...