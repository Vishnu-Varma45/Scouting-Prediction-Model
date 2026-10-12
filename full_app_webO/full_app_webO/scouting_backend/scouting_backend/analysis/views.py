from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


class SignupView(APIView):
    """
    POST /api/auth/signup/
    Body: {
        "username": "...",
        "password": "...",
        "full_name": "...",   ← optional
        "email": "..."        ← optional
    }
    Returns: { "token": "...", "user_id": ..., "username": "..." }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username  = request.data.get('username', '').strip()
        password  = request.data.get('password', '').strip()
        full_name = request.data.get('full_name', '').strip()
        email     = request.data.get('email', '').strip()

        # Validation
        if not username:
            return Response(
                {"error": "Username is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not password:
            return Response(
                {"error": "Password is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(password) < 6:
            return Response(
                {"error": "Password must be at least 6 characters"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already taken. Choose a different one."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if email and User.objects.filter(email=email).exists():
            return Response(
                {"error": "An account with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create user
        first_name = ''
        last_name  = ''
        if full_name:
            parts      = full_name.split(' ', 1)
            first_name = parts[0]
            last_name  = parts[1] if len(parts) > 1 else ''

        user = User.objects.create_user(
            username   = username,
            password   = password,
            email      = email,
            first_name = first_name,
            last_name  = last_name,
        )

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token"    : token.key,
            "user_id"  : user.pk,
            "username" : user.username,
            "full_name": user.get_full_name(),
            "email"    : user.email,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "username": "...", "password": "..." }
    Returns: { "token": "...", "user_id": ..., "username": "..." }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token"    : token.key,
            "user_id"  : user.pk,
            "username" : user.username,
            "full_name": user.get_full_name(),
            "email"    : user.email,
        })


class LogoutView(APIView):
    """POST /api/auth/logout/ — deletes the auth token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({"message": "Logged out successfully"})


class ProfileView(APIView):
    """GET /api/auth/profile/ — returns logged-in scout's info."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "user_id"  : user.pk,
            "username" : user.username,
            "full_name": user.get_full_name(),
            "email"    : user.email,
        })
