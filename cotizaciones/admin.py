from django.contrib import admin
from .models import Cotizacion, DetalleCotizacion


class DetalleCotizacionInline(admin.TabularInline):
    model = DetalleCotizacion
    extra = 1
    fields = ['producto', 'cantidad', 'precio_unitario', 'descuento_linea', 'total']
    readonly_fields = ['total']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'fecha_creacion', 'fecha_vencimiento', 'estado', 'total']
    list_filter = ['estado', 'fecha_creacion', 'fecha_vencimiento']
    search_fields = ['numero', 'cliente__nombre', 'cliente__email']
    readonly_fields = ['numero', 'subtotal', 'impuesto', 'total', 'fecha_creacion', 'fecha_actualizacion']
    inlines = [DetalleCotizacionInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero', 'cliente', 'fecha_vencimiento', 'validez_dias', 'estado')
        }),
        ('Totales', {
            'fields': ('subtotal', 'descuento', 'impuesto', 'total'),
            'classes': ('collapse',)
        }),
        ('Información Adicional', {
            'fields': ('observaciones', 'condiciones'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('usuario_creacion', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DetalleCotizacion)
class DetalleCotizacionAdmin(admin.ModelAdmin):
    list_display = ['cotizacion', 'producto', 'cantidad', 'precio_unitario', 'total']
    list_filter = ['cotizacion__estado']
    search_fields = ['cotizacion__numero', 'producto__nombre']