from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from productos.models import Producto
from proveedores.models import Proveedor
from django.utils import timezone


# Nuevo modelo para la tabla kardex_movimientos que ya existe en la BD
class KardexMovimiento(models.Model):
    """Modelo para la tabla kardex_movimientos existente"""
    
    idProducto = models.IntegerField(db_column='idProducto')
    # Nueva columna para identificar la ubicación del movimiento
    # Requiere agregar en MySQL: ALTER TABLE kardex_movimientos ADD COLUMN idUbicacion INT NULL;
    idUbicacion = models.IntegerField(db_column='idUbicacion', null=True, blank=True,
                                      help_text='ID de la ubicación donde ocurrió el movimiento')
    fecha = models.DateTimeField(db_column='fecha', default=timezone.now)
    tipoMovimiento = models.CharField(max_length=100, db_column='tipoMovimiento',
                                    help_text='Ej: VENTA, COMPRA, AJUSTE INGRESO, AJUSTE EGRESO, DEVOLUCIÓN, TRANSFERENCIA')
    detalle = models.CharField(max_length=300, db_column='detalle',
                             help_text='Ej: Factura Venta N° 001-001-12345')
    ingreso = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, db_column='ingreso')
    egreso = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, db_column='egreso')
    saldo = models.DecimalField(max_digits=12, decimal_places=2, db_column='saldo',
                               help_text='Saldo del producto DESPUÉS de este movimiento en esta ubicación')
    
    class Meta:
        db_table = 'kardex_movimientos'
        managed = False  # Django no administrará esta tabla
        ordering = ['-fecha', '-id']
        verbose_name = "Movimiento Kardex"
        verbose_name_plural = "Movimientos Kardex"
    
    def __str__(self):
        return f"Producto {self.idProducto} - {self.tipoMovimiento} - {self.detalle[:50]}"
    
    @property
    def producto(self):
        """Propiedad para obtener el producto relacionado"""
        try:
            return Producto.objects.get(id=self.idProducto)
        except Producto.DoesNotExist:
            return None
    
    @property
    def movimiento_neto(self):
        """Retorna el movimiento neto (ingreso - egreso)"""
        return self.ingreso - self.egreso


# Nuevo modelo para ubicaciones/sucursales
class Ubicacion(models.Model):
    """Modelo para manejar diferentes ubicaciones: sucursales, bodegas, etc."""
    TIPO_UBICACION = (
        ('sucursal', 'Sucursal'),
        ('bodega', 'Bodega'),
        ('almacen', 'Almacén'),
        ('deposito', 'Depósito'),
    )
    
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=15, choices=TIPO_UBICACION, default='sucursal')
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    responsable = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    es_principal = models.BooleanField(default=False)  # Ubicación principal del sistema
    
    # Campos de auditoría
    creadoPor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ubicaciones_creadas')
    creadoDate = models.DateTimeField(auto_now_add=True)
    editadoPor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ubicaciones_editadas')
    editadoDate = models.DateTimeField(auto_now=True)
    anulado = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# Nuevo modelo para Órdenes de Compra
