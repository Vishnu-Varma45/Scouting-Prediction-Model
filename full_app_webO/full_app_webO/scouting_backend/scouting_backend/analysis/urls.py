from django.urls import path
from .views import LoginView, LogoutView, ProfileView, SignupView

urlpatterns = [
    path('signup/',  SignupView.as_view(),  name='auth-signup'),
    path('login/',   LoginView.as_view(),   name='auth-login'),
    path('logout/',  LogoutView.as_view(),  name='auth-logout'),
    path('profile/', ProfileView.as_view(), name='auth-profile'),
]

