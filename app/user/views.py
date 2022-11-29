"""
Views para o user API.
"""
from rest_framework import authentication, generics, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from user.serializer import AuthTokenSerializer, UserSerializer


class CreateUserView(generics.CreateAPIView):
    """Criando um novo usuário no sistema"""
    serializer_class = UserSerializer

class CreateTokenView(ObtainAuthToken):
    """Criando um novo token para o usuário"""
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Recupera e retorna o usuário autenticado."""
        return self.request.user