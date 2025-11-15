from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_reportes, name='dashboard'),
    
    # Exportaciones
    path('productos/exportar/', views.exportar_productos, name='exportar_productos'),
    path('clientes/exportar/', views.exportar_clientes, name='exportar_clientes'),
    path('proveedores/exportar/', views.exportar_proveedores, name='exportar_proveedores'),
    
    # Estadísticas
    path('estadisticas/', views.reporte_estadisticas, name='estadisticas'),
]