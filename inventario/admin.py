from django.contrib import admin
from .models import (
    Compra, DetalleCompra, PagoCompra, Kardex, AjusteInventario, DetalleAjuste,
    Ubicacion, OrdenCompra, DetalleOrdenCompra, TransferenciaStock, 
    DetalleTransferencia, ConfiguracionStock
)


# Administración de Ubicaciones
@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'responsable', 'activo', 'es_principal']
    list_filter = ['tipo', 'activo', 'es_principal']
    search_fields = ['codigo', 'nombre', 'responsable']
    ordering = ['nombre']


# Administración de Órdenes de Compra
class DetalleOrdenCompraInline(admin.TabularInline):
    model = DetalleOrdenCompra
    extra = 0
    fields = ['producto', 'cantidad_solicitada', 'cantidad_recibida', 'precio_unitario']
    readonly_fields = ['stock_actual', 'stock_minimo']


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ['numero_orden', 'proveedor', 'estado', 'prioridad', 'fecha_creacion', 'total']
    list_filter = ['estado', 'prioridad', 'generada_automaticamente', 'fecha_creacion']
    search_fields = ['numero_orden', 'proveedor__nombre_comercial']
    readonly_fields = ['numero_orden', 'fecha_creacion', 'usuario_creacion']
    inlines = [DetalleOrdenCompraInline]
    ordering = ['-fecha_creacion']
    
    fieldsets = (
        ('Información General', {
            'fields': ('numero_orden', 'proveedor', 'ubicacion_destino', 'estado', 'prioridad')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_envio', 'fecha_entrega_esperada', 'fecha_entrega_real')
        }),
        ('Totales', {
            'fields': ('subtotal', 'descuento', 'impuesto', 'total')
        }),
        ('Información Adicional', {
            'fields': ('observaciones', 'generada_automaticamente', 'usuario_creacion', 'usuario_envio')
        }),
    )


# Administración de Transferencias de Stock
class DetalleTransferenciaInline(admin.TabularInline):
    model = DetalleTransferencia
    extra = 0
    fields = ['producto', 'cantidad', 'cantidad_recibida', 'observaciones']
    readonly_fields = ['stock_origen_antes', 'stock_destino_antes']


@admin.register(TransferenciaStock)
class TransferenciaStockAdmin(admin.ModelAdmin):
    list_display = ['numero_transferencia', 'ubicacion_origen', 'ubicacion_destino', 
                    'estado', 'tipo', 'fecha_creacion', 'usuario_creacion']
    list_filter = ['estado', 'tipo', 'fecha_creacion']
    search_fields = ['numero_transferencia', 'ubicacion_origen__nombre', 'ubicacion_destino__nombre']
    readonly_fields = ['numero_transferencia', 'fecha_creacion', 'fecha_envio', 'fecha_recepcion']
    inlines = [DetalleTransferenciaInline]
    ordering = ['-fecha_creacion']
    
    fieldsets = (
        ('Información General', {
            'fields': ('numero_transferencia', 'ubicacion_origen', 'ubicacion_destino', 'estado', 'tipo')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_envio', 'fecha_recepcion')
        }),
        ('Detalles', {
            'fields': ('motivo', 'observaciones')
        }),
        ('Usuarios', {
            'fields': ('usuario_creacion', 'usuario_envio', 'usuario_recepcion')
        }),
    )


# Administración de Configuración de Stock
@admin.register(ConfiguracionStock)
class ConfiguracionStockAdmin(admin.ModelAdmin):
    list_display = ['producto', 'ubicacion', 'stock_minimo', 'stock_maximo', 
                    'punto_reorden', 'generar_orden_automatica', 'proveedor_preferido']
    list_filter = ['generar_orden_automatica', 'ubicacion', 'fecha_creacion']
    search_fields = ['producto__nombre', 'producto__codigo', 'ubicacion__nombre']
    ordering = ['producto__nombre']
    
    fieldsets = (
        ('Producto y Ubicación', {
            'fields': ('producto', 'ubicacion')
        }),
        ('Niveles de Stock', {
            'fields': ('stock_minimo', 'stock_maximo', 'punto_reorden', 'cantidad_reorden')
        }),
        ('Configuración Automática', {
            'fields': ('generar_orden_automatica', 'proveedor_preferido')
        }),
        ('Información de Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion', 'usuario'),
            'classes': ('collapse',)
        }),
    )


# Administración existente (mantener los que ya estaban)
class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 0


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ['numero_compra', 'proveedor', 'fecha', 'total', 'estado']
    list_filter = ['estado', 'tipo_pago', 'fecha']
    search_fields = ['numero_compra', 'numero_factura_proveedor', 'proveedor__nombre_comercial']
    inlines = [DetalleCompraInline]
    readonly_fields = ['numero_compra']


@admin.register(Kardex)
class KardexAdmin(admin.ModelAdmin):
    list_display = ['producto', 'fecha', 'tipo_movimiento', 'concepto', 'cantidad', 'saldo_cantidad']
    list_filter = ['tipo_movimiento', 'concepto', 'fecha']
    search_fields = ['producto__nombre', 'producto__codigo', 'numero_documento']
    readonly_fields = ['fecha', 'saldo_cantidad', 'saldo_valor']
    ordering = ['-fecha']


class DetalleAjusteInline(admin.TabularInline):
    model = DetalleAjuste
    extra = 0


@admin.register(AjusteInventario)
class AjusteInventarioAdmin(admin.ModelAdmin):
    list_display = ['numero_ajuste', 'fecha', 'tipo_ajuste', 'motivo', 'usuario']
    list_filter = ['tipo_ajuste', 'motivo', 'fecha']
    search_fields = ['numero_ajuste']
    inlines = [DetalleAjusteInline]
    readonly_fields = ['numero_ajuste']
