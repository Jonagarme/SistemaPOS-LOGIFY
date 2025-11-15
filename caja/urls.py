from django.urls import path
from . import views

app_name = 'caja'

urlpatterns = [
    # Cajas
    path('', views.lista_cajas, name='lista'),
    path('crear/', views.crear_caja, name='crear'),
    path('<int:pk>/editar/', views.editar_caja, name='editar'),
    path('<int:caja_id>/eliminar/', views.eliminar_caja, name='eliminar'),
    path('<int:caja_id>/activar/', views.activar_caja, name='activar'),
    
    # Operaciones de caja
    path('abrir/', views.abrir_caja, name='abrir'),
    path('cerrar/', views.cerrar_caja, name='cerrar'),
    path('estado/', views.estado_caja, name='estado'),
    path('iniciar-dia/', views.iniciar_dia_caja, name='iniciar_dia'),
    
    # Movimientos
    path('movimientos/', views.lista_movimientos, name='movimientos'),
    path('movimiento/agregar/', views.agregar_movimiento, name='agregar_movimiento'),
    
    # Historiales
    path('aperturas/', views.lista_aperturas, name='aperturas'),
    path('cierres/', views.lista_cierres, name='cierres'),
    path('historial/', views.historial_cierres, name='historial'),
    
    # Dashboard
    path('dashboard/', views.dashboard_caja, name='dashboard'),
    
    # API
    path('api/verificar-caja/', views.verificar_caja_abierta, name='verificar_caja_abierta'),
    path('api/cierre/<int:cierre_id>/', views.detalle_cierre_api, name='detalle_cierre_api'),
]