class OrdenCompra(models.Model):
    """Modelo para generar órdenes de compra automáticas o manuales"""
    ESTADO_ORDEN = (
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('confirmada', 'Confirmada'),
        ('recibida_parcial', 'Recibida Parcial'),
        ('recibida_completa', 'Recibida Completa'),
        ('cancelada', 'Cancelada'),
    )
    
    PRIORIDAD_CHOICES = (
        ('baja', 'Baja'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    )
    
    numero_orden = models.CharField(max_length=50, unique=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes_compra_inventario')
    ubicacion_destino = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='ordenes_recibidas')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_entrega_esperada = models.DateField(null=True, blank=True)
    fecha_entrega_real = models.DateField(null=True, blank=True)
    
    estado = models.CharField(max_length=20, choices=ESTADO_ORDEN, default='borrador')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='normal')
    
    # Totales
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    observaciones = models.TextField(blank=True)
    generada_automaticamente = models.BooleanField(default=False)
    usuario_creacion = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ordenes_creadas')
    usuario_envio = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='ordenes_enviadas')
    
    # Campos de auditoría adicionales
    creadoPor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ordenes_auditoria_creadas', null=True, blank=True)
    creadoDate = models.DateTimeField(auto_now_add=True)
    editadoPor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_auditoria_editadas')
    editadoDate = models.DateTimeField(auto_now=True)
    anulado = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Orden de Compra"
        verbose_name_plural = "Órdenes de Compra"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"OC {self.numero_orden} - {self.proveedor.nombre_comercial}"
    
    def marcar_como_enviada(self, usuario):
        """Marca la orden como enviada"""
        self.estado = 'enviada'
        self.fecha_envio = timezone.now()
        self.usuario_envio = usuario
        self.save()
    
    @property
    def puede_ser_enviada(self):
        return self.estado == 'borrador' and self.detalles.exists()
    
    @property
    def dias_desde_envio(self):
        if self.fecha_envio:
            return (timezone.now().date() - self.fecha_envio.date()).days
        return None


class DetalleOrdenCompra(models.Model):
    """Detalle de productos en una orden de compra"""
    orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_solicitada = models.PositiveIntegerField()
    cantidad_recibida = models.PositiveIntegerField(default=0)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    descuento_linea = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Información adicional
    stock_actual = models.PositiveIntegerField(default=0)  # Stock al momento de crear la orden
    stock_minimo = models.PositiveIntegerField(default=0)  # Stock mínimo configurado
    motivo_solicitud = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Detalle de Orden de Compra"
        verbose_name_plural = "Detalles de Órdenes de Compra"
        unique_together = ['orden', 'producto']
    
    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad_solicitada}"
    
    @property
    def subtotal(self):
        return (self.cantidad_solicitada * self.precio_unitario) - self.descuento_linea
    
    @property
    def cantidad_pendiente(self):
        return max(0, self.cantidad_solicitada - self.cantidad_recibida)
    
    @property
    def esta_completo(self):
        return self.cantidad_recibida >= self.cantidad_solicitada


