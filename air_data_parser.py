import os
import sys
import django
import time

# 1. Додаємо шлях до кореня проєкту
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 2. Вказуємо на папку DjangoProject, бо settings.py саме там!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject.settings')

try:
    django.setup()
except Exception as e:
    print(f"Помилка ініціалізації: {e}")
    sys.exit(1)

# 3. Імпортуємо функцію з додатка AirForecastProject
from AirForecastProject.utils import fetch_and_save_current_data

if __name__ == "__main__":
    print("Парсер запущено (налаштування з DjangoProject)...")
    while True:
        try:
            print("--- Перевірка даних ---")
            fetch_and_save_current_data()
            time.sleep(60)
        except KeyboardInterrupt:
            break