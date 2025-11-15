from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from productos.models import Producto
from clientes.models import Cliente
from caja.models import CierreCaja


# Modelos para las tablas reales de la base de datos
class FacturaVenta(models.Model):
    """Modelo para la tabla facturas_venta existente"""
    ESTADO_CHOICES = [
        ('EMITIDA', 'Emitida'),
        ('PAGADA', 'Pagada'),
        ('ANULADA', 'Anulada'),
    ]
    
    idFactura = models.AutoField(primary_key=True, db_column='id')  # Campo ID principal
    idCliente = models.IntegerField(db_column='idCliente')
    idUsuario = models.IntegerField(db_column='idUsuario')  
    idCierreCaja = models.IntegerField(null=True, blank=True, db_column='idCierreCaja')
    numeroFactura = models.CharField(max_length=50, unique=True, db_column='numeroFactura')
    fechaEmision = models.DateTimeField(db_column='fechaEmision')
    subtotal = models.DecimalField(max_digits=12, decimal_places=4, db_column='subtotal')
    descuento = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='descuento')
    iva = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='iva')
    total = models.DecimalField(max_digits=12, decimal_places=4, db_column='total')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='EMITIDA', db_column='estado')
    creadoPor = models.IntegerField(db_column='creadoPor')
    creadoDate = models.DateTimeField(db_column='creadoDate')
    anulado = models.BooleanField(default=False, db_column='anulado')
    numeroAutorizacion = models.CharField(max_length=50, null=True, blank=True, db_column='numeroAutorizacion')
    
    class Meta:
        db_table = 'facturas_venta'
        managed = False
        verbose_name = "Factura de Venta"
        verbose_name_plural = "Facturas de Venta"
        ordering = ['-fechaEmision']
    
    def __str__(self):
        return f"Factura {self.numeroFactura}"
    
    @property
    def cliente(self):
        """Obtener objeto cliente"""
        try:
            return Cliente.objects.get(id=self.idCliente)
        except Cliente.DoesNotExist:
            return None
    
    @property
    def usuario(self):
        """Obtener objeto usuario"""
        try:
            return User.objects.get(id=self.idUsuario)
        except User.DoesNotExist:
            return None


class FacturaVentaDetalle(models.Model):
    """Modelo para la tabla facturas_venta_detalle existente"""
    
    id = models.AutoField(primary_key=True, db_column='id')  # Campo ID principal de la tabla
    idFacturaVenta = models.IntegerField(db_column='idFacturaVenta')
    idProducto = models.IntegerField(db_column='idProducto')
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, db_column='cantidad')
    precioUnitario = models.DecimalField(max_digits=12, decimal_places=4, db_column='precioUnitario')
    descuentoValor = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='descuentoValor')
    ivaValor = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='ivaValor')
    total = models.DecimalField(max_digits=12, decimal_places=4, db_column='total')
    productoNombre = models.CharField(max_length=300, null=True, blank=True, db_column='productoNombre')
    
    class Meta:
        db_table = 'facturas_venta_detalle'
        managed = False
        verbose_name = "Detalle de Factura de Venta"
        verbose_name_plural = "Detalles de Facturas de Venta"
    
    def __str__(self):
        return f"{self.productoNombre or self.idProducto} x {self.cantidad}"
    
    @property
    def factura_venta(self):
        """Obtener factura de venta"""
        try:
            return FacturaVenta.objects.get(id=self.idFacturaVenta)
        except FacturaVenta.DoesNotExist:
            return None
    
    @property
    def producto(self):
        """Obtener objeto producto"""
        try:
            return Producto.objects.get(id=self.idProducto)
        except Producto.DoesNotExist:
            return None


# Modelos originales de Django (mantenidos para compatibilidad)
class Venta(models.Model):
    TIPO_PAGO = (
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('credito', 'Crédito'),
        ('mixto', 'Mixto'),
    )
    
    ESTADO_VENTA = (
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('anulada', 'Anulada'),
        ('parcial', 'Parcialmente Pagada'),
    )
    
    numero_factura = models.CharField(max_length=50, unique=True)
    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='ventas')
    vendedor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ventas_realizadas')
    # Referencia directa al ID de caja en lugar de ForeignKey
    idCaja = models.IntegerField(null=True, blank=True)
    
    # Totales
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Pagos
    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO, default='efectivo')
    estado = models.CharField(max_length=20, choices=ESTADO_VENTA, default='pendiente')
    
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Factura {self.numero_factura} - {self.cliente.nombre_completo if self.cliente else 'Cliente Genérico'}"
    
    @classmethod
    def generar_numero_factura(cls):
        """Generar número de factura automático"""
        from datetime import date
        today = date.today()
        
        # Formato: FAC-YYYYMMDD-0001
        prefix = f"FAC-{today.strftime('%Y%m%d')}"
        
        # Buscar el último número del día
        ultimo = cls.objects.filter(
            numero_factura__startswith=prefix
        ).order_by('-numero_factura').first()
        
        if ultimo:
            # Extraer el número secuencial
            ultimo_num = int(ultimo.numero_factura.split('-')[-1])
            nuevo_num = ultimo_num + 1
        else:
            nuevo_num = 1
            
        return f"{prefix}-{nuevo_num:04d}"
    
    @property
    def saldo_pendiente(self):
        pagos_realizados = self.pagos.aggregate(total=models.Sum('monto'))['total'] or 0
        return self.total - pagos_realizados
    
    def calcular_totales(self):
        detalles = self.detalles.all()
        self.subtotal = sum(detalle.subtotal for detalle in detalles)
        self.impuesto = sum(detalle.impuesto for detalle in detalles)
        self.total = self.subtotal + self.impuesto - self.descuento
        self.save()


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_linea = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        unique_together = ['venta', 'producto']
    
    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"
    
    @property
    def subtotal(self):
        return (self.cantidad * self.precio_unitario) - self.descuento_linea
    
    @property
    def impuesto(self):
        if self.producto.aplica_iva:
            return self.subtotal * Decimal('0.15')  # IVA 15%
        return Decimal('0.00')
    
    @property
    def total_linea(self):
        return self.subtotal + self.impuesto


