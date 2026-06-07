from unittest.mock import MagicMock
from AirForecastProject.models import UserProfile
from AirForecastProject.views import proverka_i_otpravka_uvedomleniy

test_profile = UserProfile.objects.filter(send_notifs=True, chelovek__is_active=True).first()
test_city = test_profile.izbranniy_gorod

print("Email:", test_profile.chelovek.email)
print("City:", test_city.name)

test_profile.last_notif_sent = None
test_profile.save()

mock_sensor_data = MagicMock()
mock_sensor_data.pm25_val = 45.0
mock_sensor_data.lat = test_city.lat
mock_sensor_data.lon = test_city.lon
mock_sensor_data.city = test_city

print("Zapusk funkcii...")
proverka_i_otpravka_uvedomleniy(mock_sensor_data)
print("Pismo otpravleno na pochtu!")