# Nuevo modelo para Transferencias de Stock
class TransferenciaStock(models.Model):
    """Modelo para transferencias de inventario entre ubicaciones"""
    ESTADO_TRANSFERENCIA = (
        ('guardado', 'Guardado'),  # Editable, NO reserva stock
        ('transferido', 'Transferido'),  # Reserva stock, en empaque/transporte
        ('procesado', 'Procesado'),  # Inventario movido, transferencia completada
        ('cancelada', 'Cancelada'),
    )
    
    TIPO_TRANSFERENCIA = (
        ('manual', 'Manual'),
        ('reposicion', 'Reposición Automática'),
        ('redistribucion', 'Redistribución'),
        ('emergencia', 'Emergencia'),
    )
    
    numero_transferencia = models.CharField(max_length=50, unique=True)
    ubicacion_origen = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='transferencias_enviadas')
    ubicacion_destino = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='transferencias_recibidas')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    
    estado = models.CharField(max_length=15, choices=ESTADO_TRANSFERENCIA, default='guardado')
    tipo = models.CharField(max_length=15, choices=TIPO_TRANSFERENCIA, default='manual')
    
    observaciones = models.TextField(blank=True)
    motivo = models.CharField(max_length=200, blank=True)
    
    usuario_creacion = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transferencias_creadas')
    usuario_envio = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='transferencias_enviadas')
    usuario_recepcion = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='transferencias_recibidas')
    
    # Campos de auditoría adicionales
    creadoPor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transferencias_auditoria_creadas', null=True, blank=True)
    creadoDate = models.DateTimeField(auto_now_add=True)
    editadoPor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='transferencias_auditoria_editadas')
    editadoDate = models.DateTimeField(auto_now=True)
    anulado = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Transferencia de Stock"
        verbose_name_plural = "Transferencias de Stock"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"TR {self.numero_transferencia} - {self.ubicacion_origen} → {self.ubicacion_destino}"
    
    def enviar(self, usuario):
        """
        Marca la transferencia como 'transferido' y RESERVA (no descuenta) stock
        Estado: guardado → transferido
        """
        if self.estado != 'guardado':
            raise ValueError(f'No se puede enviar una transferencia en estado {self.estado}. Debe estar en estado "guardado".')
        
        # Validar que hay productos
        if not self.detalles.exists():
            raise ValueError('La transferencia no tiene productos agregados.')
        
        # RESERVAR stock en cada lote (NO descontar aún)
        with transaction.atomic():
            for detalle in self.detalles.all():
                # Validar que tenga lote asignado
                if not detalle.lote:
                    raise ValueError(f'El producto {detalle.producto.nombre} no tiene un lote asignado.')
                
                # Validar que el lote pertenece a la ubicación origen
                if detalle.lote.ubicacion_id != self.ubicacion_origen_id:
                    raise ValueError(f'El lote {detalle.lote.numero_lote} no pertenece a la ubicación origen.')
                
                # Guardar stock antes del movimiento
                detalle.stock_origen_antes = detalle.lote.cantidad_disponible
                detalle.save()
                
                # RESERVAR cantidad en el lote (NO descontar)
                try:
                    detalle.lote.reservar_cantidad(
                        cantidad=detalle.cantidad,
                        detalle=f'Transferencia {self.numero_transferencia}'
                    )
                except ValueError as e:
                    raise ValueError(f'Error al reservar {detalle.producto.nombre}: {str(e)}')
            
            # Actualizar estado de la transferencia
            self.estado = 'transferido'
            self.fecha_envio = timezone.now()
            self.usuario_envio = usuario
            self.save()
    
    def procesar(self, usuario, cantidades_recibidas=None):
        """
        Procesa la transferencia: descuenta stock del origen y suma al destino
        Estado: transferido → procesado
        
        REGLA DE SEGURIDAD: El usuario que procesa NO puede ser el mismo que envió
        
        Args:
            usuario: Usuario que recibe/procesa
            cantidades_recibidas: Dict con {detalle_id: cantidad_recibida} (opcional)
        """
        if self.estado != 'transferido':
            raise ValueError(f'No se puede procesar una transferencia en estado {self.estado}. Debe estar en estado "transferido".')
        
        # VALIDACIÓN CRÍTICA: Usuario receptor ≠ usuario envío
        if self.usuario_envio and usuario.id == self.usuario_envio.id:
            raise ValueError(
                f'ERROR DE SEGURIDAD: El usuario que transfiere ({self.usuario_envio.username}) '
                f'no puede ser el mismo que procesa la transferencia. '
                f'Debe ser procesada por un usuario diferente para garantizar auditoría.'
            )
        
        with transaction.atomic():
            for detalle in self.detalles.all():
                # Determinar cantidad a recibir
                cantidad_a_recibir = detalle.cantidad
                if cantidades_recibidas and detalle.id in cantidades_recibidas:
                    cantidad_a_recibir = cantidades_recibidas[detalle.id]
                
                # 1. DESCONTAR del lote origen y liberar reserva
                detalle.lote.descontar_cantidad(
                    cantidad=cantidad_a_recibir,
                    detalle=f'Transferencia {self.numero_transferencia} procesada'
                )
                detalle.lote.liberar_reserva(cantidad=cantidad_a_recibir)
                
                # 2. CREAR o ACTUALIZAR lote en destino
                # Buscar si ya existe el mismo lote en destino
                lote_destino, created = LoteProducto.objects.get_or_create(
                    producto=detalle.producto,
                    ubicacion=self.ubicacion_destino,
                    numero_lote=detalle.lote.numero_lote,
                    fecha_caducidad=detalle.lote.fecha_caducidad,
                    defaults={
                        'creadoPor': usuario,
                        'fecha_ingreso': timezone.now().date(),
                        'fecha_creacion': detalle.lote.fecha_creacion,
                        'cantidad_inicial': cantidad_a_recibir,
                        'cantidad_disponible': cantidad_a_recibir,
                        'proveedor': detalle.lote.proveedor,
                        'costo_unitario': detalle.lote.costo_unitario,
                    }
                )
                
                if not created:
                    # Si ya existía, solo sumar la cantidad
                    lote_destino.cantidad_disponible += Decimal(str(cantidad_a_recibir))
                    lote_destino.save()
                
                # Guardar información en el detalle
                detalle.stock_destino_antes = lote_destino.cantidad_disponible - Decimal(str(cantidad_a_recibir))
                detalle.cantidad_recibida = cantidad_a_recibir
                
                # Aplicar cambio de precio si corresponde
                if detalle.cambio_precio and detalle.precio_destino != detalle.precio_origen:
                    # Aquí podrías actualizar el precio en StockUbicacion o en el producto
                    # Por ahora solo lo registramos en el detalle
                    detalle.observaciones += f'\nPrecio cambiado de ${detalle.precio_origen} a ${detalle.precio_destino}'
                
                detalle.save()
                
                # 3. Registrar en kardex
                # Salida en origen
                KardexMovimiento.objects.create(
                    idProducto=detalle.producto.id,
                    idUbicacion=self.ubicacion_origen.id,
                    tipoMovimiento='TRANSFERENCIA SALIDA',
                    detalle=f'Transfer. {self.numero_transferencia} → {self.ubicacion_destino.nombre} (Lote: {detalle.lote.numero_lote})',
                    egreso=cantidad_a_recibir,
                    ingreso=0,
                    saldo=detalle.lote.cantidad_disponible
                )
                
                # Entrada en destino
                KardexMovimiento.objects.create(
                    idProducto=detalle.producto.id,
                    idUbicacion=self.ubicacion_destino.id,
                    tipoMovimiento='TRANSFERENCIA ENTRADA',
                    detalle=f'Transfer. {self.numero_transferencia} ← {self.ubicacion_origen.nombre} (Lote: {detalle.lote.numero_lote})',
                    ingreso=cantidad_a_recibir,
                    egreso=0,
                    saldo=lote_destino.cantidad_disponible
                )
            
            # Actualizar estado de la transferencia
            self.estado = 'procesado'
            self.fecha_recepcion = timezone.now()
            self.usuario_recepcion = usuario
            self.save()
    
    @property
    def total_productos(self):
        return self.detalles.count()
    
    @property
    def total_cantidad(self):
        return sum(detalle.cantidad for detalle in self.detalles.all())


