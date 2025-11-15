from django.urls import path
from . import views

app_name = 'cotizaciones'

urlpatterns = [
    # Lista y búsqueda
    path('', views.lista_cotizaciones, name='lista'),
    
    # CRUD básico
    path('crear/', views.crear_cotizacion, name='crear'),
    path('<int:pk>/', views.detalle_cotizacion, name='detalle'),
    path('<int:pk>/editar/', views.editar_cotizacion, name='editar'),
    
    # Acciones especiales
    path('<int:pk>/cambiar-estado/', views.cambiar_estado, name='cambiar_estado'),
    path('<int:pk>/convertir-venta/', views.convertir_a_venta, name='convertir_venta'),
    path('<int:pk>/duplicar/', views.duplicar_cotizacion, name='duplicar'),
    
    # AJAX
    path('api/precio-producto/', views.obtener_precio_producto, name='precio_producto'),
]