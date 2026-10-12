from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Player
from .serializers import PlayerSerializer


class PlayerListCreateView(generics.ListCreateAPIView):
    """GET /api/players/  — list all players registered by this scout.
       POST /api/players/ — register a new player."""
    serializer_class   = PlayerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Player.objects.filter(registered_by=self.request.user)
        # Optional search by name
        name = self.request.query_params.get('name')
        if name:
            qs = qs.filter(full_name__icontains=name)
        return qs


class PlayerDetailView(generics.RetrieveUpdateAPIView):
    """GET  /api/players/{id}/ — get player detail.
       PATCH /api/players/{id}/ — update player info."""
    serializer_class   = PlayerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Player.objects.filter(registered_by=self.request.user)