class LoteProducto(models.Model):
    """Modelo para gestión de lotes y trazabilidad de productos"""
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='lotes')
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='lotes')
    
    numero_lote = models.CharField(max_length=100, help_text='Número de lote del fabricante')
    fecha_ingreso = models.DateField(default=timezone.now, help_text='Fecha de ingreso del lote al sistema')
    fecha_caducidad = models.DateField(help_text='Fecha de vencimiento del producto')
    fecha_creacion = models.DateField(null=True, blank=True, help_text='Fecha de fabricación (opcional)')
    
    cantidad_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cantidad_disponible = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cantidad_reservada = models.DecimalField(max_digits=12, decimal_places=2, default=0, 
                                            help_text='Cantidad reservada en transferencias pendientes')
    
    # Información adicional
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    numero_factura = models.CharField(max_length=50, blank=True, help_text='Factura de compra asociada')
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)
    
    # Campos de auditoría
    creadoPor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='lotes_creados')
    creadoDate = models.DateTimeField(auto_now_add=True)
    editadoPor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes_editados')
    editadoDate = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Lote de Producto"
        verbose_name_plural = "Lotes de Productos"
        ordering = ['fecha_caducidad', 'fecha_ingreso']  # FEFO: First Expired, First Out
        unique_together = [['producto', 'ubicacion', 'numero_lote', 'fecha_caducidad']]
    
    def __str__(self):
        return f"{self.producto.nombre} - Lote {self.numero_lote} - Venc: {self.fecha_caducidad}"
    
    @property
    def dias_para_vencer(self):
        """Calcula los días que faltan para que venza el lote"""
        from datetime import date
        if self.fecha_caducidad:
            delta = self.fecha_caducidad - date.today()
            return delta.days
        return None
    
    @property
    def esta_vencido(self):
        """Verifica si el lote está vencido"""
        from datetime import date
        return self.fecha_caducidad < date.today()
    
    @property
    def por_vencer(self):
        """Verifica si el lote está por vencer (menos de 60 días)"""
        dias = self.dias_para_vencer
        return dias is not None and 0 < dias <= 60
    
    @property
    def cantidad_disponible_real(self):
        """Cantidad disponible menos la reservada"""
        return self.cantidad_disponible - self.cantidad_reservada
    
    def reservar_cantidad(self, cantidad, detalle=''):
        """Reserva cantidad para una transferencia"""
        if cantidad > self.cantidad_disponible_real:
            raise ValueError(f'No hay suficiente stock disponible en el lote. Disponible: {self.cantidad_disponible_real}, Solicitado: {cantidad}')
        
        self.cantidad_reservada += Decimal(str(cantidad))
        self.save()
    
    def liberar_reserva(self, cantidad):
        """Libera cantidad reservada"""
        self.cantidad_reservada = max(0, self.cantidad_reservada - Decimal(str(cantidad)))
        self.save()
    
    def descontar_cantidad(self, cantidad, detalle=''):
        """Descuenta cantidad del lote (usado en transferencias y ventas)"""
        if cantidad > self.cantidad_disponible:
            raise ValueError(f'No hay suficiente stock en el lote. Disponible: {self.cantidad_disponible}, Solicitado: {cantidad}')
        
        self.cantidad_disponible -= Decimal(str(cantidad))
        self.save()


