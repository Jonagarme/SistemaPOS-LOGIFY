from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = 'Crear un usuario en tu tabla usuarios existente'
    
    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Nombre de usuario')
        parser.add_argument('--password', required=True, help='Contraseña')
        parser.add_argument('--email', required=True, help='Email del usuario')
        parser.add_argument('--nombre', required=True, help='Nombre completo')
        parser.add_argument('--rol', type=int, default=1, help='ID del rol (default: 1)')
    
    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        nombre_completo = options['nombre']
        id_rol = options['rol']
        
        # Hashear la contraseña
        password_hash = make_password(password)
        
        try:
            with connection.cursor() as cursor:
                # Verificar si el usuario ya existe
                cursor.execute(
                    "SELECT id FROM usuarios WHERE nombreUsuario = %s OR email = %s", 
                    [username, email]
                )
                
                if cursor.fetchone():
                    self.stdout.write(
                        self.style.ERROR(f'El usuario {username} o email {email} ya existe')
                    )
                    return
                
                # Verificar que el rol existe
                cursor.execute("SELECT id FROM roles WHERE id = %s", [id_rol])
                if not cursor.fetchone():
                    self.stdout.write(
                        self.style.ERROR(f'El rol con ID {id_rol} no existe')
                    )
                    return
                
                # Insertar el usuario
                cursor.execute("""
                    INSERT INTO usuarios (idRol, nombreUsuario, contrasenaHash, nombreCompleto, 
                                        email, activo, creadoDate, anulado)
                    VALUES (%s, %s, %s, %s, %s, 1, %s, 0)
                """, [id_rol, username, password_hash, nombre_completo, email, timezone.now()])
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Usuario {username} creado exitosamente en la tabla usuarios'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al crear usuario: {str(e)}')
            )