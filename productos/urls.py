from django.urls import path
from . import views
from . import views_ubicaciones
from . import api_duplicados

app_name = 'productos'

urlpatterns = [
    # Productos
    path('', views.lista_productos, name='lista'),
    path('simple/', views.lista_productos_simple, name='lista_simple'),
    path('crear/', views.crear_producto, name='crear'),
    path('<int:producto_id>/editar/', views.editar_producto, name='editar'),
    path('<int:producto_id>/detalle/', views.detalle_producto, name='detalle'),
    path('stock-bajo/', views.productos_con_stock_bajo, name='stock_bajo'),
    
    # Ubicaciones de Productos en Perchas
    path('ubicaciones/', views_ubicaciones.ubicaciones_productos, name='ubicaciones_productos'),
    path('ubicaciones/secciones/', views_ubicaciones.gestionar_secciones, name='gestionar_secciones'),
    path('ubicaciones/secciones/<int:seccion_id>/', views_ubicaciones.obtener_seccion, name='obtener_seccion'),
    path('ubicaciones/secciones/<int:seccion_id>/editar/', views_ubicaciones.editar_seccion, name='editar_seccion'),
    path('ubicaciones/secciones/<int:seccion_id>/eliminar/', views_ubicaciones.eliminar_seccion, name='eliminar_seccion'),
    path('ubicaciones/secciones/json/', views_ubicaciones.obtener_secciones_json, name='obtener_secciones_json'),
    path('ubicaciones/secciones/<int:seccion_id>/perchas/', views_ubicaciones.gestionar_perchas, name='gestionar_perchas'),
    path('ubicaciones/secciones/<int:seccion_id>/perchas/json/', views_ubicaciones.obtener_perchas_seccion, name='obtener_perchas_seccion'),
    path('ubicaciones/perchas/<int:percha_id>/mapa/', views_ubicaciones.mapa_percha, name='mapa_percha'),
    path('ubicaciones/buscar-productos/', views_ubicaciones.buscar_productos_ajax, name='buscar_productos_ajax'),
    path('ubicaciones/ubicar-producto/', views_ubicaciones.ubicar_producto, name='ubicar_producto'),
    path('ubicaciones/quitar-ubicacion/', views_ubicaciones.quitar_ubicacion, name='quitar_ubicacion'),
    path('ubicaciones/producto/<int:producto_id>/', views_ubicaciones.obtener_ubicacion_producto, name='ubicacion_producto'),
    
    # Categorías
    path('categorias/', views.lista_categorias, name='categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    
    # Marcas
    path('marcas/', views.lista_marcas, name='marcas'),
    path('marcas/crear/', views.crear_marca, name='crear_marca'),
    path('marcas/<int:pk>/editar/', views.editar_marca, name='editar_marca'),
    
    # API endpoints
    path('api/buscar/', views.buscar_productos_api, name='buscar_api'),
    path('api/cache/', views.productos_cache_api, name='cache_api'),
    
    # API para detección de duplicados
    path('api/duplicados/buscar/', api_duplicados.api_buscar_similares, name='api_buscar_similares'),
    path('api/duplicados/buscar-lote/', api_duplicados.api_buscar_similares_lote, name='api_buscar_similares_lote'),
    path('api/duplicados/vincular/', api_duplicados.api_vincular_codigo, name='api_vincular_codigo'),
    path('api/duplicados/codigo/<str:codigo>/', api_duplicados.api_obtener_por_codigo, name='api_obtener_por_codigo'),
    
    # Unidades de medida
    path('unidades/', views.lista_unidades, name='unidades'),
    path('unidades/crear/', views.crear_unidad, name='crear_unidad'),
    path('unidades/<int:pk>/editar/', views.editar_unidad, name='editar_unidad'),
    
    # Reportes
    path('reportes/stock/', views.reporte_stock, name='reporte_stock'),
    path('reportes/bajo-stock/', views.productos_bajo_stock, name='bajo_stock'),
]