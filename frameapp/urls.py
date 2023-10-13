from django.urls import path

from . import views

urlpatterns = [
    path('get_image/<str:episode_number>/<str:frame_time>/', views.give_image),
    path('get_episode_name/', views.get_episode_name),
    path('search/<str:user_input>/<int:fuzziness>/<str:name_weight>/<str:overview_weight>/', views.search),
    path('decrypt/<str:encrypted_data>/', views.decrypt_data_web)
]
