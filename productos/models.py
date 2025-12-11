from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.contrib.auth.models import User


class TipoProducto(models.Model):
    """Tipos de productos del negocio"""
    nombre = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'tipos_producto'
        managed = False
        verbose_name = "Tipo de Producto"
        verbose_name_plural = "Tipos de Producto"
    
    def __str__(self):
        return self.nombre


class ClaseProducto(models.Model):
    """Clases de productos comerciales"""
    nombre = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'clases_producto'
        managed = False
        verbose_name = "Clase de Producto"
        verbose_name_plural = "Clases de Producto"
    
    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    """Categorías de productos"""
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='creadoPor', related_name='categorias_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column='creadoDate')
    
    class Meta:
        db_table = 'categorias'
        managed = False
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Subcategoria(models.Model):
    """Subcategorías de productos"""
    nombre = models.CharField(max_length=100)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, db_column='idCategoria')
    
    class Meta:
        db_table = 'subcategorias'
        managed = False
        verbose_name = "Subcategoría"
        verbose_name_plural = "Subcategorías"
    
    def __str__(self):
        return self.nombre


class SubnivelProducto(models.Model):
    """Subniveles de productos"""
    nombre = models.CharField(max_length=100)
    id_subcategoria = models.ForeignKey(Subcategoria, on_delete=models.CASCADE, db_column='idSubcategoria')
    
    class Meta:
        db_table = 'subniveles_producto'
        managed = False
        verbose_name = "Subnivel de Producto"
        verbose_name_plural = "Subniveles de Producto"
    
    def __str__(self):
        return self.nombre


