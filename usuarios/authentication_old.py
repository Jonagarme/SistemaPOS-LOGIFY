from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import Usuario


class CustomUserBackend(BaseBackend):
    """
    Backend de autenticación personalizado para la tabla usuarios
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Buscar usuario por nombre_usuario o email
            try:
                user = Usuario.objects.get(nombre_usuario=username, activo=True, anulado=False)
            except Usuario.DoesNotExist:
                try:
                    user = Usuario.objects.get(email=username, activo=True, anulado=False)
                except Usuario.DoesNotExist:
                    return None
            
            # Verificar contraseña
            if user.check_password(password):
                return user
            return None
            
        except Usuario.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None