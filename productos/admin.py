from django.contrib import admin
from .models import (
    TipoProducto, ClaseProducto, Categoria, Subcategoria, 
    SubnivelProducto, Marca, Laboratorio, Producto, UnidadMedida
)


@admin.register(TipoProducto)
class TipoProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(ClaseProducto)
class ClaseProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(Subcategoria)
class SubcategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'id_categoria']
    list_filter = ['id_categoria']
    search_fields = ['nombre']


@admin.register(SubnivelProducto)
class SubnivelProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'id_subcategoria']
    list_filter = ['id_subcategoria']
    search_fields = ['nombre']


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(Laboratorio)
class LaboratorioAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_principal', 'nombre', 'id_categoria', 'id_marca', 
        'precio_venta', 'stock', 'activo'
    ]
    list_filter = [
        'id_categoria', 'id_marca', 'id_laboratorio', 'activo', 
        'es_divisible', 'es_psicotropico', 'clasificacion_abc'
    ]
    search_fields = ['codigo_principal', 'codigo_auxiliar', 'nombre', 'descripcion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo_principal', 'codigo_auxiliar', 'nombre', 'descripcion', 'observaciones')
        }),
        ('Clasificación', {
            'fields': (
                'id_tipo_producto', 'id_clase_producto', 'id_categoria', 
                'id_subcategoria', 'id_subnivel', 'id_marca', 'id_laboratorio'
            )
        }),
        ('Inventario', {
            'fields': ('stock', 'stock_minimo', 'stock_maximo')
        }),
        ('Precios y Costos', {
            'fields': ('costo_unidad', 'costo_caja', 'pvp_unidad', 'precio_venta')
        }),
        ('Características', {
            'fields': (
                'registro_sanitario', 'es_divisible', 'es_psicotropico', 
                'requiere_cadena_frio', 'requiere_seguimiento', 
                'clasificacion_abc', 'calculo_abc_manual'
            )
        }),
        ('Control', {
            'fields': ('activo', 'anulado')
        })
    )


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'abreviacion', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'abreviacion']
