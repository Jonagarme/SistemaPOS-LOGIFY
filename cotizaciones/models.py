from django.db import models
from django.contrib.auth.models import User
from clientes.models import Cliente
from productos.models import Producto
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class Cotizacion(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
        ('vencida', 'Vencida'),
        ('convertida', 'Convertida a Venta'),
    ]
    
    numero = models.CharField(max_length=20, unique=True, verbose_name='Número de Cotización')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name='Cliente')
    referencia_cliente = models.CharField(max_length=100, blank=True, null=True, verbose_name='Referencia del Cliente')
    fecha = models.DateField(verbose_name='Fecha de Cotización', help_text='Fecha de emisión de la cotización', default=timezone.now)
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_vencimiento = models.DateField(verbose_name='Fecha de Vencimiento')
    validez_dias = models.IntegerField(default=15, verbose_name='Validez en Días')
    
    # Estados
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador', verbose_name='Estado')
    
    # Totales
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Subtotal')
    descuento_global = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Descuento Global %')
    impuesto = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Impuesto (15%)')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Total')
    
    # Información adicional
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    condiciones = models.TextField(blank=True, null=True, verbose_name='Términos y Condiciones')
    
    # Metadatos
    usuario_creacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Creado por')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')
    
    # Conversión a venta
    venta_relacionada = models.ForeignKey('ventas.Venta', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Venta Generada')
    
    class Meta:
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Cotización {self.numero} - {self.cliente.nombre}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            # Generar número de cotización automáticamente
            ultimo_numero = Cotizacion.objects.filter(
                numero__startswith='COT-'
            ).order_by('-numero').first()
            
            if ultimo_numero:
                try:
                    ultimo_num = int(ultimo_numero.numero.split('-')[1])
                    nuevo_num = ultimo_num + 1
                except (ValueError, IndexError):
                    nuevo_num = 1
            else:
                nuevo_num = 1
            
            self.numero = f'COT-{nuevo_num:06d}'
        
        # Calcular totales
        self.calcular_totales()
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        """Calcula los totales de la cotización"""
        detalles = self.detallecotizacion_set.all()
        self.subtotal = sum(detalle.total for detalle in detalles) - self.descuento
        self.impuesto = self.subtotal * Decimal('0.15')  # 15% ISV
        self.total = self.subtotal + self.impuesto
    
    def puede_convertir_a_venta(self):
        """Verifica si la cotización puede convertirse a venta"""
        return self.estado in ['enviada', 'aceptada'] and not self.venta_relacionada
    
    def esta_vencida(self):
        """Verifica si la cotización está vencida"""
        from django.utils import timezone
        return timezone.now().date() > self.fecha_vencimiento


class DetalleCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, verbose_name='Cotización')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, verbose_name='Producto')
    cantidad = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Cantidad')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio Unitario')
    descuento_linea = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Descuento')
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total')
    
    # Información adicional del producto en el momento de la cotización
    descripcion_producto = models.TextField(blank=True, verbose_name='Descripción')
    
    class Meta:
        verbose_name = 'Detalle de Cotización'
        verbose_name_plural = 'Detalles de Cotización'
        unique_together = ['cotizacion', 'producto']
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} unidades"
    
    def save(self, *args, **kwargs):
        # Calcular total
        subtotal = self.precio_unitario * self.cantidad
        self.total = subtotal - self.descuento_linea
        
        # Guardar descripción del producto
        if not self.descripcion_producto:
            self.descripcion_producto = self.producto.descripcion or self.producto.nombre
        
        super().save(*args, **kwargs)
        
        # Actualizar totales de la cotización
        self.cotizacion.calcular_totales()
        self.cotizacion.save()