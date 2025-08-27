from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("profile/", views.profile_page, name="profile"),
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
    path('api/dashboard_algos/', views.api_dashboard_algos, name='api_dashboard_algos'),
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
# urls.py
    path('market/offers/', views.market_offers_list, name='market_offers_list'),            # GET discoverable offers
    path('market/offer/<int:offer_id>/', views.market_offer_detail, name='market_offer'),   # GET
    path('market/offer/<int:offer_id>/invite/', views.market_offer_invite, name='offer_invite'), # POST create invite
    path('market/invite/<str:token>/', views.market_invite_accept, name='invite_accept'),   # GET accept (creates trial/sub)
    path('market/subscribe/', views.market_subscribe, name='market_subscribe'),             # POST create subscription (free/trial or start checkout)
    path('webhooks/payments/', views.payments_webhook, name='payments_webhook'), 
    path('checkout/start', views.checkout_start, name='checkout_start'),
    path("api/algo/performance", views.api_algo_performance, name="api_algo_performance"),
    path('marketplace/', views.marketplace_page, name='marketplace'),
# urls.py
    path('api/dashboard/toggle_hide/', views.api_dashboard_toggle_hide, name='api_dashboard_toggle_hide'),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("resend-otps/", views.resend_otps, name="resend_otps"),
    path("login/", views.login_view, name="login"),
    path("accounts/login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("api/check-unique/", views.check_unique, name="check_unique"),
    path("profile/", views.profile_page, name="profile_page"),
    path("profile/update/", views.profile_update, name="profile_update"),
    path("profile/resend-otps/", views.profile_resend_otps, name="profile_resend_otps"),
    path("profile/change-password/", views.profile_change_password, name="profile_change_password"),
    path("dashboard/", views.dashboard_page, name="dashboard_page"),
# urls.py
path("signup/", views.signup_view, name="signup"),
path("signup/verify/", views.verify_signup_codes, name="verify_signup_codes"),
path("signup/resend/", views.resend_signup_codes, name="resend_signup_codes"),
path("profile/start-contact-change/", views.start_contact_change, name="start_contact_change"),
path("profile/verify-contact-change/", views.verify_contact_change, name="verify_contact_change"),
path("profile/change-password/current/", views.change_password_with_current, name="change_password_with_current"),
path("profile/change-password/start-otp/", views.start_password_change_otp, name="start_password_change_otp"),
path("profile/change-password/verify-otp/", views.verify_password_change_otp, name="verify_password_change_otp"),
path("profile/delete/", views.delete_account, name="delete_account"),
path("brokers/<int:broker_id>/edit/", views.broker_edit_page, name="broker_edit"),
    path("api/brokers/", views.api_brokers, name="api_brokers"),
    path("api/broker/<int:broker_id>/", views.api_broker_detail, name="api_broker_detail"),
    path("api/exchanges/", views.api_exchanges, name="api_exchanges"),


]
