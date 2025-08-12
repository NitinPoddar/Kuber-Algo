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
    path('get-minimum-fund/', views.get_minimum_fund, name='get_minimum_fund'),
    path('api/instruments/grouped/', views.get_grouped_instruments, name='get_grouped_instruments'),
    path('insert-instruments/', views.insert_instruments, name='insert_instruments'),
    path('api/user_variable/save/', views.save_user_variable, name='save_user_variable'),
    path('api/user_variable/delete/', views.delete_user_variable, name='delete_user_variable'),
    path('check_algo_name/', views.check_algo_name, name='check_algo_name'),
    path('variables/', views.variable_parameters_page, name='variable_parameters'),
    path('api/variables/', views.api_variables, name='api_variables'),
    path('api/variable/<int:var_id>/', views.api_variable_detail, name='api_variable_detail'),
    path('api/categories/', views.api_categories, name='api_categories'),
    path('api/parameters/', views.api_parameters, name='api_parameters'),
    path('api/parameter/<int:param_id>/', views.api_parameter_detail, name='api_parameter_detail'),
    path('api/test_function_code/', views.api_test_function_code, name='api_test_function_code'),
    path('environment/', views.environment_page, name='environment'),
    # BrokerAccount
    path('api/env/accounts/', views.api_broker_accounts, name='api_broker_accounts'),                 # GET, POST
    path('api/env/account/<int:acc_id>/', views.api_broker_account_detail, name='api_broker_account_detail'),  # POST, DELETE
    path('api/env/account/<int:acc_id>/test/', views.api_broker_account_test, name='api_broker_account_test'), # POST
    # AlgoBrokerLink
    path('api/env/links/', views.api_links, name='api_links'),                         # GET (filter by algo), POST
    path('api/env/link/<int:link_id>/', views.api_link_detail, name='api_link_detail'), # POST, DELETE
    # Global Variables
    path('api/env/globals/', views.api_globals, name='api_globals'),                   # GET, POST
    path('api/env/global/<int:gv_id>/', views.api_global_detail, name='api_global_detail'),  # POST, DELETE
    path('dashboard/', views.dashboard_page, name='dashboard'),
    # dashboard data & actions
    path('api/dashboard/algos/', views.api_dashboard_algos, name='api_dashboard_algos'),
    path('api/dashboard/<int:algo_id>/register/', views.api_dashboard_register, name='api_dashboard_register'),
    path('api/dashboard/<int:algo_id>/run/', views.api_dashboard_run, name='api_dashboard_run'),
    path('api/dashboard/<int:algo_id>/pause/', views.api_dashboard_pause, name='api_dashboard_pause'),
    path('api/dashboard/<int:algo_id>/stop/', views.api_dashboard_stop, name='api_dashboard_stop'),
    path('api/dashboard/<int:algo_id>/logs/', views.api_dashboard_logs, name='api_dashboard_logs'),
    # core/urls.py
path('api/dashboard/status_styles/', views.api_status_styles, name='api_status_styles'),
# add this
path('accounts/brokers/new', views.broker_account_create, name='broker-account-create'),
]
