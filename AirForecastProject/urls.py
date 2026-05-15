from django.urls import path

from . import views
from .views import MainDashboardView, ArticleListView, AccountView, login_view, logout_view, register_view, \
    ForecastAnalysisView

urlpatterns = [

    path("", MainDashboardView.as_view(), name="dashboard"),
    path("articles/", ArticleListView.as_view(), name="articles"),
    path("account/", AccountView.as_view(), name="account"),

    path('login/', login_view, name="login"),
    path('register/', register_view, name="register"),
    path("logout/", logout_view, name='logout'),
    path('analysis/', ForecastAnalysisView.as_view(), name='forecast_analysis'),
    path('api/get_air_status/<int:city_id>/', views.MainDashboardView.get_air_status_api, name='get_air_status_api'),
    path('ai-admin/', views.ai_admin_dashboard, name='ai_admin_dashboard'),
    path('ai-admin/retrain/', views.trigger_retrain, name='trigger_retrain'),
    path('ai-admin/rollback/', views.rollback_model, name='rollback_model'),
    path('api/training-status/', views.api_training_status, name='api_training_status'),
]