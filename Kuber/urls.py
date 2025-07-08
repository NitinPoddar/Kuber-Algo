from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views  # Needed for signup_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # Core app URLs
    path('', include('core.urls')),  # includes all algo-related URLs

    # Auth routes
    path('signup/', views.signup_view, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