class PagoVenta(models.Model):
    METODO_PAGO = (
        ('efectivo', 'Efectivo'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
        ('transferencia', 'Transferencia Bancaria'),
        ('cheque', 'Cheque'),
    )
    
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO)
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    referencia = models.CharField(max_length=100, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = "Pago de Venta"
        verbose_name_plural = "Pagos de Ventas"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.get_metodo_pago_display()} - L. {self.monto}"


# Comentar temporalmente los modelos de devoluciones para evitar errores
# Estos se pueden reactivar después de crear las tablas correctamente

# class DevolucionVenta(models.Model):
#     MOTIVO_CHOICES = (
#         ('defectuoso', 'Producto Defectuoso'),
#         ('cambio', 'Cambio de Producto'),
#         ('error', 'Error en Venta'),
#         ('cliente', 'Solicitud del Cliente'),
#     )
    
#     # Guardar solo el ID de la factura (no ForeignKey porque es tabla externa)
#     id_factura_original = models.IntegerField(help_text="ID de la factura original")
#     numero_devolucion = models.CharField(max_length=50, unique=True)
#     fecha = models.DateTimeField(auto_now_add=True)
#     motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)
#     observaciones = models.TextField(blank=True)
#     usuario = models.ForeignKey(User, on_delete=models.PROTECT)
#     total_devolucion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
#     class Meta:
#         verbose_name = "Devolución de Venta"
#         verbose_name_plural = "Devoluciones de Ventas"
#         ordering = ['-fecha']
    
#     def __str__(self):
#         try:
#             factura = FacturaVenta.objects.get(idFactura=self.id_factura_original)
#             return f"Devolución {self.numero_devolucion} - {factura.numeroFactura}"
#         except FacturaVenta.DoesNotExist:
#             return f"Devolución {self.numero_devolucion} - Factura {self.id_factura_original}"
    
#     @property
#     def factura_original(self):
#         """Obtener la factura original asociada"""
#         try:
#             return FacturaVenta.objects.get(idFactura=self.id_factura_original)
#         except FacturaVenta.DoesNotExist:
#             return None
    
    class Meta:
        verbose_name = "Devolución de Venta"
        verbose_name_plural = "Devoluciones de Ventas"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Devolución {self.numero_devolucion} - {self.factura_original.numeroFactura}"
    
    @classmethod
    def generar_numero_devolucion(cls):
        """Generar número de devolución automático"""
        from datetime import date
        today = date.today()
        
        # Formato: DEV-YYYYMMDD-0001
        prefix = f"DEV-{today.strftime('%Y%m%d')}"
        
        # Buscar el último número del día
        ultimo = cls.objects.filter(
            numero_devolucion__startswith=prefix
        ).order_by('-numero_devolucion').first()
        
        if ultimo:
            # Extraer el número secuencial
            ultimo_num = int(ultimo.numero_devolucion.split('-')[-1])
            nuevo_num = ultimo_num + 1
        else:
            nuevo_num = 1
            
        return f"{prefix}-{nuevo_num:04d}"


# Comentar temporalmente los modelos de devoluciones para evitar errores
# Estos se pueden reactivar después de crear las tablas correctamente

# class DetalleDevolucion(models.Model):
#     devolucion = models.ForeignKey(DevolucionVenta, on_delete=models.CASCADE, related_name='detalles')
#     # Guardar solo el ID del detalle de factura (no ForeignKey porque es tabla externa)
#     id_detalle_factura = models.IntegerField(help_text="ID del detalle de factura original")
#     cantidad_devuelta = models.PositiveIntegerField()
    
#     class Meta:
#         verbose_name = "Detalle de Devolución"
#         verbose_name_plural = "Detalles de Devoluciones"
    
#     def __str__(self):
#         try:
#             detalle_factura = FacturaVentaDetalle.objects.get(id=self.id_detalle_factura)
#             producto_nombre = detalle_factura.productoNombre or f"Producto {detalle_factura.idProducto}"
#             return f"{producto_nombre} x {self.cantidad_devuelta}"
#         except FacturaVentaDetalle.DoesNotExist:
#             return f"Detalle {self.id_detalle_factura} x {self.cantidad_devuelta}"
    
#     @property
#     def detalle_factura(self):
#         """Obtener el detalle de factura asociado"""
#         try:
#             return FacturaVentaDetalle.objects.get(id=self.id_detalle_factura)
#         except FacturaVentaDetalle.DoesNotExist:
#             return None
    
#     @property
#     def total_devuelto(self):
#         detalle = self.detalle_factura
#         if detalle:
#             return self.cantidad_devuelta * detalle.precioUnitario
#         return 0
