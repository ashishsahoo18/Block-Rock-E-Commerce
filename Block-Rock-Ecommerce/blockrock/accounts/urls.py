from django.urls import path

from . import views


urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('account/', views.account, name='account'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/password/', views.profile_password, name='profile_password'),
    path('password-reset/', views.AccountPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.AccountPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.AccountPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.AccountPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('accounts/signup/', views.register, name='signup'),
]
