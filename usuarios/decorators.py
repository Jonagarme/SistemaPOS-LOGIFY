"""
Decoradores para control de permisos basado en roles
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db import connection


def requiere_permiso(modulo, permiso, tipo='ver'):
    """
    Decorador que verifica si el usuario tiene permiso para acceder a una vista
    
    Uso:
        @requiere_permiso('productos', 'listar_productos', 'ver')
        def lista_productos(request):
            ...
    
    Args:
        modulo: El módulo del sistema (productos, ventas, caja, etc.)
        permiso: El permiso específico (listar_productos, crear_venta, etc.)
        tipo: Tipo de permiso ('ver', 'crear', 'editar', 'eliminar')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Verificar si el usuario está autenticado
            if not request.user.is_authenticated:
                messages.error(request, 'Debe iniciar sesión para acceder a esta página')
                return redirect('usuarios:login')
            
            # Obtener el usuario del sistema
            try:
                usuario_id = request.session.get('usuario_sistema_id')
                if not usuario_id:
                    messages.error(request, 'No se pudo verificar su sesión')
                    return redirect('usuarios:login')
                
                # Consultar permisos desde la base de datos
                with connection.cursor() as cursor:
                    # Obtener el rol del usuario
                    cursor.execute("""
                        SELECT r.id, r.nombre
                        FROM usuarios u
                        JOIN roles r ON u.idRol = r.id
                        WHERE u.id = %s AND u.activo = 1 AND u.anulado = 0
                    """, [usuario_id])
                    
                    rol_data = cursor.fetchone()
                    if not rol_data:
                        messages.error(request, 'Usuario sin rol asignado')
                        return redirect('usuarios:dashboard')
                    
                    rol_id, rol_nombre = rol_data
                    
                    # El administrador tiene acceso a todo
                    if rol_nombre.lower() == 'administrador':
                        return view_func(request, *args, **kwargs)
                    
                    # Verificar permiso específico
                    cursor.execute("""
                        SELECT puede_ver, puede_crear, puede_editar, puede_eliminar
                        FROM rol_permisos
                        WHERE idRol = %s AND modulo = %s AND permiso = %s
                    """, [rol_id, modulo, permiso])
                    
                    permiso_data = cursor.fetchone()
                    if not permiso_data:
                        # No tiene el permiso
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False,
                                'error': 'No tiene permisos para realizar esta acción'
                            }, status=403)
                        messages.error(request, 'No tiene permisos para acceder a esta página')
                        return redirect('usuarios:dashboard')
                    
                    puede_ver, puede_crear, puede_editar, puede_eliminar = permiso_data
                    
                    # Verificar según el tipo de permiso solicitado
                    tiene_permiso = False
                    if tipo == 'ver':
                        tiene_permiso = puede_ver
                    elif tipo == 'crear':
                        tiene_permiso = puede_crear
                    elif tipo == 'editar':
                        tiene_permiso = puede_editar
                    elif tipo == 'eliminar':
                        tiene_permiso = puede_eliminar
                    
                    if not tiene_permiso:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False,
                                'error': f'No tiene permisos para {tipo} en {modulo}'
                            }, status=403)
                        messages.error(request, f'No tiene permisos para {tipo} en este módulo')
                        return redirect('usuarios:dashboard')
                    
                    # Si tiene el permiso, ejecutar la vista
                    return view_func(request, *args, **kwargs)
                    
            except Exception as e:
                print(f"Error verificando permisos: {e}")
                messages.error(request, 'Error al verificar permisos')
                return redirect('usuarios:dashboard')
        
        return wrapper
    return decorator


def solo_administrador(view_func):
    """
    Decorador que permite acceso solo a administradores
    
    Uso:
        @solo_administrador
        def gestionar_permisos(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Debe iniciar sesión')
            return redirect('usuarios:login')
        
        try:
            usuario_id = request.session.get('usuario_sistema_id')
            if not usuario_id:
                messages.error(request, 'Sesión inválida')
                return redirect('usuarios:login')
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT r.nombre
                    FROM usuarios u
                    JOIN roles r ON u.idRol = r.id
                    WHERE u.id = %s
                """, [usuario_id])
                
                result = cursor.fetchone()
                if not result or result[0].lower() != 'administrador':
                    messages.error(request, 'Esta función está disponible solo para administradores')
                    return redirect('usuarios:dashboard')
            
            return view_func(request, *args, **kwargs)
            
        except Exception as e:
            print(f"Error verificando rol de administrador: {e}")
            messages.error(request, 'Error al verificar permisos')
            return redirect('usuarios:dashboard')
    
    return wrapper


def registrar_auditoria(modulo, accion, entidad=None, obtener_id_entidad=None, descripcion_template=None):
    """
    Decorador que registra automáticamente las acciones en la tabla de auditoría
    
    Uso:
        @registrar_auditoria('productos', 'CREAR', 'producto', 
                            obtener_id_entidad=lambda response: response.context.get('producto_id'),
                            descripcion_template='Creó el producto {nombre}')
        def crear_producto(request):
            ...
    
    Args:
        modulo: Módulo del sistema (productos, ventas, caja, etc.)
        accion: Tipo de acción (CREAR, EDITAR, ELIMINAR, VER, etc.)
        entidad: Tipo de entidad (producto, venta, cliente, etc.)
        obtener_id_entidad: Función para obtener el ID de la entidad desde kwargs o string con nombre del parámetro
        descripcion_template: Template string para la descripción
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Ejecutar la vista original
            response = view_func(request, *args, **kwargs)
            
            try:
                # Obtener usuario
                usuario_id = request.session.get('usuario_sistema_id')
                if not usuario_id:
                    return response
                
                # Obtener nombre de usuario
                usuario_nombre = request.user.username if hasattr(request.user, 'username') else 'Sistema'
                
                with connection.cursor() as cursor:
                    cursor.execute("SELECT nombreCompleto FROM usuarios WHERE id = %s", [usuario_id])
                    result = cursor.fetchone()
                    if result:
                        usuario_nombre = result[0]
                
                # Obtener ID de entidad
                id_entidad = None
                if obtener_id_entidad:
                    if callable(obtener_id_entidad):
                        id_entidad = obtener_id_entidad(*args, **kwargs)
                    elif isinstance(obtener_id_entidad, str):
                        id_entidad = kwargs.get(obtener_id_entidad)
                elif 'pk' in kwargs:
                    id_entidad = kwargs['pk']
                elif 'id' in kwargs:
                    id_entidad = kwargs['id']
                
                # Generar descripción
                descripcion = descripcion_template or f'{accion} en {modulo}'
                if kwargs:
                    try:
                        descripcion = descripcion.format(**kwargs)
                    except:
                        pass
                
                # Obtener datos extra del POST
                extra = None
                if request.method == 'POST' and accion in ['CREAR', 'EDITAR', 'ELIMINAR']:
                    import json
                    extra_dict = {key: value for key, value in request.POST.items() 
                                 if not key.startswith('csrf') and key not in ['password', 'contrasena']}
                    extra = json.dumps(extra_dict, ensure_ascii=False) if extra_dict else None
                
                # Registrar en auditoría
                from usuarios.models import Auditoria
                Auditoria.registrar(
                    usuario_id=usuario_id,
                    usuario_nombre=usuario_nombre,
                    modulo=modulo,
                    accion=accion,
                    entidad=entidad,
                    id_entidad=id_entidad,
                    descripcion=descripcion,
                    request=request,
                    extra=extra
                )
                
            except Exception as e:
                # No fallar la vista si hay error en auditoría
                print(f"Error registrando auditoría: {e}")
            
            return response
        
        return wrapper
    return decorator
