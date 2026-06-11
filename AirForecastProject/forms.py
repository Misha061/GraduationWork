from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from .models import CityArea, AirSensorData, EcoArticle, Forecast


class RegisterUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Ваш Email',
        widget=forms.EmailInput(attrs={'placeholder': 'example@mail.com', 'style': 'width: 100%; padding: 10px; margin-bottom: 15px;'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Введіть пароль', 'style': 'width: 100%; padding: 10px; margin-bottom: 15px;'})
    )

class CityAreaForm(forms.ModelForm):
    class Meta:
        model = CityArea
        fields = ['name']

class AirSensorDataForm(forms.ModelForm):
    class Meta:
        model = AirSensorData
        fields = ['city', 'pm25_val', 'pm10_val', 'lat', 'lon']

class EcoArticleForm(forms.ModelForm):
    class Meta:
        model = EcoArticle
        fields = ['zagolovok', 'soderzhanie', 'url_article']

class UserAccountUpdateForm(UserChangeForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Залиште пустим, щоб не змінювати'})
    )
    class Meta:
        model = User
        fields = ['email']

class ForecastForm(forms.Form):
    model = Forecast
    fields = ['pm25_val', 'pm10_val', 'prediction_hours']
