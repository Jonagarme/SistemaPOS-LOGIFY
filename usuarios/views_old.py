"""
Vistas temporales mínimas para autenticación personalizada
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import connection


@login_required
def dashboard(request):
    """Dashboard principal del sistema"""
    try:
        with connection.cursor() as cursor:
            # Total de productos
            cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1")
            total_productos = cursor.fetchone()[0]
            
            # Total de clientes
            cursor.execute("SELECT COUNT(*) FROM clientes WHERE activo = 1")
            total_clientes = cursor.fetchone()[0]
            
            # Total de proveedores
            cursor.execute("SELECT COUNT(*) FROM proveedores WHERE activo = 1")
            total_proveedores = cursor.fetchone()[0]
            
            # Ventas del día
            cursor.execute("""
                SELECT COALESCE(SUM(total), 0) 
                FROM ventas 
                WHERE DATE(fecha_venta) = CURDATE()
            """)
            ventas_hoy = cursor.fetchone()[0] or 0
            
        context = {
            'total_productos': total_productos,
            'total_clientes': total_clientes,
            'total_proveedores': total_proveedores,
            'ventas_hoy': ventas_hoy,
        }
    except Exception as e:
        context = {
            'total_productos': 0,
            'total_clientes': 0,
            'total_proveedores': 0,
            'ventas_hoy': 0,
            'error': f'Error al cargar datos: {str(e)}'
        }
    
    return render(request, 'dashboard.html', context)


def custom_login(request):
    """Vista de login personalizada"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            # Intentar autenticar
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'¡Bienvenido {user.get_full_name() or user.username}!')
                    return redirect('usuarios:dashboard')
                else:
                    messages.error(request, 'Tu cuenta está desactivada.')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor, completa todos los campos.')
    
    return render(request, 'usuarios/custom_login.html')


def custom_logout(request):
    """Vista de logout personalizada"""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('usuarios:login')


# Funciones temporalmente comentadas hasta completar la migración
def lista_usuarios(request):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def crear_usuario(request):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def editar_usuario(request, usuario_id):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def detalle_usuario(request, usuario_id):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def cambiar_estado_usuario(request, usuario_id):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def anular_usuario(request, usuario_id):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def lista_roles(request):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def crear_rol(request):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def editar_rol(request, rol_id):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def perfil_usuario(request):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def cambiar_password(request):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')

def configuracion_empresa(request):
    """TEMPORALMENTE DESHABILITADA - Migración en proceso"""
    messages.warning(request, 'Funcionalidad en mantenimiento durante migración.')
    return redirect('usuarios:dashboard')