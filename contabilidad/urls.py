from django.urls import path
from . import views

app_name = 'contabilidad'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_contabilidad, name='dashboard'),
    
    # Cuentas por cobrar
    path('cuentas-por-cobrar/', views.cuentas_por_cobrar, name='cuentas_por_cobrar'),
    path('registrar-pago-cxc/', views.registrar_pago_cxc, name='registrar_pago_cxc'),
    
    # Cuentas por pagar
    path('cuentas-por-pagar/', views.cuentas_por_pagar, name='cuentas_por_pagar'),
    path('registrar-pago-cxp/', views.registrar_pago_cxp, name='registrar_pago_cxp'),
    
    # Flujo de caja
    path('flujo-caja/', views.flujo_caja, name='flujo_caja'),
    
    # Conciliación bancaria
    path('conciliacion-bancaria/', views.conciliacion_bancaria, name='conciliacion_bancaria'),
    path('marcar-conciliado/', views.marcar_conciliado, name='marcar_conciliado'),
    
    # Control de gastos
    path('control-gastos/', views.control_gastos, name='control_gastos'),
    path('aprobar-gasto/', views.aprobar_gasto, name='aprobar_gasto'),
    
    # Reportes contables
    path('reportes/', views.reportes_contables, name='reportes_contables'),
]