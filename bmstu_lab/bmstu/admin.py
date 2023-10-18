from django.contrib import admin
from bmstu.models import Users, Reservations, Events, Event_Reservation

class EventsAdmin(admin.ModelAdmin):
    list_display = ('Event_id', 'Name', 'Start_date', 'End_date', 'Status')  # Определите, какие поля отображать в списке
    list_filter = ('Status',)  # Добавьте фильтры для полей
    search_fields = ('Name',)  # Добавьте поля для поиска

# class UsersAdmin(admin.ModelAdmin):
#     list_display = ('User_id', 'Role', 'Mail', 'Password', 'Nickname')  # Определите, какие поля отображать в списке
#     list_filter = ('Status',)  # Добавьте фильтры для полей
#     search_fields = ('Name',)  # Добавьте поля для поиска
# class UsersAdmin(admin.ModelAdmin):

# class UsersAdmin(admin.ModelAdmin):


# Регистрируем модель Events с настройками EventsAdmin
admin.site.register(Users)
admin.site.register(Reservations)
admin.site.register(Events)
admin.site.register(Event_Reservation)
