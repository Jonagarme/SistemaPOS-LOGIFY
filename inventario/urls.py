from django.urls import path
from . import views
from . import views_reportes
from . import api_stock

app_name = 'inventario'

urlpatterns = [
    # Compras
    path('compras/', views.lista_compras, name='compras'),
    path('compras/nueva/', views.nueva_compra, name='nueva_compra'),
    path('compras/<int:pk>/detalle/', views.detalle_compra, name='detalle_compra'),
    path('compras/<int:pk>/editar/', views.editar_compra, name='editar_compra'),
    path('compras/<int:pk>/anular/', views.anular_compra, name='anular_compra'),
    
    # Órdenes de Compra (PO)
    path('ordenes-compra/', views.lista_ordenes_compra, name='lista_ordenes_compra'),
    path('ordenes-compra/crear/', views.crear_orden_compra, name='crear_orden_compra'),
    path('ordenes-compra/<int:pk>/', views.detalle_orden_compra, name='detalle_orden_compra'),
    path('ordenes-compra/<int:pk>/enviar/', views.enviar_orden_compra, name='enviar_orden_compra'),
    path('ordenes-compra/generar-automaticas/', views.generar_ordenes_automaticas, name='generar_ordenes_automaticas'),
    
    # Transferencias de Stock
    path('transferencias/', views.lista_transferencias, name='lista_transferencias'),
    path('transferencias/crear/', views.crear_transferencia, name='crear_transferencia'),
    path('transferencias/<int:pk>/', views.detalle_transferencia, name='detalle_transferencia'),
    path('transferencias/<int:pk>/enviar/', views.enviar_transferencia, name='enviar_transferencia'),
    path('transferencias/<int:pk>/recibir/', views.recibir_transferencia, name='recibir_transferencia'),
    
    # Ubicaciones
    path('ubicaciones/', views.lista_ubicaciones, name='ubicaciones'),
    path('ubicaciones/crear/', views.crear_ubicacion, name='crear_ubicacion'),
    
    # Reportes
    path('reportes/', views_reportes.index_reportes, name='reportes'),
    path('reportes/productos-caducados/', views_reportes.reporte_productos_caducados, name='reporte_productos_caducados'),
    path('reportes/productos-caducados/export/', views_reportes.export_productos_caducados, name='export_productos_caducados'),
    path('reportes/dashboard-caducados/', views_reportes.dashboard_caducados, name='dashboard_caducados'),
    
    # Configuración de Stock
    path('configuracion-stock/', views.configuracion_stock, name='configuracion_stock'),
    path('configuracion-stock/crear/', views.crear_configuracion_stock, name='crear_configuracion_stock'),
    
    # Kardex
    path('kardex/', views.kardex_general, name='kardex'),
    path('kardex/<int:producto_id>/', views.kardex_producto, name='kardex_producto'),
    path('kardex/exportar/', views.exportar_kardex, name='exportar_kardex'),
    
    # Ajustes de inventario
    path('ajustes/', views.lista_ajustes, name='ajustes'),
    path('ajustes/nuevo/', views.nuevo_ajuste, name='nuevo_ajuste'),
    path('ajustes/<int:pk>/detalle/', views.detalle_ajuste, name='detalle_ajuste'),
    
    # Reportes
    path('reportes/', views.reportes_inventario, name='reportes'),
    path('reportes/valorado/', views.inventario_valorado, name='inventario_valorado'),
    path('reportes/movimientos/', views.reporte_movimientos, name='reporte_movimientos'),
    path('reportes/compras-por-proveedor/', views.compras_por_proveedor, name='compras_por_proveedor'),
    
    # API Stock por Ubicación
    path('api/stock/<int:producto_id>/', api_stock.api_stock_por_ubicacion, name='api_stock_por_ubicacion'),
    path('api/productos-ubicacion/<int:ubicacion_id>/', api_stock.api_productos_con_stock, name='api_productos_con_stock'),
    path('api/resumen-stocks/', api_stock.api_resumen_stocks, name='api_resumen_stocks'),
]