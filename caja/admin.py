from django.contrib import admin
from .models import Caja, CierreCaja, AperturaCaja


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'activa']
    list_filter = ['activa']
    search_fields = ['codigo', 'nombre']


@admin.register(CierreCaja)
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = ['id', 'idCaja', 'fechaApertura', 'fechaCierre', 'estado', 'saldoInicial', 'diferencia']
    list_filter = ['estado', 'fechaApertura', 'fechaCierre']
    search_fields = ['idCaja']
    readonly_fields = ['fechaApertura', 'creadoDate']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('idCaja', 'estado')
        }),
        ('Apertura', {
            'fields': ('idUsuarioApertura', 'fechaApertura', 'saldoInicial')
        }),
        ('Cierre', {
            'fields': ('idUsuarioCierre', 'fechaCierre', 'totalIngresosSistema', 'totalEgresosSistema', 
                      'saldoTeoricoSistema', 'totalContadoFisico', 'diferencia')
        }),
        ('Auditoría', {
            'fields': ('creadoPor', 'creadoDate', 'anulado', 'anuladoPor', 'anuladoDate')
        })
    )


@admin.register(AperturaCaja)
class AperturaCajaAdmin(admin.ModelAdmin):
    list_display = ['AperturaID', 'Caja', 'FechaApertura', 'MontoInicial', 'UsuarioApertura']
    list_filter = ['FechaApertura']
    search_fields = ['Caja', 'UsuarioApertura']
    readonly_fields = ['FechaApertura']
