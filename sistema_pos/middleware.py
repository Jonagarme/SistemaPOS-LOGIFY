from django.contrib.auth.models import AnonymousUser
from django.db import OperationalError, connection
from django.utils.functional import SimpleLazyObject


class OfflineAuthMiddleware:
    """
    Middleware que maneja la autenticación en modo offline
    usando datos de sesión cuando la base de datos no está disponible
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.db_available = True
        self.last_check = None
    
    def __call__(self, request):
        # Verificar conectividad de manera eficiente
        import time
        current_time = time.time()
        
        # Solo verificar cada 5 segundos para no sobrecargar
        if self.last_check is None or (current_time - self.last_check) > 5:
            try:
                # Intentar una consulta simple para verificar la conexión
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                self.db_available = True
                self.last_check = current_time
            except (OperationalError, Exception) as e:
                print(f"OfflineAuthMiddleware: Base de datos no disponible - {e}")
                self.db_available = False
                self.last_check = current_time
        
        # Establecer modo offline en el request
        request.modo_offline = not self.db_available
        
        if not self.db_available:
            # Modo offline - establecer usuario manualmente desde sesión
            usuario_offline = request.session.get('usuario_offline')
            
            if usuario_offline:
                # Crear un objeto simulado de usuario
                class OfflineUser:
                    def __init__(self, data):
                        self.id = data.get('id')
                        self.pk = data.get('id')
                        self.username = data.get('username')
                        self.nombre_completo = data.get('nombre_completo')
                        self.rol_nombre = data.get('rol_nombre')
                        self.usuario_sistema_id = data.get('usuario_sistema_id')
                        self.is_authenticated = True
                        self.is_active = True
                        self.is_staff = False
                        self.is_superuser = False
                        self.is_anonymous = False
                    
                    def __str__(self):
                        return self.username
                    
                    def get_username(self):
                        return self.username
                
                # Crear usuario offline y asignarlo
                offline_user = OfflineUser(usuario_offline)
                request.user = SimpleLazyObject(lambda: offline_user)
            else:
                # No hay datos de sesión, usar AnonymousUser
                request.user = SimpleLazyObject(lambda: AnonymousUser())
        
        response = self.get_response(request)
        return response
