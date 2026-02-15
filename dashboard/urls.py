from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("action/<int:pk>/", views.action_detail, name="detail"),
    path("action/<int:pk>/update/", views.action_update, name="update"),
    path("action/<int:pk>/respond/", views.add_response, name="respond"),
    path("action/create/", views.action_create, name="create"),
    path("report/<int:year>/week/<int:week>/", views.weekly_report, name="weekly_report"),
]
