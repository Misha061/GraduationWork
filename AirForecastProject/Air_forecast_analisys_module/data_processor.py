import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE_PATH = os.path.join(BASE_DIR, 'Air_forecast_analisys_module', 'processed_data.npy')
import os, django, numpy as np, pandas as pd, joblib
from sklearn.preprocessing import MinMaxScaler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject.settings')
django.setup()
from AirForecastProject.models import AirSensorData


def prepare_data():
    print("Крок 1: Завантаження та розширена інженерія ознак...")
    qs = AirSensorData.objects.all().order_by('vremya')
    df = pd.DataFrame(list(qs.values('vremya', 'pm25_val', 'pm10_val', 'lat', 'lon')))

    if df.empty: return

    for col in ['pm25_val', 'pm10_val']:
        limit = df[col].quantile(0.99)
        df.loc[df[col] > limit, col] = limit

    df['h_sin'] = np.sin(2 * np.pi * df['vremya'].dt.hour / 24)
    df['h_cos'] = np.cos(2 * np.pi * df['vremya'].dt.hour / 24)
    df['s_sin'] = np.sin(2 * np.pi * df['vremya'].dt.dayofyear / 365)
    df['s_cos'] = np.cos(2 * np.pi * df['vremya'].dt.dayofyear / 365)

    features = ['pm25_val', 'pm10_val', 'lat', 'lon', 'h_sin', 'h_cos', 's_sin', 's_cos']
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(df[features])

    joblib.dump(scaler, 'air_scaler.gz')
    np.save(DATA_FILE_PATH, scaled_data)
    print(f"Дані підготовлено. Кількість ознак: {len(features)}")


if __name__ == "__main__":
    prepare_data()