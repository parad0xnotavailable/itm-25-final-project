from django.urls import path
from . import views

urlpatterns = [
    path("", views.reservation_preface, name="home"),
    path("reserve/", views.reserve_init, name="reserve_init"),
    path("check-availability/", views.check_availability, name="check_availability"),
    path("alternatives/", views.reserve_alt, name="reserve_alt"),
    path("details/", views.details, name="details"),
    path("submit-reservation/", views.submit_reservation, name="submit_reservation"),
    path("reservation-success/", views.reservation_success, name="reservation_success"),
    path("cancel/<uuid:token>/", views.cancel_reservation, name="cancel_reservation"),
    path("join-waitlist/", views.join_waitlist, name="join_waitlist"),
    path('success/<int:reservation_id>/', views.success_final, name='success_final'),

]
