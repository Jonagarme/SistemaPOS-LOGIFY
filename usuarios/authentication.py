from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class UsuarioSistemaBackend(BaseBackend):
    """
    Backend de autenticación que usa directamente tu tabla usuarios
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Autentica un usuario contra tu tabla usuarios existente
        """
        if username is None or password is None:
            return None
            
        try:
            with connection.cursor() as cursor:
                # Buscar usuario por nombreUsuario o email en tu tabla
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
                    logger.warning(f"Usuario no encontrado en tabla usuarios: {username}")
                    return None
                
                user_id, nombre_usuario, contrasena_hash, nombre_completo, email, activo, anulado, rol_nombre = row
                
                # Verificar contraseña - manejar múltiples formatos
                password_valid = False
                
                # 1. Intentar verificar con formato Django
                if contrasena_hash.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
                    password_valid = check_password(password, contrasena_hash)
                else:
                    # 2. Verificar con SHA-256 (tu formato actual)
                    import hashlib
                    sha256_hash = hashlib.sha256(password.encode()).hexdigest()
                    if sha256_hash == contrasena_hash:
                        password_valid = True
                        # Actualizar a formato Django para futuras verificaciones
                        from django.contrib.auth.hashers import make_password
                        new_hash = make_password(password)
                        try:
                            with connection.cursor() as update_cursor:
                                update_cursor.execute(
                                    "UPDATE usuarios SET contrasenaHash = %s WHERE id = %s",
                                    [new_hash, user_id]
                                )
                                logger.info(f"Contraseña actualizada a formato Django para usuario {username}")
                        except Exception as e:
                            logger.warning(f"No se pudo actualizar hash para {username}: {e}")
                
                if password_valid:
                    # Crear o actualizar usuario Django vinculado
                    django_username = f"usr_{user_id}"  # Prefijo para evitar conflictos
                    
                    user, created = User.objects.get_or_create(
                        username=django_username,
                        defaults={
                            'email': email,
                            'first_name': nombre_completo.split(' ')[0] if ' ' in nombre_completo else nombre_completo,
                            'last_name': ' '.join(nombre_completo.split(' ')[1:]) if ' ' in nombre_completo else '',
                            'is_active': True,
                            'is_staff': rol_nombre and 'admin' in rol_nombre.lower(),  # Determinar si es staff
                        }
                    )
                    
                    # Siempre actualizar datos para mantener sincronización
                    user.email = email
                    user.first_name = nombre_completo.split(' ')[0] if ' ' in nombre_completo else nombre_completo
                    user.last_name = ' '.join(nombre_completo.split(' ')[1:]) if ' ' in nombre_completo else ''
                    user.is_staff = rol_nombre and 'admin' in rol_nombre.lower()
                    user.save()
                    
                    # Agregar datos adicionales del sistema
                    user.usuario_sistema_id = user_id
                    user.nombre_usuario_original = nombre_usuario
                    user.rol_nombre = rol_nombre or "Sin rol"
                    user.nombre_completo = nombre_completo
                    
                    logger.info(f"Usuario autenticado exitosamente: {username} -> Django user: {django_username}")
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
            user = User.objects.get(pk=user_id)
            
            # Re-agregar datos del sistema si es necesario
            if hasattr(user, 'usuario_sistema_id'):
                return user
            
            # Si no tiene los datos, buscarlos en la BD
            if user.username.startswith('usr_'):
                sistema_id = user.username.replace('usr_', '')
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT u.id, u.nombreUsuario, u.nombreCompleto, 
                                   u.email, r.nombre as rol_nombre
                            FROM usuarios u
                            LEFT JOIN roles r ON u.idRol = r.id
                            WHERE u.id = %s AND u.activo = 1 AND u.anulado = 0
                        """, [sistema_id])
                        
                        row = cursor.fetchone()
                        if row:
                            user_id, nombre_usuario, nombre_completo, email, rol_nombre = row
                            user.usuario_sistema_id = user_id
                            user.nombre_usuario_original = nombre_usuario
                            user.rol_nombre = rol_nombre or "Sin rol"
                            user.nombre_completo = nombre_completo
                except:
                    pass
            
            return user
        except User.DoesNotExist:
            return None