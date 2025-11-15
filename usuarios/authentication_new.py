from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class CustomUserBackend(BaseBackend):
    """
    Backend de autenticación personalizado que verifica contra la tabla usuarios existente
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Autentica un usuario contra la tabla usuarios existente
        """
        if username is None or password is None:
            return None
            
        try:
            with connection.cursor() as cursor:
                # Buscar usuario por nombre de usuario o email
                cursor.execute("""
                    SELECT u.id, u.nombreUsuario, u.contrasenaHash, u.nombreCompleto, 
                           u.email, u.activo, u.anulado, r.nombre as rol_nombre
                    FROM usuarios u
                    LEFT JOIN roles r ON u.idRol = r.id
                    WHERE (u.nombreUsuario = %s OR u.email = %s) 
                    AND u.activo = 1 AND u.anulado = 0
                """, [username, username])
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Usuario no encontrado: {username}")
                    return None
                
                user_id, nombre_usuario, contrasena_hash, nombre_completo, email, activo, anulado, rol_nombre = row
                
                # Verificar contraseña
                if check_password(password, contrasena_hash):
                    # Crear o obtener el usuario de Django vinculado
                    user, created = User.objects.get_or_create(
                        username=nombre_usuario,
                        defaults={
                            'email': email,
                            'first_name': nombre_completo.split(' ')[0] if ' ' in nombre_completo else nombre_completo,
                            'last_name': ' '.join(nombre_completo.split(' ')[1:]) if ' ' in nombre_completo else '',
                            'is_active': True,
                        }
                    )
                    
                    # Actualizar datos si es necesario
                    if not created:
                        user.email = email
                        user.first_name = nombre_completo.split(' ')[0] if ' ' in nombre_completo else nombre_completo
                        user.last_name = ' '.join(nombre_completo.split(' ')[1:]) if ' ' in nombre_completo else ''
                        user.save()
                    
                    # Agregar datos adicionales del usuario del sistema
                    user.usuario_id = user_id
                    user.rol_nombre = rol_nombre or "Sin rol"
                    
                    logger.info(f"Usuario autenticado exitosamente: {username}")
                    return user
                else:
                    logger.warning(f"Contraseña incorrecta para usuario: {username}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error en autenticación: {str(e)}")
            return None
    
    def get_user(self, user_id):
        """
        Obtiene un usuario por ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None