from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['cedula_ruc', 'nombres', 'apellidos', 'tipo_identificacion', 'razon_social', 'telefono_principal', 'estado']
    list_filter = ['tipo_identificacion', 'estado', 'anulado', 'creado_date']
    search_fields = ['cedula_ruc', 'nombres', 'apellidos', 'razon_social', 'email']
    readonly_fields = ['creado_date', 'editado_date', 'creado_por', 'editado_por']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('tipo_identificacion', 'cedula_ruc')
        }),
        ('Datos Personales', {
            'fields': ('nombres', 'apellidos', 'razon_social', 'fecha_nacimiento')
        }),
        ('Contacto', {
            'fields': ('telefono', 'celular', 'email', 'direccion')
        }),
        ('Cliente', {
            'fields': ('tipo_cliente',)
        }),
        ('Control', {
            'fields': ('estado', 'anulado', 'creado_date', 'editado_date', 'creado_por', 'editado_por')
        }),
    )
