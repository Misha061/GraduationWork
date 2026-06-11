import os
from .forms import RegisterUserForm, LoginForm, EcoArticleForm, UserAccountUpdateForm, ForecastForm
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from .Air_forecast_analisys_module.model_trainer import train_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import EcoArticle, UserProfile, Forecast
from .models import SystemState, ModelTrainingLog
from .utils import get_city_wide_ai_forecast, get_location_name_by_coords
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from .models import CityArea, AirSensorData
from django.contrib.auth.models import User
from django.views.generic import ListView
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from django.shortcuts import render
from django.http import JsonResponse
import shutil
import threading

AREA_NAMES = {

    (50.4501, 30.5234): "Центр (Київ)",
    (50.5186, 30.6019): "Троєщина (Київ)",
    (50.5085, 30.4986): "Оболонь (Київ)",
    (50.3956, 30.6133): "Осокорки (Київ)",
    (50.4287, 30.4727): "Солом'янка (Київ)",


    (46.4825, 30.7233): "Центр (Одеса)",
    (46.3986, 30.7183): "Таїрове (Одеса)",
    (46.5772, 30.7891): "Пересип (Одеса)",
    (46.4357, 30.7126): "Черемушки (Одеса)",
    (46.4173, 30.7495): "Фонтан (Одеса)",


    (49.8397, 24.0297): "Центр (Львів)",
    (49.7946, 24.0624): "Сихів (Львів)",
    (49.8406, 23.9611): "Левандівка (Львів)",
    (49.8659, 23.9317): "Рясне (Львів)",
    (49.8385, 24.0626): "Личаків (Львів)",


    (49.2331, 28.4682): "Центр (Вінниця)",
    (49.2238, 28.4116): "Вишенька (Вінниця)",
    (49.2458, 28.4907): "Замостя (Вінниця)",
    (49.2241, 28.4891): "Старе Місто (Вінниця)",
    (49.2559, 28.5204): "Тяжилів (Вінниця)",


    (48.9226, 24.7111): "Центр (Івано-Франківськ)",
    (48.9419, 24.6853): "Пасічна (Івано-Франківськ)",
    (48.9377, 24.7431): "Каскад (Івано-Франківськ)",
    (48.9103, 24.6957): "БАМ (Івано-Франківськ)",
    (48.9248, 24.7397): "Майзлі (Івано-Франківськ)"
}

def login_view(request):
    if request.method == "GET":
        form = LoginForm()
        return render(request, 'login.html', {"form": form})

    elif request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email_input = form.cleaned_data['email']
            password_input = form.cleaned_data['password']
            try:
                user_obj = User.objects.get(email=email_input)

                username = user_obj.username
            except User.DoesNotExist:

                username = None

            user = authenticate(request, username=username, password=password_input)

            if user is not None:
                login(request, user)

                display_name = user.first_name if user.first_name else email_input
                messages.success(request, f"Вітаємо, {display_name}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Неправильний email або пароль")

        return render(request, 'login.html', {"form": form})


def register_view(request):
    if request.method == "GET":
        form = RegisterUserForm()
        return render(request, 'register.html', {"form": form})
    elif request.method == "POST":
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(chelovek=user)
            login(request, user)
            messages.success(request, "Реєстрація успішна!")
            return redirect('dashboard')
        return render(request, 'register.html', {"form": form})


def logout_view(request):
    logout(request)
    messages.success(request, "Ви успішно вийшли із системи!")
    return redirect('login')

