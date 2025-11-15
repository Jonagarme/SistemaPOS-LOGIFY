from django.urls import path
from . import views, views_ordenes, views_exportar

app_name = 'proveedores'

urlpatterns = [
    path('', views.lista_proveedores, name='lista'),
    path('crear/', views.crear_proveedor, name='crear'),
    path('<int:pk>/editar/', views.editar_proveedor, name='editar'),
    path('<int:pk>/detalle/', views.detalle_proveedor, name='detalle'),
    path('<int:pk>/eliminar/', views.eliminar_proveedor, name='eliminar'),
    path('<int:pk>/historial/', views.historial_proveedor, name='historial'),
    path('buscar/', views.buscar_proveedores, name='buscar'),
    
    # Órdenes de Compra
    path('ordenes/', views_ordenes.lista_ordenes_proveedor, name='lista_ordenes'),
    path('ordenes/crear/', views_ordenes.crear_orden_proveedor, name='crear_orden'),
    path('ordenes/<int:pk>/', views_ordenes.detalle_orden_proveedor, name='detalle_orden_proveedor'),
    path('ordenes/<int:pk>/cambiar-estado/', views_ordenes.cambiar_estado_orden, name='cambiar_estado_orden'),
    
    # APIs AJAX
    path('api/buscar-productos/', views_ordenes.api_buscar_productos, name='api_buscar_productos'),
    path('api/proveedor/<int:pk>/', views_ordenes.api_datos_proveedor, name='api_datos_proveedor'),
    
    # Exportar
    path('ordenes/<int:pk>/excel/', views_exportar.exportar_orden_excel, name='exportar_orden_excel'),
    path('ordenes/<int:pk>/pdf/', views_exportar.exportar_orden_pdf, name='exportar_orden_pdf'),
]