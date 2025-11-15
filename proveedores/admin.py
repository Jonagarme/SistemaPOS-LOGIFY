from django.contrib import admin
from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['ruc', 'razon_social', 'nombre_comercial', 'telefono', 'email', 'estado']
    list_filter = ['estado', 'anulado', 'creado_date']
    search_fields = ['ruc', 'razon_social', 'nombre_comercial', 'email']
    readonly_fields = ['creado_date', 'editado_date', 'creado_por', 'editado_por']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('ruc', 'razon_social', 'nombre_comercial')
        }),
        ('Contacto', {
            'fields': ('telefono', 'email', 'direccion')
        }),
        ('Control', {
            'fields': ('estado', 'anulado', 'creado_date', 'editado_date', 'creado_por', 'editado_por')
        }),
    )