class DetalleTransferencia(models.Model):
    """Detalle de productos en una transferencia"""
    transferencia = models.ForeignKey(TransferenciaStock, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    lote = models.ForeignKey(LoteProducto, on_delete=models.PROTECT, null=True, blank=True, 
                            help_text='Lote específico del cual se toma el producto')
    
    # Cantidades
    cantidad = models.PositiveIntegerField(help_text='Cantidad total en unidades')
    cantidad_cajas = models.PositiveIntegerField(default=0, help_text='Número de cajas completas')
    cantidad_fracciones = models.PositiveIntegerField(default=0, help_text='Cantidad de fracciones/unidades sueltas')
    unidades_por_caja = models.PositiveIntegerField(default=1, help_text='Unidades que contiene cada caja')
    cantidad_recibida = models.PositiveIntegerField(default=0)
    
    # Precios
    precio_origen = models.DecimalField(max_digits=12, decimal_places=2, default=0, 
                                       help_text='PVP en ubicación origen')
    precio_destino = models.DecimalField(max_digits=12, decimal_places=2, default=0, 
                                        help_text='PVP en ubicación destino (puede ser diferente)')
    cambio_precio = models.BooleanField(default=False, 
                                       help_text='Indica si se modificó el precio para el destino')
    
    # Información adicional
    stock_origen_antes = models.PositiveIntegerField(default=0)
    stock_destino_antes = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Detalle de Transferencia"
        verbose_name_plural = "Detalles de Transferencias"
        unique_together = ['transferencia', 'producto']
    
    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"
    
    @property
    def cantidad_pendiente(self):
        return max(0, self.cantidad - self.cantidad_recibida)


# Modelo para configurar niveles de stock automático
class ConfiguracionStock(models.Model):
    """Configuración de niveles de stock por producto y ubicación"""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='configuraciones_stock')
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.CASCADE, related_name='configuraciones_stock')
    
    stock_minimo = models.PositiveIntegerField(default=0)
    stock_maximo = models.PositiveIntegerField(default=0)
    punto_reorden = models.PositiveIntegerField(default=0)
    cantidad_reorden = models.PositiveIntegerField(default=0)
    
    # Configuración automática
    generar_orden_automatica = models.BooleanField(default=False)
    proveedor_preferido = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Campos de auditoría adicionales
    creadoPor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='config_stock_auditoria_creadas', null=True, blank=True)
    creadoDate = models.DateTimeField(auto_now_add=True)
    editadoPor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='config_stock_auditoria_editadas')
    editadoDate = models.DateTimeField(auto_now=True)
    anulado = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Configuración de Stock"
        verbose_name_plural = "Configuraciones de Stock"
        unique_together = ['producto', 'ubicacion']
        ordering = ['producto__nombre']
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.ubicacion.nombre}"
    
    @property
    def necesita_reorden(self):
        """Verifica si el producto necesita reorden basado en el stock actual"""
        # Aquí iría la lógica para verificar el stock actual vs punto de reorden
        return False  # Placeholder


