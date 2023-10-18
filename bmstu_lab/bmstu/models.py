from django.db import models

class Users(models.Model):
    User_id = models.AutoField(primary_key=True)
    Role = models.CharField(max_length=20)
    Mail = models.CharField(max_length=30)
    Password = models.CharField(max_length=30)
    Nickname = models.CharField(max_length=20)
    class Meta:
        managed = False
        db_table = 'bmstu_users'

class Reservations(models.Model):
    STATUS_CHOICE = (
        ('M', 'Made'),
        ('iP', 'In Progress'),
        ('C', 'Completed'),
        ('Ca', 'Canceled'),
        ('D', 'Deleted'),
    )
    Reserve_id = models.AutoField(primary_key=True)
    Moderator_id = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='moderator_reservations')
    Client_id = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='client_reservations')
    Creation_date = models.DateField()
    Formation_date = models.DateField()
    Completion_date = models.DateField()
    Status = models.CharField(max_length=2, choices=STATUS_CHOICE)
    class Meta:
        managed = False
        db_table = 'bmstu_reservations'

class Events(models.Model):
    STATUS_CHOICE = (
        ('A', 'Доступно'),
        ('C', 'Завершено'),
        ('S', 'Скоро'),
        ('D', 'Удалено'),
    )
    Event_id = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=30)
    Start_date = models.DateField()
    End_date = models.DateField()
    Image = models.CharField(max_length=255)
    Status = models.CharField(max_length=20,choices=STATUS_CHOICE)
    Info = models.CharField(max_length=255)
    class Meta:
        managed = False
        db_table = 'bmstu_events'

class Event_Reservation(models.Model):
    Event_id = models.ForeignKey(Events, on_delete=models.CASCADE)
    Reserve_id = models.ForeignKey(Reservations, on_delete=models.CASCADE)
    Group_info = models.CharField(max_length=20)
    Group_size = models.IntegerField()
    Date = models.DateField()
    class Meta:
        managed = False
        db_table = 'bmstu_event_reservation'

