from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal

from usuarios.models import PerfilUsuario
from productos.models import Categoria, Marca, UnidadMedida, Producto
from clientes.models import Cliente
from proveedores.models import Proveedor
from caja.models import Caja


class Command(BaseCommand):
    help = 'Crea datos de prueba para el sistema POS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Elimina todos los datos existentes antes de crear nuevos',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Eliminando datos existentes...')
            self.reset_data()

        self.stdout.write('Creando datos de prueba...')
        
        with transaction.atomic():
            self.create_users()
            self.create_categories()
            self.create_brands()
            self.create_units()
            self.create_products()
            self.create_clients()
            self.create_suppliers()
            self.create_cash_registers()

        self.stdout.write(
            self.style.SUCCESS('Datos de prueba creados exitosamente')
        )

    def reset_data(self):
        """Elimina todos los datos de prueba"""
        Producto.objects.all().delete()
        Categoria.objects.all().delete()
        Marca.objects.all().delete()
        UnidadMedida.objects.all().delete()
        Cliente.objects.all().delete()
        Proveedor.objects.all().delete()
        Caja.objects.all().delete()
        PerfilUsuario.objects.exclude(usuario__is_superuser=True).delete()
        User.objects.filter(is_superuser=False).delete()

    def create_users(self):
        """Crea usuarios de prueba"""
        usuarios_data = [
            {
                'username': 'cajero1',
                'first_name': 'María',
                'last_name': 'González',
                'email': 'maria@pos.com',
                'password': 'password123',
                'rol': 'cajero'
            },
            {
                'username': 'vendedor1',
                'first_name': 'Carlos',
                'last_name': 'Rodríguez',
                'email': 'carlos@pos.com',
                'password': 'password123',
                'rol': 'vendedor'
            },
            {
                'username': 'supervisor1',
                'first_name': 'Ana',
                'last_name': 'Martínez',
                'email': 'ana@pos.com',
                'password': 'password123',
                'rol': 'supervisor'
            }
        ]

        for user_data in usuarios_data:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    email=user_data['email'],
                    password=user_data['password']
                )
                
                PerfilUsuario.objects.create(
                    usuario=user,
                    rol=user_data['rol'],
                    telefono='9999-9999',
                    direccion='Dirección de prueba'
                )
                
                self.stdout.write(f'Usuario creado: {user_data["username"]}')

    def create_categories(self):
        """Crea categorías de productos"""
        categorias = [
            'Alimentos',
            'Bebidas',
            'Limpieza',
            'Higiene Personal',
            'Electrónicos',
            'Papelería',
            'Hogar',
            'Medicamentos'
        ]

        for nombre in categorias:
            categoria, created = Categoria.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': f'Categoría de {nombre.lower()}'}
            )
            if created:
                self.stdout.write(f'Categoría creada: {nombre}')

    def create_brands(self):
        """Crea marcas de productos"""
        marcas = [
            'Coca Cola',
            'Pepsi',
            'Nestlé',
            'Unilever',
            'P&G',
            'Samsung',
            'Sony',
            'Genérica'
        ]

        for nombre in marcas:
            marca, created = Marca.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': f'Marca {nombre}'}
            )
            if created:
                self.stdout.write(f'Marca creada: {nombre}')

    def create_units(self):
        """Crea unidades de medida"""
        unidades = [
            ('Unidad', 'UN'),
            ('Kilogramo', 'KG'),
            ('Gramo', 'GR'),
            ('Litro', 'LT'),
            ('Mililitro', 'ML'),
            ('Metro', 'MT'),
            ('Centímetro', 'CM'),
            ('Docena', 'DOC'),
            ('Caja', 'CJ'),
            ('Paquete', 'PQ')
        ]

        for nombre, abrev in unidades:
            unidad, created = UnidadMedida.objects.get_or_create(
                nombre=nombre,
                abreviacion=abrev
            )
            if created:
                self.stdout.write(f'Unidad creada: {nombre}')

    def create_products(self):
        """Crea productos de prueba"""
        productos_data = [
            {
                'codigo': 'PROD001',
                'nombre': 'Coca Cola 600ml',
                'categoria': 'Bebidas',
                'marca': 'Coca Cola',
                'unidad': 'UN',
                'precio_compra': Decimal('15.00'),
                'precio_venta': Decimal('20.00'),
                'stock_actual': 50
            },
            {
                'codigo': 'PROD002',
                'nombre': 'Pan Blanco',
                'categoria': 'Alimentos',
                'marca': 'Genérica',
                'unidad': 'UN',
                'precio_compra': Decimal('8.00'),
                'precio_venta': Decimal('12.00'),
                'stock_actual': 30
            },
            {
                'codigo': 'PROD003',
                'nombre': 'Detergente en Polvo 1kg',
                'categoria': 'Limpieza',
                'marca': 'Unilever',
                'unidad': 'KG',
                'precio_compra': Decimal('25.00'),
                'precio_venta': Decimal('35.00'),
                'stock_actual': 20
            },
            {
                'codigo': 'PROD004',
                'nombre': 'Agua Purificada 1L',
                'categoria': 'Bebidas',
                'marca': 'Genérica',
                'unidad': 'LT',
                'precio_compra': Decimal('5.00'),
                'precio_venta': Decimal('8.00'),
                'stock_actual': 100
            },
            {
                'codigo': 'PROD005',
                'nombre': 'Papel Higiénico 4 rollos',
                'categoria': 'Higiene Personal',
                'marca': 'P&G',
                'unidad': 'PQ',
                'precio_compra': Decimal('18.00'),
                'precio_venta': Decimal('25.00'),
                'stock_actual': 40
            }
        ]

        for prod_data in productos_data:
            if not Producto.objects.filter(codigo=prod_data['codigo']).exists():
                categoria = Categoria.objects.get(nombre=prod_data['categoria'])
                marca = Marca.objects.get(nombre=prod_data['marca'])
                unidad = UnidadMedida.objects.get(abreviacion=prod_data['unidad'])

                producto = Producto.objects.create(
                    codigo=prod_data['codigo'],
                    nombre=prod_data['nombre'],
                    categoria=categoria,
                    marca=marca,
                    unidad_medida=unidad,
                    precio_compra=prod_data['precio_compra'],
                    precio_venta=prod_data['precio_venta'],
                    stock_actual=prod_data['stock_actual'],
                    stock_minimo=5,
                    stock_maximo=100
                )
                
                self.stdout.write(f'Producto creado: {prod_data["nombre"]}')

    def create_clients(self):
        """Crea clientes de prueba"""
        clientes_data = [
            {
                'codigo': 'CLI001',
                'nombres': 'Juan Carlos',
                'apellidos': 'Pérez López',
                'numero_documento': '0801-1990-12345',
                'telefono': '9999-1234',
                'email': 'juan@email.com'
            },
            {
                'codigo': 'CLI002',
                'nombres': 'María Elena',
                'apellidos': 'García Mendoza',
                'numero_documento': '0801-1985-67890',
                'telefono': '9999-5678',
                'email': 'maria@email.com'
            },
            {
                'codigo': 'CLI003',
                'tipo_cliente': 'empresa',
                'nombres': 'Empresa',
                'nombre_comercial': 'Comercial Los Ángeles S.A.',
                'numero_documento': '08019990001234',
                'telefono': '2222-1234',
                'email': 'ventas@losangeles.com'
            }
        ]

        for cliente_data in clientes_data:
            if not Cliente.objects.filter(codigo=cliente_data['codigo']).exists():
                cliente = Cliente.objects.create(**cliente_data)
                self.stdout.write(f'Cliente creado: {cliente.nombre_completo}')

    def create_suppliers(self):
        """Crea proveedores de prueba"""
        proveedores_data = [
            {
                'codigo': 'PROV001',
                'nombre_comercial': 'Distribuidora Central S.A.',
                'numero_documento': '08019990001111',
                'contacto_principal': 'Luis Martínez',
                'telefono': '2222-5555',
                'email': 'ventas@distribuidoracentral.com'
            },
            {
                'codigo': 'PROV002',
                'nombre_comercial': 'Suplidora Nacional',
                'numero_documento': '08019990002222',
                'contacto_principal': 'Carmen Rodríguez',
                'telefono': '2222-6666',
                'email': 'compras@suplidoranacional.com'
            }
        ]

        for prov_data in proveedores_data:
            if not Proveedor.objects.filter(codigo=prov_data['codigo']).exists():
                proveedor = Proveedor.objects.create(**prov_data)
                self.stdout.write(f'Proveedor creado: {proveedor.nombre_comercial}')

    def create_cash_registers(self):
        """Crea cajas registradoras"""
        cajas = [
            'Caja Principal',
            'Caja Secundaria',
            'Caja Express'
        ]

        for nombre in cajas:
            caja, created = Caja.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': f'Descripción de {nombre}'}
            )
            if created:
                self.stdout.write(f'Caja creada: {nombre}')