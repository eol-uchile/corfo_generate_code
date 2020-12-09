from django.conf.urls import url
from .views import generate_code
from django.contrib.auth.decorators import login_required

urlpatterns = [
    url('generate', login_required(generate_code), name='generate'),
]