class Compra(models.Model):
    TIPO_PAGO = (
        ('efectivo', 'Efectivo'),
        ('credito', 'Crédito'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
    )
    
    ESTADO_COMPRA = (
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('anulada', 'Anulada'),
        ('parcial', 'Parcialmente Pagada'),
    )
    
    numero_compra = models.CharField(max_length=50, unique=True)
    numero_factura_proveedor = models.CharField(max_length=100, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_factura = models.DateField()
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='compras')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='compras_realizadas')
    
    # Totales
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO, default='efectivo')
    estado = models.CharField(max_length=20, choices=ESTADO_COMPRA, default='pendiente')
    
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Compra {self.numero_compra} - {self.proveedor.nombre_comercial}"
    
    @property
    def saldo_pendiente(self):
        pagos_realizados = self.pagos.aggregate(total=models.Sum('monto'))['total'] or 0
        return self.total - pagos_realizados


class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_linea = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Detalle de Compra"
        verbose_name_plural = "Detalles de Compra"
        unique_together = ['compra', 'producto']
    
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


class PagoCompra(models.Model):
    METODO_PAGO = (
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia Bancaria'),
        ('cheque', 'Cheque'),
    )
    
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='pagos')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO)
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    referencia = models.CharField(max_length=100, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = "Pago de Compra"
        verbose_name_plural = "Pagos de Compras"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.get_metodo_pago_display()} - L. {self.monto}"


class Kardex(models.Model):
    TIPO_MOVIMIENTO = (
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste_entrada', 'Ajuste Entrada'),
        ('ajuste_salida', 'Ajuste Salida'),
        ('transferencia_entrada', 'Transferencia Entrada'),
        ('transferencia_salida', 'Transferencia Salida'),
    )
    
    CONCEPTO_CHOICES = (
        ('compra', 'Compra'),
        ('venta', 'Venta'),
        ('devolucion_compra', 'Devolución Compra'),
        ('devolucion_venta', 'Devolución Venta'),
        ('ajuste_inventario', 'Ajuste de Inventario'),
        ('transferencia', 'Transferencia'),
        ('inventario_inicial', 'Inventario Inicial'),
    )
    
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos_kardex')
    fecha = models.DateTimeField(auto_now_add=True)
    tipo_movimiento = models.CharField(max_length=25, choices=TIPO_MOVIMIENTO)
    concepto = models.CharField(max_length=25, choices=CONCEPTO_CHOICES)
    
    # Cantidades
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Saldos (se calculan automáticamente)
    saldo_cantidad = models.PositiveIntegerField(default=0)
    saldo_valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Referencias
    numero_documento = models.CharField(max_length=100, blank=True)
    observaciones = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = "Kardex"
        verbose_name_plural = "Movimientos Kardex"
        ordering = ['-fecha', '-id']
    
    def __str__(self):
        return f"{self.producto.codigo} - {self.get_tipo_movimiento_display()} - {self.cantidad}"
    
    @property
    def valor_total(self):
        return self.cantidad * self.precio_unitario


class AjusteInventario(models.Model):
    TIPO_AJUSTE = (
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    )
    
    MOTIVO_CHOICES = (
        ('faltante', 'Faltante'),
        ('sobrante', 'Sobrante'),
        ('dañado', 'Producto Dañado'),
        ('vencido', 'Producto Vencido'),
        ('error_sistema', 'Error del Sistema'),
        ('inventario_fisico', 'Inventario Físico'),
    )
    
    numero_ajuste = models.CharField(max_length=50, unique=True)
    fecha = models.DateTimeField(auto_now_add=True)
    tipo_ajuste = models.CharField(max_length=10, choices=TIPO_AJUSTE)
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)
    observaciones = models.TextField()
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = "Ajuste de Inventario"
        verbose_name_plural = "Ajustes de Inventario"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Ajuste {self.numero_ajuste} - {self.get_tipo_ajuste_display()}"