class Marca(models.Model):
    """Marcas de productos"""
    nombre = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'marcas'
        managed = False
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Laboratorio(models.Model):
    """Laboratorios y fabricantes"""
    nombre = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'laboratorios'
        managed = False
        verbose_name = "Laboratorio"
        verbose_name_plural = "Laboratorios"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Modelo adaptado para la estructura de productos de LogiPharmBD"""
    
    CLASIFICACION_ABC_CHOICES = [
        ('A', 'Clase A'),
        ('B', 'Clase B'), 
        ('C', 'Clase C'),
    ]
    
    # Campos principales
    nombre = models.CharField(max_length=255)
    codigo_principal = models.CharField(max_length=50, unique=True, db_column='codigoPrincipal')
    codigo_auxiliar = models.CharField(max_length=50, null=True, blank=True, db_column='codigoAuxiliar')
    descripcion = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    registro_sanitario = models.CharField(max_length=50, null=True, blank=True, db_column='registroSanitario')
    fecha_caducidad = models.DateField(null=True, blank=True, db_column='fechaCaducidad', help_text='Fecha de caducidad del producto')
    
    # Relaciones foráneas
    id_tipo_producto = models.ForeignKey(TipoProducto, on_delete=models.PROTECT, default=1, db_column='idTipoProducto')
    id_clase_producto = models.ForeignKey(ClaseProducto, on_delete=models.PROTECT, default=1, db_column='idClaseProducto')
    id_categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, default=1, db_column='idCategoria')
    id_subcategoria = models.ForeignKey(Subcategoria, on_delete=models.PROTECT, default=1, db_column='idSubcategoria')
    id_subnivel = models.ForeignKey(SubnivelProducto, on_delete=models.SET_NULL, null=True, blank=True, db_column='idSubnivel')
    id_marca = models.ForeignKey(Marca, on_delete=models.PROTECT, default=1, db_column='idMarca')
    id_laboratorio = models.ForeignKey(Laboratorio, on_delete=models.SET_NULL, null=True, blank=True, default=1, db_column='idLaboratorio')
    
    # Inventario
    stock = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, db_column='stockMinimo')
    stock_maximo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, db_column='stockMaximo')
    
    # Precios y costos
    costo_unidad = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000, db_column='costoUnidad')
    costo_caja = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000, db_column='costoCaja')
    pvp_unidad = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000, db_column='pvpUnidad')
    precio_venta = models.DecimalField(max_digits=12, decimal_places=4, default=0.0000, db_column='precioVenta')
    
    # Características del producto
    es_divisible = models.BooleanField(default=False, db_column='esDivisible')
    es_psicotropico = models.BooleanField(default=False, db_column='esPsicotropico')
    requiere_cadena_frio = models.BooleanField(default=False, db_column='requiereCadenaFrio')
    requiere_seguimiento = models.BooleanField(default=False, db_column='requiereSeguimiento')
    calculo_abc_manual = models.BooleanField(default=False, db_column='calculoABCManual')
    clasificacion_abc = models.CharField(max_length=1, choices=CLASIFICACION_ABC_CHOICES, null=True, blank=True, db_column='clasificacionABC')
    
    # Control y auditoría (simplificado)
    activo = models.BooleanField(default=True)
    anulado = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'productos'
        managed = False
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo_principal} - {self.nombre}"
    
    @property
    def porcentaje_ganancia(self):
        """Calcula el porcentaje de ganancia basado en costo y precio de venta"""
        if self.costo_unidad > 0:
            return ((self.precio_venta - self.costo_unidad) / self.costo_unidad) * 100
        return 0
    
    @property
    def necesita_restock(self):
        """Verifica si el producto necesita reabastecimiento"""
        return self.stock <= self.stock_minimo
    
    @property
    def valor_inventario(self):
        """Calcula el valor total del inventario de este producto"""
        return self.stock * self.costo_unidad
    
    @property
    def tiene_stock_disponible(self):
        """Verifica si hay stock disponible"""
        return self.stock > 0 and self.activo and not self.anulado


# Modelos para ubicación de productos en perchas
class Seccion(models.Model):
    """Secciones del establecimiento (Ej: Productos A, Productos B, Accesorios)"""
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text='Color hex para identificación visual')
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=1)
    
    class Meta:
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"
        ordering = ['orden', 'nombre']
    
    def __str__(self):
        return self.nombre


class Percha(models.Model):
    """Perchas dentro de cada sección"""
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, related_name='perchas')
    nombre = models.CharField(max_length=50)  # Ej: P1, P2, Percha A, etc.
    descripcion = models.TextField(null=True, blank=True)
    filas = models.PositiveIntegerField(default=5, help_text='Número de filas en la percha')
    columnas = models.PositiveIntegerField(default=10, help_text='Número de columnas en la percha')
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Percha"
        verbose_name_plural = "Perchas"
        ordering = ['seccion', 'nombre']
        unique_together = ['seccion', 'nombre']
    
    def __str__(self):
        return f"{self.seccion.nombre} - {self.nombre}"
    
    @property
    def capacidad_total(self):
        """Capacidad total de productos en la percha"""
        return self.filas * self.columnas
    
    @property
    def productos_ubicados(self):
        """Número de productos actualmente ubicados"""
        return self.ubicaciones.filter(activo=True).count()
    
    @property
    def espacios_disponibles(self):
        """Espacios disponibles en la percha"""
        return self.capacidad_total - self.productos_ubicados


class UbicacionProducto(models.Model):
    """Ubicación específica de un producto en una percha"""
    producto_id = models.IntegerField(help_text='ID del producto en la tabla productos')
    percha = models.ForeignKey(Percha, on_delete=models.CASCADE, related_name='ubicaciones')
    fila = models.PositiveIntegerField()
    columna = models.PositiveIntegerField()
    observaciones = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_ubicacion = models.DateTimeField(auto_now_add=True)
    usuario_ubicacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Ubicación de Producto"
        verbose_name_plural = "Ubicaciones de Productos"
        unique_together = ['percha', 'fila', 'columna']
        ordering = ['percha', 'fila', 'columna']
    
    def __str__(self):
        try:
            producto = Producto.objects.get(id=self.producto_id)
            return f"{producto.nombre} - {self.percha} (F{self.fila}C{self.columna})"
        except Producto.DoesNotExist:
            return f"Producto ID {self.producto_id} - {self.percha} (F{self.fila}C{self.columna})"
    
    @property
    def producto(self):
        """Obtener el objeto producto"""
        try:
            return Producto.objects.get(id=self.producto_id)
        except Producto.DoesNotExist:
            return None
    
    @property
    def ubicacion_completa(self):
        """Descripción completa de la ubicación"""
        return f"{self.percha.seccion.nombre} > {self.percha.nombre} > Fila {self.fila}, Columna {self.columna}"
    
    @property
    def codigo_ubicacion(self):
        """Código corto de ubicación para mostrar en POS"""
        return f"{self.percha.nombre}-F{self.fila}C{self.columna}"


# Modelo para códigos alternativos de productos
class CodigoAlternativo(models.Model):
    """Códigos alternativos de proveedores vinculados a un producto maestro"""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='codigos_alternativos', db_column='idProducto')
    codigo = models.CharField(max_length=100, unique=True, help_text="Código del proveedor")
    nombre_proveedor = models.CharField(max_length=200, db_column='nombreProveedor', help_text="Nombre del producto según el proveedor", null=True, blank=True)
    id_proveedor = models.IntegerField(null=True, blank=True, db_column='idProveedor', help_text="ID del proveedor de origen")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column='fechaCreacion')
    
    class Meta:
        db_table = 'codigos_alternativos'
        managed = True
        verbose_name = "Código Alternativo"
        verbose_name_plural = "Códigos Alternativos"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.codigo} → {self.producto.nombre}"


# Mantener los modelos antiguos para compatibilidad (puedes eliminarlos después)
class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    abreviacion = models.CharField(max_length=10, unique=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.abreviacion})"
