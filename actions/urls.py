from django.urls import path

from . import views

app_name = "actions"

urlpatterns = [
    path("inbound/", views.inbound_email_webhook, name="inbound_email"),
]
