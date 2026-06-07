import django
import numpy as np
import tensorflow as tf
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE_PATH = os.path.join(BASE_DIR, 'Air_forecast_analisys_module', 'processed_data.npy')
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, BatchNormalization, LeakyReLU
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject.settings')
django.setup()


class DjangoProgressCallback(tf.keras.callbacks.Callback):
    def __init__(self, state_id, total_epochs):
        super(DjangoProgressCallback, self).__init__()
        self.state_id = state_id
        self.total_epochs = total_epochs

    def on_train_begin(self, logs=None):
        from AirForecastProject.models import SystemState
        state, _ = SystemState.objects.get_or_create(id=self.state_id)
        state.is_training = True
        state.current_epoch = 0
        state.total_epochs = self.total_epochs
        state.progress = 0
        state.save()

    def on_epoch_end(self, epoch, logs=None):
        from AirForecastProject.models import SystemState, ModelTrainingLog
        state = SystemState.objects.get(id=self.state_id)
        current_epoch = epoch + 1
        progress_percent = int((current_epoch / self.total_epochs) * 100)
        state.current_epoch = current_epoch
        state.progress = progress_percent
        state.save()
        if logs:
            ModelTrainingLog.objects.create(
                loss=round(logs.get('loss', 0), 5),
                mae=round(logs.get('mae', 0), 5),
                epochs=current_epoch,
                model_version=f"v_{timezone.now().strftime('%Y%m%d_%H%M')}",
                is_active=False
            )

    def on_train_end(self, logs=None):
        from AirForecastProject.models import SystemState
        state = SystemState.objects.get(id=self.state_id)
        state.is_training = False
        state.progress = 100
        state.save()
        print(f"\nНавчання завершено успішно. Модель збережена.")


def train_model(model_name="5"):
    print("Крок 2: Запуск глибокого навчання (5 шарів)...")
    try:
        data = np.load(DATA_FILE_PATH)
    except FileNotFoundError:
        print("Помилка: Файл processed_data.npy не знайдено!")
        return

    X, y = [], []
    lookback = 24
    if len(data) <= lookback + 24:
        return

    for i in range(lookback, len(data) - 24):
        X.append(data[i - lookback:i])
        y.append([
            data[i, 0], data[i + 2, 0], data[i + 23, 0],
            data[i, 1], data[i + 2, 1], data[i + 23, 1]
        ])

    X, y = np.array(X), np.array(y)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model = Sequential([
        Input(shape=(X.shape[1], X.shape[2])),
        LSTM(128, return_sequences=True),
        BatchNormalization(),
        LSTM(64),
        Dropout(0.3),
        Dense(64),
        LeakyReLU(alpha=0.1),
        Dense(32),
        BatchNormalization(),
        LeakyReLU(alpha=0.1),
        Dense(16, activation='relu'),
        Dense(6)
    ])

    epochs_count = 30
    progress_callback = DjangoProgressCallback(state_id=1, total_epochs=epochs_count)

    opt = tf.keras.optimizers.Adam(learning_rate=0.0005)
    model.compile(optimizer=opt, loss='mse', metrics=['mae'])

    model.fit(
        X_train, y_train,
        epochs=epochs_count,
        validation_data=(X_test, y_test),
        batch_size=32,
        callbacks=[progress_callback],
        verbose=1
    )

    model.save(f'air_forecast_model.h{model_name}')

    from AirForecastProject.models import ModelTrainingLog
    try:
        last_log = ModelTrainingLog.objects.latest('timestamp')
        last_log.is_active = True
        last_log.save()
    except:
        pass

    print("=== МОДЕЛЬ УСПІШНО ОНОВЛЕНО ===")


if __name__ == "__main__":
    train_model()