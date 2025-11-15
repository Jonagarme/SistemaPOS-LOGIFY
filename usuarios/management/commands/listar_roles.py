from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Listar roles disponibles en tu tabla roles'
    
    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, nombre, descripcion, anulado
                    FROM roles 
                    ORDER BY id
                """)
                
                roles = cursor.fetchall()
                
                if not roles:
                    self.stdout.write(
                        self.style.WARNING('No hay roles en la tabla roles')
                    )
                    return
                
                self.stdout.write(
                    self.style.SUCCESS('Roles disponibles:')
                )
                self.stdout.write('-' * 50)
                
                for rol in roles:
                    id_rol, nombre, descripcion, anulado = rol
                    estado = "ANULADO" if anulado else "ACTIVO"
                    self.stdout.write(
                        f'ID: {id_rol:2d} | {nombre:20s} | {estado:8s} | {descripcion or "Sin descripción"}'
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al consultar roles: {str(e)}')
            )