class MainDashboardView(ListView):
    model = CityArea
    template_name = 'dashboard.html'
    context_object_name = 'goroda'

    def get_context_data(self, **kwargs):
        print(f"DEBUG: Loading Dashboard for user: {self.request.user}")
        context = super().get_context_data(**kwargs)
        context['user_city'] = None
        if self.request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(chelovek=self.request.user)
                context['user_city'] = profile.izbranniy_gorod
                print(f"DEBUG: Found favorite city: {profile.izbranniy_gorod}")
            except UserProfile.DoesNotExist:
                print("DEBUG: User profile not found")
        return context

    @staticmethod
    def get_air_status_api(request, city_id):
        requested_hour = request.GET.get('hour', 'now')
        print(f"\n--- [START API DEBUG] ---")
        print(f"Запит для міста ID: {city_id}, Година: {requested_hour}")

        base_qs = AirSensorData.objects.filter(city_id=city_id)


        latest_records = base_qs.order_by('-vremya')[:5]
        if requested_hour != 'now':
            hour_qs = base_qs.filter(vremya__hour=int(requested_hour)).order_by('-vremya')[:5]
            if hour_qs.exists():
                latest_records = hour_qs
            else:
                print(f"За годину {requested_hour} даних немає")

        locations_data = []
        t_pm25, t_pm10, count = 0, 0, 0

        for record in latest_records:
            try:
                l_lat = float(str(record.lat).replace(',', '.'))
                l_lon = float(str(record.lon).replace(',', '.'))
                point_key = (round(l_lat, 4), round(l_lon, 4))
                location_name = AREA_NAMES.get(point_key, f"Точка {record.id}")

                locations_data.append({
                    'lat': l_lat,
                    'lon': l_lon,
                    'pm25': round(record.pm25_val, 2),
                    'pm10': round(record.pm10_val, 2),
                    'location_name': location_name
                })
                t_pm25 += record.pm25_val
                t_pm10 += record.pm10_val
                count += 1
            except Exception as e:
                print(f"Помилка запису: {e}")

        current_pm25 = round(t_pm25 / count, 2) if count > 0 else 0
        current_pm10 = round(t_pm10 / count, 2) if count > 0 else 0


        history_list = []
        try:

            now_local = timezone.localtime(timezone.now())
            seven_days_ago = now_local - timedelta(days=7)

            h_qs = base_qs.filter(vremya__gte=seven_days_ago).order_by('vremya')

            if h_qs.exists():
                buckets = defaultdict(list)
                for r in h_qs:

                    local_time = timezone.localtime(r.vremya)


                    b_hour = (local_time.hour // 3) * 3
                    b_time = local_time.replace(hour=b_hour, minute=0, second=0, microsecond=0)
                    buckets[b_time].append(r)

                for b_time in sorted(buckets.keys()):
                    recs = buckets[b_time]
                    history_list.append({

                        'time': b_time.strftime("%d.%m %H:00"),
                        'pm25': round(sum(i.pm25_val for i in recs) / len(recs), 2),
                        'pm10': round(sum(i.pm10_val for i in recs) / len(recs), 2)
                    })
        except Exception as e:
            print(f"Помилка історії: {e}")

        return JsonResponse({
            'current_avg_pm25': current_pm25,
            'current_avg_pm10': current_pm10,
            'locations': locations_data,
            'history_list': history_list,
            'forecast_1h': "Обробка нейромережею..."
        })

class ArticleListView(ListView):
    model = EcoArticle
    form_class = EcoArticleForm
    template_name = 'articles.html'
    context_object_name = 'articles'

    def get_queryset(self):
        return EcoArticle.objects.all().order_by('-data_pub')

class AccountView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    form_class = UserAccountUpdateForm
    template_name = 'account.html'
    success_url = reverse_lazy('account')


    def get_object(self, queryset=None):
        return self.request.user


    def test_func(self):
        profile_user = self.get_object()
        return profile_user == self.request.user


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)


        user_prof, created = UserProfile.objects.get_or_create(chelovek=self.request.user)
        context['profile'] = user_prof
        context['goroda'] = CityArea.objects.all()

        if user_prof.izbranniy_gorod:
            context['history_data'] = AirSensorData.objects.filter(
                city=user_prof.izbranniy_gorod
            ).order_by('-vremya')[:10]
        else:
            context['history_data'] = None

        return context

    def form_valid(self, form):
        user = form.save(commit=False)

        new_password = form.cleaned_data.get('password')
        new_email = form.cleaned_data.get('email')

        if new_email:
            user.email = new_email


        if new_password:
            user.set_password(new_password)

        user.save()

        if new_password or new_email:
            update_session_auth_hash(self.request, user)

        user_prof, created = UserProfile.objects.get_or_create(chelovek=self.request.user)

        gorod_id = self.request.POST.get('gorod_select')
        if gorod_id and gorod_id != 'none':
            user_prof.izbranniy_gorod_id = gorod_id
        else:
            user_prof.izbranniy_gorod = None

        new_interval = self.request.POST.get('interval')
        if new_interval:
            user_prof.update_interval = new_interval

        user_prof.send_notifs = 'notifs' in self.request.POST
        user_prof.save()

        from django.contrib import messages
        messages.success(self.request, "Профіль успішно оновлено!")
        return redirect(self.get_success_url())

    def test_func(self):
        profile_user = self.get_object()
        return profile_user == self.request.user

class ForecastAnalysisView(TemplateView):
    template_name = 'forecast_analysis.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        state, _ = SystemState.objects.get_or_create(id=1)

        if state.is_training:
            context['maintenance_mode'] = True
            return context
        city_id = self.request.GET.get('city_id')

        context['cities'] = CityArea.objects.all()

        if city_id:
            try:
                city = CityArea.objects.get(id=city_id)
                now = timezone.now()

                existing_forecasts = Forecast.objects.filter(
                    city=city,
                    created_at__year=now.year,
                    created_at__month=now.month,
                    created_at__day=now.day,
                    created_at__hour=now.hour
                )

                if not existing_forecasts.exists():
                    Forecast.objects.filter(city=city).delete()

                    ai_results = get_city_wide_ai_forecast(city_id)

                    new_forecasts = []
                    for res in ai_results:
                        for h in [1, 3, 24]:
                            h_key = f'{h}h'

                            new_forecasts.append(Forecast(
                                city=city,
                                location_name=res['location_name'],
                                lat=res['lat'],
                                lon=res['lon'],
                                predicted_pm25=res['pm25'][h_key],
                                predicted_pm10=res['pm10'][h_key],
                                prediction_hours=h
                            ))

                    Forecast.objects.bulk_create(new_forecasts)
                    existing_forecasts = Forecast.objects.filter(city=city).order_by('prediction_hours')

                context['forecast_data'] = existing_forecasts
                context['selected_city'] = city

            except CityArea.DoesNotExist:
                pass

        return context

def proverka_i_otpravka_uvedomleniy(sensor_zapis):
    NORMA_PM25_WHO = 25.0
    now = timezone.now()

    if sensor_zapis.pm25_val > NORMA_PM25_WHO:
        rayon = get_location_name_by_coords(sensor_zapis.lat, sensor_zapis.lon)
        zainteresovannie_ludi = UserProfile.objects.filter(
            izbranniy_gorod=sensor_zapis.city,
            send_notifs=True
        )

        people_for_sharing = []

        for prof in zainteresovannie_ludi:
            if not prof.last_notif_sent or now >= prof.last_notif_sent + timedelta(hours=prof.update_interval):
                people_for_sharing .append(prof)

        if people_for_sharing :
            t = threading.Thread(
                target=send_bulk_emails,
                args=(people_for_sharing , sensor_zapis, rayon)
            )
            t.start()


def send_bulk_emails(users, data, rayon):
    for prof in users:
        try:
            user_email = prof.chelovek.email
            if user_email:
                send_mail(
                    subject=f'⚠️ Увага: Забруднення у районі {rayon}',
                    message=(
                        f"Рівень PM2.5 у місті {data.city.name} ({rayon}) перевищив норму!\n"
                        f"Поточне значення: {data.pm25_val} µg/m³.\n\n"
                        f"Ми сповістимо вас знову не раніше ніж через {prof.update_interval} год."
                    ),
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user_email],
                    fail_silently=True,
                )
                prof.last_notif_sent = timezone.now()
                prof.save()
        except Exception as e:
            print(f"Помилка відправки: {e}")

def is_ai_admin(user):

    if not user.is_authenticated:
        return False
    try:
        return user.userprofile.user_admin
    except ObjectDoesNotExist:
        return False

@user_passes_test(is_ai_admin, login_url='/login/')
def ai_admin_dashboard(request):
    state, _ = SystemState.objects.get_or_create(id=1)
    logs = ModelTrainingLog.objects.order_by('-timestamp')[:20]

    comparison_list = []
    recent_forecasts = Forecast.objects.filter(prediction_hours=1).order_by('-created_at')[:5]

    for f in recent_forecasts:

        real = AirSensorData.objects.filter(
            lat=f.lat, lon=f.lon,
            vremya__gt=f.created_at
        ).order_by('vremya').first()

        if real:
            comparison_list.append({
                'location': f.location_name,
                'time': f.created_at,
                'pred_pm25': f.predicted_pm25,
                'real_pm25': real.pm25_val,
                'diff': round(abs(f.predicted_pm25 - real.pm25_val), 2)
            })

    return render(request, 'ai_admin.html', {
        'state': state,
        'logs': logs,
        'comparisons': comparison_list,
        'backup_exists': os.path.exists('air_forecast_model_backup.h5')
    })
@user_passes_test(is_ai_admin, login_url='/login/')
def trigger_retrain(request):
    state, _ = SystemState.objects.get_or_create(id=1)
    if state.is_training:
        return redirect('ai_admin_dashboard')

    def background_train():

        if os.path.exists('Air_forecast_analisys_module/air_forecast_model.h5'):
            shutil.copy('Air_forecast_analisys_module/air_forecast_model.h5', 'air_forecast_model_backup.h5')

        try:
            train_model(model_name="5")
        finally:
            state.is_training = False
            state.save()

    state.is_training = True
    state.progress = 0
    state.save()

    thread = threading.Thread(target=background_train)
    thread.start()

    return redirect('ai_admin_dashboard')
@user_passes_test(is_ai_admin, login_url='/login/')
def rollback_model(request):
    if os.path.exists('air_forecast_model_backup.h5'):
        shutil.copy('air_forecast_model_backup.h5', 'Air_forecast_analisys_module/air_forecast_model.h5')
    return redirect('ai_admin_dashboard')
@user_passes_test(is_ai_admin, login_url='/login/')
def api_training_status(request):
    state = SystemState.objects.get(id=1)
    return JsonResponse({
        'is_training': state.is_training,
        'progress': state.progress,
        'epoch': state.current_epoch,
        'total': state.total_epochs
    })