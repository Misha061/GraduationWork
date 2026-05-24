import joblib, numpy as np
from tensorflow.keras.models import load_model
from django.utils import timezone


MODEL = load_model('air_forecast_model.h5')
SCALER = joblib.load('air_scaler.gz')


def get_forecast_from_ai(last_24_qs):

    df = pd.DataFrame(list(last_24_qs.values('pm25_val', 'pm10_val', 'vremya')))

    df['h_sin'] = np.sin(2 * np.pi * df['vremya'].dt.hour / 24)
    df['h_cos'] = np.cos(2 * np.pi * df['vremya'].dt.hour / 24)
    df['s_sin'] = np.sin(2 * np.pi * df['vremya'].dt.dayofyear / 365)
    df['s_cos'] = np.cos(2 * np.pi * df['vremya'].dt.dayofyear / 365)

    features = ['pm25_val', 'pm10_val', 'h_sin', 'h_cos', 's_sin', 's_cos']
    input_scaled = SCALER.transform(df[features])


    pred = MODEL.predict(np.expand_dims(input_scaled, axis=0))[0]



    mi = SCALER.data_min_[:2]
    ma = SCALER.data_max_[:2]


    res = []
    for i in range(6):
        m_idx = 0 if i < 3 else 1
        res.append(round(pred[i] * (ma[m_idx] - mi[m_idx]) + mi[m_idx], 2))

    return {
        'pm25': {'1h': res[0], '3h': res[1], '24h': res[2]},
        'pm10': {'1h': res[3], '3h': res[4], '24h': res[5]}
    }