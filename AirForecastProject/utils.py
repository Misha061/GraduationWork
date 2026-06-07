from concurrent.futures import ThreadPoolExecutor
import time
from .forms import AirSensorDataForm
import requests
from .models import CityArea
import os
import joblib
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from .models import AirSensorData

API_KEY = "8f68d6d051d505bcaf5da7f85b7858f0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'Air_forecast_analisys_module', 'air_forecast_model.h5')
SCALER_PATH = os.path.join(BASE_DIR, 'Air_forecast_analisys_module', 'air_scaler.gz')
_AI_MODEL = None
_AI_SCALER = None


VIRTUAL_SENSORS = {

    "Kyiv_Center": (50.4501, 30.5234),
    "Kyiv_Troieshchyna": (50.5186, 30.6019),
    "Kyiv_Obolon": (50.5085, 30.4986),
    "Kyiv_Osokorky": (50.3956, 30.6133),
    "Kyiv_Solomyanka": (50.4287, 30.4727),


    "Odesa_Center": (46.4825, 30.7233),
    "Odesa_Tairove": (46.3986, 30.7183),
    "Odesa_Peresyp": (46.5772, 30.7891),
    "Odesa_Cheremushky": (46.4357, 30.7126),
    "Odesa_Fontan": (46.4173, 30.7495),


    "Lviv_Center": (49.8397, 24.0297),
    "Lviv_Sykhiv": (49.7946, 24.0624),
    "Lviv_Levandivka": (49.8406, 23.9611),
    "Lviv_Riasne": (49.8659, 23.9317),
    "Lviv_Lychakiv": (49.8385, 24.0626),


    "Vinnytsia_Center": (49.2331, 28.4682),
    "Vinnytsia_Vyshenka": (49.2238, 28.4116),
    "Vinnytsia_Zamostia": (49.2458, 28.4907),
    "Vinnytsia_Stare_Misto": (49.2241, 28.4891),
    "Vinnytsia_Tyazhyliv": (49.2559, 28.5204),


    "Frankivsk_Center": (48.9226, 24.7111),
    "Frankivsk_Pasichna": (48.9419, 24.6853),
    "Frankivsk_Kaskad": (48.9377, 24.7431),
    "Frankivsk_BAM": (48.9103, 24.6957),
    "Frankivsk_Maizli": (48.9248, 24.7397)
}

CITY_DB_MAPPING = {
    "Kyiv": "Київ",
    "Odesa": "Одеса",
    "Lviv": "Львів",
    "Vinnytsia": "Вінниця",
    "Frankivsk": "Івано-Франківськ"
}

def save_new_air_data(city_id, pm25, pm10, lat, lon):
    data = {
        'city': city_id,
        'pm25_val': pm25,
        'pm10_val': pm10,
        'lat': lat,
        'lon': lon
    }
    form = AirSensorDataForm(data)
    if form.is_valid():
        form.save()
        return True
    else:
        print(f"Помилка збереження для міста ID {city_id}:", form.errors)
        return False

def fetch_and_save_current_data():

    db_cities = {city.name: city for city in CityArea.objects.all()}

    if not db_cities:
        print("У базі немає жодного міста (CityArea). Додайте міста через панель адміністратора.")
        return

    for sensor_name, (lat, lon) in VIRTUAL_SENSORS.items():

        city_prefix = sensor_name.split('_')[0]
        db_city_name = CITY_DB_MAPPING.get(city_prefix)

        if db_city_name and db_city_name in db_cities:
            city_obj = db_cities[db_city_name]
            url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"

            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    pm25 = data['list'][0]['components']['pm2_5']
                    pm10 = data['list'][0]['components']['pm10']


                    save_new_air_data(city_obj.id, pm25, pm10, lat, lon)
                    print(f"[OK] {sensor_name} -> збережено (PM2.5: {pm25}, lat: {lat}, lon: {lon})")
                else:
                    print(f"[Помилка API] Код {response.status_code} для {sensor_name}")
            except Exception as e:
                print(f"[Помилка] Не вдалося оновити {sensor_name}: {e}")
        else:
            print(f"[Увага] Локацію {sensor_name} пропущено: місто '{db_city_name}' не знайдено в базі даних.")
            time.sleep(0.5)

