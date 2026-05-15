from django.contrib import admin
from .models import CityArea, AirSensorData, EcoArticle, UserProfile

@admin.register(EcoArticle)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('zagolovok', 'data_pub')
    search_fields = ('zagolovok', 'soderzhanie')

@admin.register(CityArea)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'lat', 'lon')

admin.site.register(AirSensorData)
admin.site.register(UserProfile)