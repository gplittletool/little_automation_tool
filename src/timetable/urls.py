from django.urls import path
from timetable.views import index


app_name = 'timetable'

urlpatterns = [
    path('', index, name='index')
]