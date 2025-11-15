from django.core.management.base import BaseCommand
from usuarios.models import Usuario, Rol
from django.contrib.auth.hashers import make_password
from django.utils import timezone


class Command(BaseCommand):
    help = 'Crear usuario administrador'
    
    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Nombre de usuario')
        parser.add_argument('--email', type=str, help='Email del usuario')
        parser.add_argument('--password', type=str, help='Contraseña')
        parser.add_argument('--nombre', type=str, help='Nombre completo')
        
    def handle(self, *args, **options):
        username = options.get('username') or input('Nombre de usuario: ')
        email = options.get('email') or input('Email: ')
        password = options.get('password') or input('Contraseña: ')
        nombre = options.get('nombre') or input('Nombre completo: ')
        
        # Verificar si existe un rol admin
        try:
            rol_admin = Rol.objects.get(id=1)  # Asumiendo que el rol admin tiene id=1
        except Rol.DoesNotExist:
            self.stdout.write(self.style.ERROR('No existe un rol con id=1. Creando rol por defecto...'))
            # En este caso, necesitarías crear el rol manualmente en la BD
            return
        
        # Crear usuario
        try:
            usuario = Usuario.objects.create(
                nombre_usuario=username,
                email=email,
                contrasena_hash=make_password(password),
                nombre_completo=nombre,
                id_rol=rol_admin,
                activo=True,
                is_staff=True,
                is_superuser=True,
                creado_date=timezone.now()
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Usuario {username} creado exitosamente')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creando usuario: {str(e)}')
            )