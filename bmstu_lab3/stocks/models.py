from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, username, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email=email)

class Users(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    is_staff = models.BooleanField(default=False, verbose_name="Является ли пользователь менеджером?")
    is_superuser = models.BooleanField(default=False, verbose_name="Является ли пользователь админом?")
    is_active = models.BooleanField(default=True)
    
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        managed = True
        db_table = 'bmstu_users'

class Reservations(models.Model):
    STATUS_CHOICE = (
        ('M', 'Черновик'),
        ('iP', 'В работе'),
        ('C', 'Завершена'),
        ('Ca', 'Отменена'),
        ('D', 'Удалена'),
    )
    Reserve_id = models.AutoField(primary_key=True)
    Moderator_id = models.ForeignKey(Users, null=True, blank=True, on_delete=models.CASCADE, related_name='moderator_reservations')
    Client_id = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='client_reservations')
    Creation_date = models.DateTimeField()
    Formation_date = models.DateTimeField(null=True)
    Completion_date = models.DateTimeField(null=True)
    Status = models.CharField(max_length=20, choices=STATUS_CHOICE)
    class Meta:
        managed = True
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
    Image = models.ImageField(upload_to='events/')  
    Status = models.CharField(max_length=20,choices=STATUS_CHOICE)
    Info = models.CharField(max_length=255)
    class Meta:
        managed = True
        db_table = 'bmstu_events'

class Event_Reservation(models.Model):
    Event_id = models.ForeignKey(Events, on_delete=models.CASCADE)
    Reserve_id = models.ForeignKey(Reservations, on_delete=models.CASCADE)
    Group_info = models.CharField(max_length=20)
    Group_size = models.IntegerField()
    Date = models.DateField()
    class Meta:
        managed = True
        db_table = 'bmstu_event_reservation'