def load_ai_assets():
    global _AI_MODEL, _AI_SCALER

    if _AI_MODEL is None:

        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            _AI_MODEL = load_model(MODEL_PATH, compile=False)
            _AI_SCALER = joblib.load(SCALER_PATH)
    return _AI_MODEL, _AI_SCALER


def get_prediction_for_location(location_coords, city_id, model, scaler):
    lat, lon = location_coords

    qs = AirSensorData.objects.filter(
        city_id=city_id,
        lat=lat,
        lon=lon
    ).order_by('-vremya')[:24]

    if qs.count() < 24:
        return None

    df = pd.DataFrame(list(qs.values('pm25_val', 'pm10_val', 'vremya', 'lat', 'lon')))
    df = df.sort_values('vremya')


    df['h_sin'] = np.sin(2 * np.pi * df['vremya'].dt.hour / 24)
    df['h_cos'] = np.cos(2 * np.pi * df['vremya'].dt.hour / 24)
    df['s_sin'] = np.sin(2 * np.pi * df['vremya'].dt.dayofyear / 365)
    df['s_cos'] = np.cos(2 * np.pi * df['vremya'].dt.dayofyear / 365)

    features = ['pm25_val', 'pm10_val', 'lat', 'lon', 'h_sin', 'h_cos', 's_sin', 's_cos']

    input_scaled = scaler.transform(df[features])
    input_reshaped = np.expand_dims(input_scaled, axis=0)

    raw_pred = model.predict(input_reshaped, verbose=0)[0]

    mi25, ma25 = scaler.data_min_[0], scaler.data_max_[0]
    mi10, ma10 = scaler.data_min_[1], scaler.data_max_[1]

    def res(v, mi, ma): return round(max(0.1, v * (ma - mi) + mi), 2)

    return {
        'lat': lat, 'lon': lon,
        'location_name': get_location_name_by_coords(lat, lon),  # Назва району
        'pm25': {
            '1h': res(raw_pred[0], mi25, ma25),
            '3h': res(raw_pred[1], mi25, ma25),
            '24h': res(raw_pred[2], mi25, ma25)
        },
        'pm10': {
            '1h': res(raw_pred[3], mi10, ma10),
            '3h': res(raw_pred[4], mi10, ma10),
            '24h': res(raw_pred[5], mi10, ma10)
        }
    }

def get_city_wide_ai_forecast(city_id):
    model, scaler = load_ai_assets()

    if not model: return []

    locs = AirSensorData.objects.filter(city_id=city_id).values('lat', 'lon').distinct()
    coords = [(float(l['lat']), float(l['lon'])) for l in locs]

    with ThreadPoolExecutor(max_workers=5) as ex:

        futs = [ex.submit(get_prediction_for_location, c, city_id, model, scaler) for c in coords]
        return [f.result() for f in futs if f.result()]

def get_location_name_by_coords(lat, lon):
    for name, coords in VIRTUAL_SENSORS.items():

        if abs(coords[0] - lat) < 0.001 and abs(coords[1] - lon) < 0.001:

            full_name = name.split('_')[-1]
            translations = {
                "Center": "Центр", "Troieshchyna": "Троєщина", "Obolon": "Оболонь",
                "Osokorky": "Осокорки", "Solomyanka": "Солом'янка", "Tairove": "Таїрове",
                "Peresyp": "Пересип", "Cheremushky": "Черемушки", "Fontan": "Фонтан",
                "Sykhiv": "Сихів", "Levandivka": "Левандівка", "Riasne": "Рясне",
                "Lychakiv": "Личаків", "Vyshenka": "Вишенька", "Zamostia": "Замостя",
                "Pasichna": "Пасічна", "Kaskad": "Каскад", "Maizli": "Майзлі"
            }
            return translations.get(full_name, full_name)
    return "Інший район"