from django.urls import path
from django.contrib.auth import views as auth_views
from account import views as account_views
from wrsm_app import views as wrsm_app_views
from .views import LoginView


urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', wrsm_app_views.custom_logout_view, name='logout'),
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'), name='password_change_done'),
    path('password-reset/', auth_views.PasswordResetView.as_view(),
        name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'),
    path('register/', account_views.register, name='register'),
    path('edit/', account_views.edit, name='edit'),
    
    path('api/login/', LoginView.as_view(), name='api_login'),
]