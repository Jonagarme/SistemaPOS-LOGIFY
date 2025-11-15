from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import connection
import hashlib


class Command(BaseCommand):
    help = 'Convierte contraseñas SHA-256 a formato Django'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario', 
            help='Convertir solo un usuario específico'
        )
        parser.add_argument(
            '--password', 
            help='Contraseña en texto plano para el usuario específico'
        )
        parser.add_argument(
            '--dry-run', 
            action='store_true',
            help='Solo mostrar qué se haría, sin hacer cambios'
        )
    
    def handle(self, *args, **options):
        if options['usuario'] and options['password']:
            # Convertir un usuario específico con contraseña conocida
            self.convert_specific_user(options['usuario'], options['password'], options['dry_run'])
        else:
            # Mostrar usuarios con formato SHA-256
            self.show_sha256_users()
    
    def convert_specific_user(self, username, password, dry_run):
        """Convierte la contraseña de un usuario específico"""
        try:
            with connection.cursor() as cursor:
                # Buscar usuario
                cursor.execute("""
                    SELECT id, nombreUsuario, contrasenaHash 
                    FROM usuarios 
                    WHERE nombreUsuario = %s
                """, [username])
                
                row = cursor.fetchone()
                if not row:
                    self.stdout.write(
                        self.style.ERROR(f'Usuario {username} no encontrado')
                    )
                    return
                
                user_id, nombre_usuario, current_hash = row
                
                # Verificar si la contraseña actual es SHA-256
                sha256_hash = hashlib.sha256(password.encode()).hexdigest()
                
                if current_hash == sha256_hash:
                    # Es SHA-256, convertir a Django
                    new_hash = make_password(password)
                    
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(f'[DRY RUN] Se convertiría {username}:')
                        )
                        self.stdout.write(f'  SHA-256: {current_hash}')
                        self.stdout.write(f'  Django:  {new_hash[:50]}...')
                    else:
                        cursor.execute(
                            "UPDATE usuarios SET contrasenaHash = %s WHERE id = %s",
                            [new_hash, user_id]
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Contraseña de {username} convertida a formato Django')
                        )
                elif current_hash.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  {username} ya tiene formato Django')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ La contraseña de {username} no coincide o tiene formato desconocido')
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
    
    def show_sha256_users(self):
        """Muestra usuarios que probablemente tienen contraseñas SHA-256"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT u.id, u.nombreUsuario, u.contrasenaHash, u.email, r.nombre as rol
                    FROM usuarios u
                    LEFT JOIN roles r ON u.idRol = r.id
                    WHERE u.activo = 1 AND u.anulado = 0
                    ORDER BY u.id
                """)
                
                users = cursor.fetchall()
                
                if not users:
                    self.stdout.write(
                        self.style.WARNING('No hay usuarios activos')
                    )
                    return
                
                self.stdout.write(
                    self.style.SUCCESS('Usuarios en el sistema:')
                )
                self.stdout.write('-' * 80)
                
                for user in users:
                    user_id, username, password_hash, email, rol = user
                    
                    # Determinar tipo de hash
                    if password_hash.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
                        hash_type = "Django ✅"
                    elif len(password_hash) == 64 and all(c in '0123456789abcdef' for c in password_hash):
                        hash_type = "SHA-256 ⚠️"
                    else:
                        hash_type = "Desconocido ❌"
                    
                    self.stdout.write(
                        f'ID: {user_id:2d} | {username:15s} | {hash_type:12s} | {rol or "Sin rol":15s} | {email}'
                    )
                
                self.stdout.write('\n' + '=' * 80)
                self.stdout.write('Para convertir un usuario específico:')
                self.stdout.write('python manage.py convertir_passwords --usuario admin --password admin')
                self.stdout.write('python manage.py convertir_passwords --usuario admin --password admin --dry-run')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )