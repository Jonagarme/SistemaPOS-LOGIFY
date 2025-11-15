from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.lista_clientes, name='lista'),
    path('crear/', views.crear_cliente, name='crear'),
    path('<int:pk>/editar/', views.editar_cliente, name='editar'),
    path('<int:pk>/detalle/', views.detalle_cliente, name='detalle'),
    path('<int:pk>/eliminar/', views.eliminar_cliente, name='eliminar'),
    path('<int:pk>/historial/', views.historial_cliente, name='historial'),
    path('buscar/', views.buscar_clientes, name='buscar'),
]