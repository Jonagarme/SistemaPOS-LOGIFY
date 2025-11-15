# -*- coding: utf-8 -*-
"""
Comando para migrar stock global a stock por ubicación
Uso: python manage.py migrar_stock_sucursales
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from inventario.models import Ubicacion, StockUbicacion
from productos.models import Producto

User = get_user_model()


class Command(BaseCommand):
    help = 'Migra el stock global de productos a la ubicación principal'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ubicacion',
            type=int,
            help='ID de la ubicación principal (si no se especifica, usa la marcada como principal)'
        )
        parser.add_argument(
            '--usuario',
            type=int,
            default=1,
            help='ID del usuario que ejecuta la migración (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la migración sin guardar cambios'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        usuario_id = options['usuario']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('MIGRACIÓN DE STOCK A SISTEMA DE SUCURSALES'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n⚠️  Modo DRY-RUN activado - No se guardarán cambios\n'))
        
        try:
            # Obtener usuario
            try:
                usuario = User.objects.get(id=usuario_id)
                self.stdout.write(f'✓ Usuario: {usuario.username}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'✗ Usuario con ID {usuario_id} no existe'))
                return
            
            # Obtener o crear ubicación principal
            if options['ubicacion']:
                ubicacion = Ubicacion.objects.get(id=options['ubicacion'])
            else:
                ubicacion, created = Ubicacion.objects.get_or_create(
                    es_principal=True,
                    defaults={
                        'codigo': 'PRINC',
                        'nombre': 'Sucursal Principal',
                        'tipo': 'sucursal',
                        'activo': True,
                        'creadoPor': usuario
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✓ Ubicación principal creada: {ubicacion.nombre}'))
                else:
                    self.stdout.write(f'✓ Ubicación principal: {ubicacion.nombre}')
            
            # Obtener productos activos
            productos = Producto.objects.filter(activo=True)
            total_productos = productos.count()
            
            self.stdout.write(f'\n📦 Total de productos activos: {total_productos}')
            
            if dry_run:
                self.stdout.write(self.style.NOTICE('\n🔍 Productos que se migrarían:'))
                for producto in productos[:10]:  # Mostrar solo los primeros 10
                    stock_actual = getattr(producto, 'stock', 0)
                    self.stdout.write(f'   - {producto.nombre}: {stock_actual} unidades')
                if total_productos > 10:
                    self.stdout.write(f'   ... y {total_productos - 10} productos más')
                self.stdout.write(self.style.WARNING('\n⚠️  Ejecuta sin --dry-run para aplicar los cambios'))
                return
            
            # Realizar migración con transacción
            with transaction.atomic():
                creados = 0
                actualizados = 0
                errores = 0
                
                self.stdout.write('\n🔄 Migrando stock...')
                
                for producto in productos:
                    try:
                        stock_actual = getattr(producto, 'stock', 0)
                        
                        # Obtener o crear stock por ubicación
                        stock_ubicacion, created = StockUbicacion.objects.get_or_create(
                            producto=producto,
                            ubicacion=ubicacion,
                            defaults={
                                'cantidad': stock_actual,
                                'stock_minimo': 0,
                                'punto_reorden': 0,
                                'creadoPor': usuario
                            }
                        )
                        
                        if created:
                            creados += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'   ✓ {producto.nombre}: {stock_actual} unidades'
                                )
                            )
                        else:
                            # Si ya existe, actualizar cantidad si es diferente
                            if stock_ubicacion.cantidad != stock_actual:
                                stock_ubicacion.cantidad = stock_actual
                                stock_ubicacion.editadoPor = usuario
                                stock_ubicacion.save()
                                actualizados += 1
                                self.stdout.write(
                                    f'   ↻ {producto.nombre}: actualizado a {stock_actual} unidades'
                                )
                    
                    except Exception as e:
                        errores += 1
                        self.stdout.write(
                            self.style.ERROR(f'   ✗ Error en {producto.nombre}: {str(e)}')
                        )
                
                # Resumen
                self.stdout.write('\n' + '=' * 70)
                self.stdout.write(self.style.SUCCESS('✓ MIGRACIÓN COMPLETADA'))
                self.stdout.write('=' * 70)
                self.stdout.write(f'\n📊 Resumen:')
                self.stdout.write(f'   • Productos nuevos: {creados}')
                self.stdout.write(f'   • Productos actualizados: {actualizados}')
                if errores > 0:
                    self.stdout.write(self.style.ERROR(f'   • Errores: {errores}'))
                self.stdout.write(f'   • Total procesados: {total_productos}')
                
                self.stdout.write('\n📍 Siguiente pasos:')
                self.stdout.write('   1. Verifica los stocks en el admin de Django')
                self.stdout.write('   2. Crea ubicaciones adicionales si tienes más sucursales')
                self.stdout.write('   3. Asigna cada caja a su ubicación correspondiente')
                self.stdout.write('   4. Comienza a usar transferencias entre sucursales')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error general: {str(e)}'))
            raise
