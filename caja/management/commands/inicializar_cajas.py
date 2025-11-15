from django.core.management.base import BaseCommand
from caja.models import Caja


class Command(BaseCommand):
    help = 'Inicializa datos básicos del sistema de cajas'

    def handle(self, *args, **options):
        # Crear caja principal por defecto si no existe
        caja_principal, created = Caja.objects.get_or_create(
            nombre='Caja Principal',
            defaults={
                'ubicacion': 'Mostrador Principal',
                'descripcion': 'Caja principal del punto de venta',
                'activa': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Caja "{caja_principal.nombre}" creada exitosamente')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Caja "{caja_principal.nombre}" ya existe')
            )
        
        # Verificar que exista al menos una caja activa
        cajas_activas = Caja.objects.filter(activa=True).count()
        self.stdout.write(
            self.style.SUCCESS(f'Total de cajas activas: {cajas_activas}')
        )