from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import pytz

def get_kyiv_time():
    return timezone.now().astimezone(pytz.timezone('Europe/Kyiv'))

class CityArea(models.Model):
    name = models.CharField(max_length=100)
    lat = models.FloatField()
    lon = models.FloatField()

    def __str__(self):
        return self.name

class AirSensorData(models.Model):
    city = models.ForeignKey(CityArea, on_delete=models.CASCADE)
    pm25_val = models.FloatField()
    pm10_val = models.FloatField()
    vremya = models.DateTimeField(default=get_kyiv_time)
    lat = models.FloatField()
    lon = models.FloatField()

    class Meta:
        indexes = [
            models.Index(fields=['vremya'], name='time_idx'),
            models.Index(fields=['city', 'vremya'], name='city_time_idx'),
        ]

class UserProfile(models.Model):
    chelovek = models.OneToOneField(User, on_delete=models.CASCADE)
    izbranniy_gorod = models.ForeignKey(CityArea, on_delete=models.SET_NULL, null=True)
    update_interval = models.FloatField(default=1.0)
    send_notifs = models.BooleanField(default=False)
    user_admin = models.BooleanField(default=False)
    last_notif_sent = models.DateTimeField(null=True, blank=True)
    def get_absolute_url(self):
        return reverse('dashboard', kwargs={'pk': self.pk})

class EcoArticle(models.Model):
    zagolovok = models.CharField(max_length=255)
    soderzhanie = models.TextField()
    data_pub = models.DateTimeField(auto_now_add=True)
    url_article = models.URLField()
    def get_absolute_url(self):
        return reverse('dashboard', kwargs={'pk': self.pk})

class Forecast(models.Model):
    city = models.ForeignKey(CityArea, on_delete=models.CASCADE, related_name='city_forecasts')
    location_name = models.CharField(max_length=100, default="Невідома локація")
    lat = models.FloatField()
    lon = models.FloatField()
    predicted_pm25 = models.FloatField()
    predicted_pm10 = models.FloatField()
    prediction_hours = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.location_name} - {self.prediction_hours}h'

    def __str__(self):
        return f'{self.city}'

    def get_absolute_url(self):
        return reverse('dashboard', kwargs={'pk': self.pk})

class ModelTrainingLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    loss = models.FloatField()
    mae = models.FloatField()
    epochs = models.IntegerField()
    model_version = models.CharField(max_length=50)
    is_active = models.BooleanField(default=False)

class SystemState(models.Model):
    is_training = models.BooleanField(default=False)
    current_epoch = models.IntegerField(default=0)
    total_epochs = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)
    last_update = models.DateTimeField(auto_now=True)