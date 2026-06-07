import os
import sys
import django

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject.settings')

try:
    django.setup()
except Exception as e:
    print(f"Помилка ініціалізації: {e}")
    sys.exit(1)

from AirForecastProject.utils import fetch_historical_air_data_utc

if __name__ == "__main__":
    print("Парсер запущено (налаштування з DjangoProject)...")
    fetch_historical_air_data_utc()