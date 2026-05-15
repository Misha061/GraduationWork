from celery import shared_task
from .models import AirSensorData, ForecastData, CityArea
from .ml_utils import prognoz_logic
from django.utils import timezone
import pandas as pd


@shared_task
def obschitat_prognozi():
    vse_goroda = CityArea.objects.all()

    for gorod in vse_goroda:
        # Беремо останні 100 записів для цього міста як вхід для LSTM
        poslednie_danni = AirSensorData.objects.filter(city=gorod).order_by('-vremya')[:100]

        if len(poslednie_danni) < 20:  # Мало даних для навчання
            continue

        # Формуємо DataFrame для обробки
        df = pd.DataFrame(list(poslednie_danni.values('pm25_val', 'pm10_val')))

        # Викликаємо модель для різних горизонтів (1, 2, 5, 12, 24 год)
        horizonti = [1, 2, 5, 12, 24]
        for h in horizonti:
            p25_pred = prognoz_logic(df, h)  # Повертає число

            # Зберігаємо результат
            ForecastData.objects.create(
                sensor_ref=poslednie_danni[0],
                horizon_hours=h,
                predicted_pm25=p25_pred,
                vremya_prognoza=timezone.now() + timezone.timedelta(hours=h)
            )