from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # Ventas
    path('', views.lista_ventas, name='lista'),
    path('nueva/', views.nueva_venta, name='crear'),
    path('crear-ajax/', views.crear_ajax, name='crear_ajax'),
    path('<int:pk>/detalle/', views.detalle_venta, name='detalle'),
    path('<int:pk>/anular/', views.anular_venta, name='anular'),
    path('<int:pk>/imprimir/', views.imprimir_factura, name='imprimir'),
    path('ticket/<str:numero_venta>/', views.ticket, name='ticket'),
    path('<int:venta_id>/ticket-termico/', views.ticket_termico, name='ticket_termico'),
    path('<int:venta_id>/json-facturacion/', views.json_facturacion, name='json_facturacion'),
    
    # Reportes
    path('reporte-consolidado/', views.reporte_consolidado, name='reporte_consolidado'),
    
    # Búsquedas de Ventas
    path('debug-ventas/', views.debug_ventas, name='debug_ventas'),  # Temporal para debug
    path('buscar-numero/', views.buscar_ventas_por_numero, name='buscar_ventas_numero'),
    path('<int:venta_id>/detalle-venta/', views.obtener_venta_detalle, name='venta_detalle'),
    path('buscar-por-numero/', views.obtener_venta_por_numero, name='venta_por_numero'),
    
    # Facturas Electrónicas
    path('facturas/', views.facturas_electronicas, name='facturas_electronicas'),
    path('facturas/buscar-numero/', views.buscar_facturas_por_numero, name='buscar_facturas_numero'),
    path('facturas/<int:factura_id>/detalle/', views.obtener_factura_detalle, name='factura_detalle'),
    path('facturas/buscar-por-numero/', views.obtener_factura_por_numero, name='factura_por_numero'),
    path('facturas/<int:pk>/detalle/', views.detalle_factura_electronica, name='detalle_factura_electronica'),
    path('facturas/<int:pk>/anular/', views.anular_factura_electronica, name='anular_factura_electronica'),
    path('facturas/<int:pk>/reenviar-sri/', views.reenviar_al_sri, name='reenviar_sri'),
    path('facturas/exportar/', views.exportar_facturas, name='exportar_facturas'),
    path('facturas/imprimir/', views.imprimir_facturas, name='imprimir_facturas'),
    
    # Ingreso de Productos desde XML
    path('ingreso-productos/', views.ingreso_productos, name='ingreso_productos'),
    path('procesar-xml/', views.procesar_xml_factura, name='procesar_xml'),
    path('consultar-clave/', views.consultar_clave_acceso, name='consultar_clave'),
    path('procesar-ingreso/', views.procesar_ingreso_productos, name='procesar_ingreso'),
    path('historial-precios/', views.obtener_historial_precios, name='historial_precios'),
    path('desvincular-codigo/', views.desvincular_codigo_alternativo, name='desvincular_codigo'),
    
    # Procesos de venta
    path('buscar-producto/', views.buscar_producto, name='buscar_producto'),
    path('agregar-producto/', views.agregar_producto, name='agregar_producto'),
    path('procesar-venta/', views.procesar_venta, name='procesar_venta'),
    
    # Devoluciones
    path('devoluciones/', views.lista_devoluciones, name='devoluciones'),
    path('devoluciones/crear/', views.crear_devolucion, name='crear_devolucion'),
    path('devoluciones/buscar-venta/', views.buscar_venta_devolucion, name='buscar_venta_devolucion'),
    path('devoluciones/<int:pk>/detalle/', views.detalle_devolucion, name='detalle_devolucion'),
    
    # Reportes
    path('reportes/', views.reportes_ventas, name='reportes'),
    path('reportes/por-fecha/', views.ventas_por_fecha, name='ventas_por_fecha'),
    path('reportes/por-vendedor/', views.ventas_por_vendedor, name='ventas_por_vendedor'),
    path('reportes/por-producto/', views.ventas_por_producto, name='ventas_por_producto'),
]