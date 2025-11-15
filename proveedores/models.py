from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Proveedor(models.Model):
    """Modelo para la tabla proveedores existente"""
    
    ruc = models.CharField(max_length=13, unique=True, db_column='ruc')
    razon_social = models.CharField(max_length=200, db_column='razonSocial')
    nombre_comercial = models.CharField(max_length=200, blank=True, null=True, db_column='nombreComercial')
    direccion = models.TextField(blank=True, null=True, db_column='direccion')
    telefono = models.CharField(max_length=20, blank=True, null=True, db_column='telefono')
    email = models.CharField(max_length=100, blank=True, null=True, db_column='email')
    estado = models.BooleanField(default=True, db_column='estado')
    anulado = models.BooleanField(default=False, db_column='anulado')
    
    # Campos de auditoría
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='proveedores_creados',
        db_column='creadoPor'
    )
    creado_date = models.DateTimeField(auto_now_add=True, db_column='creadoDate')
    editado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='proveedores_editados',
        db_column='editadoPor'
    )
    editado_date = models.DateTimeField(auto_now=True, db_column='editadoDate')
    
    class Meta:
        managed = False
        db_table = 'proveedores'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
    
    def __str__(self):
        return self.nombre_comercial or self.razon_social
    
    @property
    def nombre(self):
        """Propiedad para compatibilidad - devuelve nombre comercial o razón social"""
        return self.nombre_comercial or self.razon_social
    
    @property
    def whatsapp_formateado(self):
        """Devuelve el número de teléfono formateado para WhatsApp (solo dígitos)"""
        if self.telefono:
            return ''.join(filter(str.isdigit, self.telefono))
        return ''


class OrdenCompraProveedor(models.Model):
    """Modelo para órdenes de compra a proveedores"""
    
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('ENVIADA', 'Enviada'),
        ('CONFIRMADA', 'Confirmada'),
        ('RECIBIDA', 'Recibida'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    numero_orden = models.CharField(max_length=20, unique=True, db_column='numero_orden')
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='ordenes_compra',
        db_column='proveedor_id'
    )
    fecha_orden = models.DateTimeField(auto_now_add=True, db_column='fecha_orden')
    fecha_entrega_estimada = models.DateField(null=True, blank=True, db_column='fecha_entrega_estimada')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='subtotal')
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='iva')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total')
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR', db_column='estado')
    
    observaciones = models.TextField(blank=True, null=True, db_column='observaciones')
    
    # Campos WhatsApp
    enviada_whatsapp = models.BooleanField(default=False, db_column='enviada_whatsapp')
    fecha_envio_whatsapp = models.DateTimeField(null=True, blank=True, db_column='fecha_envio_whatsapp')
    
    anulado = models.BooleanField(default=False, db_column='anulado')
    
    # Campos de auditoría - mantener como IntegerField pero con métodos helper
    creado_por = models.IntegerField(null=True, db_column='creado_por')
    creado_date = models.DateTimeField(auto_now_add=True, db_column='creado_date')
    editado_por = models.IntegerField(null=True, blank=True, db_column='editado_por')
    editado_date = models.DateTimeField(auto_now=True, db_column='editado_date')
    
    class Meta:
        managed = False
        db_table = 'ordenes_compra_proveedor'
        verbose_name = 'Orden de Compra'
        verbose_name_plural = 'Órdenes de Compra'
        ordering = ['-fecha_orden']
    
    def __str__(self):
        return f"{self.numero_orden} - {self.proveedor.nombre}"
    
    def get_creado_por_user(self):
        """Obtener el objeto User que creó la orden"""
        if self.creado_por:
            try:
                return User.objects.get(id=self.creado_por)
            except User.DoesNotExist:
                return None
        return None
    
    def get_editado_por_user(self):
        """Obtener el objeto User que editó la orden"""
        if self.editado_por:
            try:
                return User.objects.get(id=self.editado_por)
            except User.DoesNotExist:
                return None
        return None
    
    def calcular_totales(self):
        """Calcula los totales de la orden basándose en los detalles"""
        from django.db.models import Sum, F
        
        totales = self.detalles.aggregate(
            total_subtotal=Sum(F('cantidad') * F('precio_unitario'))
        )
        
        self.subtotal = totales['total_subtotal'] or Decimal('0.00')
        self.iva = self.subtotal * Decimal('0.15')  # IVA 15%
        self.total = self.subtotal + self.iva
        self.save()


class DetalleOrdenProveedor(models.Model):
    """Modelo para el detalle de órdenes de compra"""
    
    orden = models.ForeignKey(
        OrdenCompraProveedor,
        on_delete=models.CASCADE,
        related_name='detalles',
        db_column='orden_id'
    )
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.PROTECT,
        db_column='producto_id'
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, db_column='precio_unitario')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        managed = False
        db_table = 'detalles_orden_proveedor'
        verbose_name = 'Detalle de Orden'
        verbose_name_plural = 'Detalles de Órdenes'
        unique_together = [['orden', 'producto']]
    
    def __str__(self):
        return f"{self.orden.numero_orden} - {self.producto.nombre}"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal automáticamente
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
