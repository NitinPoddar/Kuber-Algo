from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('profile/', views.profile, name='profile'),
    path('add-broker/', views.add_broker, name='add_broker'),
    path('add-algo/', views.add_algo, name='add_algo'),
    path('algo-list/', views.algo_list, name='algo_list'),
    path('edit-algo/<int:id>/', views.edit_algo, name='edit_algo'),
    path('delete-algo/<int:id>/', views.delete_algo, name='delete_algo'),
    path('register-algo/', views.register_algo, name='register_algo'),
    path('run-algo/', views.run_algo, name='run_algo'),
    path('get-minimum-fund/', views.get_minimum_fund, name='get_minimum_fund'),
    path('build-algo/', views.build_algo, name='build_algo'),
    path('api/instruments/grouped/', views.get_grouped_instruments, name='get_grouped_instruments'),
    path('insert-instruments/', views.insert_instruments, name='insert_instruments'),
    path('api/user_variable/save/', views.save_user_variable, name='save_user_variable'),
    path('api/user_variable/delete/', views.delete_user_variable, name='delete_user_variable'),
    path('check_algo_name/', views.check_algo_name, name='check_algo_name'),
]
