from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Autenticación personalizada
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('api/usuario-info/', views.usuario_info, name='usuario_info'),
    
    # Gestión de usuarios del sistema
    path('gestion/', views.lista_usuarios, name='lista_usuarios'),
    path('gestion/crear/', views.crear_usuario, name='crear_usuario'),
    path('gestion/<int:usuario_id>/editar/', views.editar_usuario, name='editar_usuario'),
    path('gestion/<int:usuario_id>/detalle/', views.detalle_usuario, name='detalle_usuario'),
    path('cambiar-estado/<int:usuario_id>/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('anular/<int:usuario_id>/', views.anular_usuario, name='anular_usuario'),
    
    # Gestión de roles
    path('roles/', views.lista_roles, name='lista_roles'),
    path('roles/crear/', views.crear_rol, name='crear_rol'),
    path('roles/<int:rol_id>/editar/', views.editar_rol, name='editar_rol'),
    
    # Gestión de usuarios (manteniendo URLs originales para compatibilidad)
    path('', views.lista_usuarios, name='lista'),
    path('crear/', views.crear_usuario, name='crear'),
    path('<int:pk>/editar/', views.editar_usuario, name='editar'),
    path('<int:pk>/detalle/', views.detalle_usuario, name='detalle'),
    
    # Perfil de usuario
    path('perfil/', views.perfil_usuario, name='perfil'),
    path('perfil/cambiar-password/', views.cambiar_password, name='cambiar_password'),
    
    # Configuración de empresa
    path('configuracion-empresa/', views.configuracion_empresa, name='configuracion_empresa'),
    
    # Test
    path('test/', views.test_usuarios, name='test_usuarios'),
    path('debug/', views.lista_usuarios_debug, name='lista_usuarios_debug'),
]