class DetalleAjuste(models.Model):
    ajuste = models.ForeignKey(AjusteInventario, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_anterior = models.PositiveIntegerField()
    cantidad_nueva = models.PositiveIntegerField()
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Detalle de Ajuste"
        verbose_name_plural = "Detalles de Ajustes"
        unique_together = ['ajuste', 'producto']
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad_anterior} → {self.cantidad_nueva}"
    
    @property
    def diferencia(self):
        return self.cantidad_nueva - self.cantidad_anterior


# ============================
# STOCK POR UBICACIÓN (SUCURSALES)
# ============================

class StockUbicacion(models.Model):
    """
    Modelo para manejar stock de productos por ubicación/sucursal.
    Permite que cada sucursal tenga su propio inventario independiente.
    """
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='stocks_por_ubicacion')
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.CASCADE, related_name='stocks_productos')
    
    # Stock actual en esta ubicación
    cantidad = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Cantidad disponible en esta ubicación'
    )
    
    # Configuración de niveles de stock por ubicación
    stock_minimo = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text='Nivel mínimo de stock para alertas'
    )
    stock_maximo = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text='Nivel máximo de stock recomendado'
    )
    punto_reorden = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text='Punto en el que se debe reordenar'
    )
    
    # Campos de auditoría
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    creadoPor = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='stocks_ubicacion_creados')
    creadoDate = models.DateTimeField(auto_now_add=True)
    editadoPor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stocks_ubicacion_editados')
    editadoDate = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Stock por Ubicación"
        verbose_name_plural = "Stocks por Ubicación"
        unique_together = ['producto', 'ubicacion']
        ordering = ['ubicacion', 'producto']
        indexes = [
            models.Index(fields=['producto', 'ubicacion']),
            models.Index(fields=['ubicacion', 'cantidad']),
        ]
    
    def __str__(self):
        return f"{self.producto.nombre} en {self.ubicacion.nombre}: {self.cantidad}"
    
    @property
    def requiere_reorden(self):
        """Indica si el stock está por debajo del punto de reorden"""
        return self.cantidad <= self.punto_reorden
    
    @property
    def stock_bajo(self):
        """Indica si el stock está por debajo del mínimo"""
        return self.cantidad <= self.stock_minimo
    
    @property
    def stock_excedido(self):
        """Indica si el stock supera el máximo"""
        return self.stock_maximo > 0 and self.cantidad > self.stock_maximo
    
    def ajustar_stock(self, cantidad, tipo_movimiento, detalle, usuario):
        """
        Ajusta el stock y registra el movimiento en kardex
        
        Args:
            cantidad: cantidad a ajustar (positivo para aumentar, negativo para disminuir)
            tipo_movimiento: tipo de movimiento (ej: 'VENTA', 'COMPRA', 'TRANSFERENCIA')
            detalle: descripción del movimiento
            usuario: usuario que realiza el ajuste
        """
        cantidad_anterior = self.cantidad
        self.cantidad += Decimal(str(cantidad))
        
        # Validar que no quede negativo
        if self.cantidad < 0:
            raise ValueError(f'Stock insuficiente. Disponible: {cantidad_anterior}, Solicitado: {abs(cantidad)}')
        
        self.editadoPor = usuario
        self.save()
        
        # Registrar en kardex
        KardexMovimiento.objects.create(
            idProducto=self.producto.id,
            idUbicacion=self.ubicacion.id,
            fecha=timezone.now(),
            tipoMovimiento=tipo_movimiento,
            detalle=f"{detalle} - {self.ubicacion.nombre}",
            ingreso=cantidad if cantidad > 0 else 0,
            egreso=abs(cantidad) if cantidad < 0 else 0,
            saldo=self.cantidad
        )
        
        return self.cantidad

