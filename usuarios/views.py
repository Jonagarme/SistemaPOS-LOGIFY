"""
Vistas para autenticación con tu tabla usuarios existente
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ConfiguracionEmpresa
from .forms import ConfiguracionEmpresaForm
import json


@login_required
def dashboard(request):
    """Dashboard principal del sistema"""
    try:
        # Obtener datos del usuario desde tu tabla
        usuario_info = {}
        if hasattr(request.user, 'usuario_sistema_id'):
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT u.nombreCompleto, u.email, r.nombre as rol
                    FROM usuarios u
                    LEFT JOIN roles r ON u.idRol = r.id
                    WHERE u.id = %s
                """, [request.user.usuario_sistema_id])
                
                row = cursor.fetchone()
                if row:
                    usuario_info = {
                        'nombre_completo': row[0],
                        'email': row[1],
                        'rol': row[2] or 'Sin rol'
                    }
        
        # Estadísticas del dashboard
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
            'usuario_info': usuario_info,
            'total_productos': total_productos,
            'total_clientes': total_clientes,
            'total_proveedores': total_proveedores,
            'ventas_hoy': ventas_hoy,
        }
    except Exception as e:
        context = {
            'usuario_info': {},
            'total_productos': 0,
            'total_clientes': 0,
            'total_proveedores': 0,
            'ventas_hoy': 0,
            'error': f'Error al cargar datos: {str(e)}'
        }
    
    return render(request, 'dashboard.html', context)


def custom_login(request):
    """Vista de login que autentica contra tu tabla usuarios"""
    if request.user.is_authenticated:
        return redirect('usuarios:dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            # El backend personalizado se encargará de verificar tu tabla
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Obtener datos completos del usuario desde tu tabla
                nombre_completo = getattr(user, 'nombre_completo', user.get_full_name() or user.username)
                rol_nombre = getattr(user, 'rol_nombre', 'Usuario')
                usuario_sistema_id = getattr(user, 'usuario_sistema_id', None)
                
                # Guardar información del usuario en sesión para modo offline
                request.session['usuario_offline'] = {
                    'id': user.id,
                    'username': user.username,
                    'nombre_completo': nombre_completo,
                    'rol_nombre': rol_nombre,
                    'usuario_sistema_id': usuario_sistema_id
                }
                
                # Registrar en auditoría
                from usuarios.models import Auditoria
                Auditoria.registrar(
                    usuario_id=usuario_sistema_id or user.id,
                    usuario_nombre=nombre_completo,
                    modulo='usuarios',
                    accion='LOGIN',
                    descripcion=f'{nombre_completo} ({rol_nombre}) inició sesión',
                    request=request
                )
                
                # Mensajes de bienvenida personalizados
                import datetime
                hora_actual = datetime.datetime.now()
                
                if hora_actual.hour < 12:
                    saludo = "¡Buenos días"
                elif hora_actual.hour < 18:
                    saludo = "¡Buenas tardes"
                else:
                    saludo = "¡Buenas noches"
                
                messages.success(request, f'{saludo} {nombre_completo}! 👋')
                messages.info(request, f'🎯 Has ingresado como: {rol_nombre}')
                messages.info(request, f'📅 Fecha de acceso: {hora_actual.strftime("%d/%m/%Y a las %H:%M")}')
                
                # Redireccionar según el rol o petición
                next_url = request.GET.get('next', 'usuarios:dashboard')
                return redirect(next_url)
            else:
                # Registrar intento fallido
                from usuarios.models import Auditoria
                Auditoria.registrar(
                    usuario_id=0,
                    usuario_nombre=username,
                    modulo='usuarios',
                    accion='LOGIN_FALLIDO',
                    descripcion=f'Intento fallido de login para usuario: {username}',
                    request=request
                )
                messages.error(request, 'Usuario o contraseña incorrectos, o tu cuenta está desactivada.')
        else:
            messages.error(request, 'Por favor, completa todos los campos.')
    
    return render(request, 'usuarios/custom_login.html')


def custom_logout(request):
    """Vista de logout personalizada con mensaje personalizado"""
    nombre_usuario = ""
    rol_usuario = ""
    usuario_sistema_id = None
    
    # Obtener información del usuario antes del logout
    if request.user.is_authenticated:
        if hasattr(request.user, 'nombre_completo'):
            nombre_usuario = request.user.nombre_completo
        else:
            nombre_usuario = request.user.get_full_name() or request.user.username
        
        # Obtener rol si está disponible
        if hasattr(request.user, 'rol_nombre'):
            rol_usuario = request.user.rol_nombre
        
        # Obtener ID del usuario del sistema
        if hasattr(request.user, 'usuario_sistema_id'):
            usuario_sistema_id = request.user.usuario_sistema_id
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT u.nombreCompleto, r.nombre as rol
                        FROM usuarios u
                        LEFT JOIN roles r ON u.idRol = r.id
                        WHERE u.id = %s
                    """, [request.user.usuario_sistema_id])
                    
                    row = cursor.fetchone()
                    if row:
                        nombre_usuario = row[0]
                        rol_usuario = row[1] or "Usuario"
            except:
                pass  # Si hay error, usar los datos que ya tenemos
        
        # Registrar logout en auditoría ANTES de cerrar sesión
        from usuarios.models import Auditoria
        Auditoria.registrar(
            usuario_id=usuario_sistema_id or request.user.id,
            usuario_nombre=nombre_usuario,
            modulo='usuarios',
            accion='LOGOUT',
            descripcion=f'{nombre_usuario} ({rol_usuario}) cerró sesión',
            request=request
        )
    
    logout(request)
    
    # Mensajes personalizados según el contexto
    if nombre_usuario and rol_usuario:
        messages.success(request, f'👋 ¡Hasta luego {nombre_usuario}!')
        messages.info(request, f'Tu sesión como {rol_usuario} ha sido cerrada de forma segura.')
    elif nombre_usuario:
        messages.success(request, f'👋 ¡Hasta luego {nombre_usuario}!')
        messages.info(request, 'Tu sesión ha sido cerrada de forma segura.')
    else:
        messages.info(request, '✅ Tu sesión ha sido cerrada correctamente.')
    
    # Mensaje adicional de seguridad
    messages.info(request, '🔒 Por tu seguridad, recuerda cerrar completamente tu navegador si usas una computadora compartida.')
    
    return redirect('usuarios:login')


# Vista para obtener información del usuario actual (AJAX)
@login_required
def usuario_info(request):
    """Retorna información del usuario actual desde tu tabla"""
    from django.http import JsonResponse
    
    try:
        if hasattr(request.user, 'usuario_sistema_id'):
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT u.id, u.nombreUsuario, u.nombreCompleto, u.email, 
                           r.nombre as rol, u.activo, u.anulado
                    FROM usuarios u
                    LEFT JOIN roles r ON u.idRol = r.id
                    WHERE u.id = %s
                """, [request.user.usuario_sistema_id])
                
                row = cursor.fetchone()
                if row:
                    return JsonResponse({
                        'success': True,
                        'usuario': {
                            'id': row[0],
                            'nombre_usuario': row[1],
                            'nombre_completo': row[2],
                            'email': row[3],
                            'rol': row[4] or 'Sin rol',
                            'activo': bool(row[5]),
                            'anulado': bool(row[6])
                        }
                    })
        
        return JsonResponse({
            'success': False,
            'error': 'No se pudo obtener información del usuario'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def lista_usuarios(request):
    """Lista todos los usuarios de tu tabla MySQL"""
    try:
        # Obtener parámetros de filtro
        search = request.GET.get('search', '')
        rol_filter = request.GET.get('rol', '')
        estado_filter = request.GET.get('estado', '')
        
        with connection.cursor() as cursor:
            # Primero, obtener lista de roles para los filtros
            cursor.execute("SELECT id, nombre FROM roles WHERE anulado = 0 ORDER BY nombre")
            roles = [{'id': row[0], 'nombre': row[1]} for row in cursor.fetchall()]
            
            # Construir query con filtros
            query = """
                SELECT u.id, u.nombreUsuario, u.nombreCompleto, u.email, 
                       r.nombre as rol, u.activo, u.anulado, u.creadoDate
                FROM usuarios u
                LEFT JOIN roles r ON u.idRol = r.id
                WHERE 1=1
            """
            params = []
            
            # Aplicar filtro de búsqueda
            if search:
                query += " AND (u.nombreUsuario LIKE %s OR u.nombreCompleto LIKE %s OR u.email LIKE %s)"
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            # Aplicar filtro de rol
            if rol_filter:
                query += " AND u.idRol = %s"
                params.append(rol_filter)
            
            # Aplicar filtro de estado
            if estado_filter == 'activo':
                query += " AND u.activo = 1 AND u.anulado = 0"
            elif estado_filter == 'inactivo':
                query += " AND u.activo = 0 AND u.anulado = 0"
            elif estado_filter == 'anulado':
                query += " AND u.anulado = 1"
            
            query += " ORDER BY u.id DESC"
            
            # Ejecutar query
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            usuarios = []
            for row in rows:
                usuarios.append({
                    'id': row[0],
                    'nombre_usuario': row[1],
                    'nombre_completo': row[2],
                    'email': row[3],
                    'rol_nombre': row[4] or 'Sin rol',
                    'activo': bool(row[5]) if row[5] is not None else True,
                    'anulado': bool(row[6]) if row[6] is not None else False,
                    'creado_date': row[7],
                })
        
        context = {
            'titulo': 'Gestión de Usuarios',
            'page_obj': usuarios,  # Cambiar de 'usuarios' a 'page_obj'
            'roles': roles,
            'search': search,
            'rol_filter': rol_filter,
            'estado_filter': estado_filter,
            'total_usuarios': len(usuarios),
            'activos': len([u for u in usuarios if u['activo'] and not u['anulado']]),
            'inactivos': len([u for u in usuarios if not u['activo'] or u['anulado']])
        }
        
        return render(request, 'usuarios/lista_usuarios.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar usuarios: {str(e)}')
        return redirect('usuarios:dashboard')

@login_required
def crear_usuario(request):
    """Crear nuevo usuario en tu tabla MySQL"""
    if request.method == 'POST':
        try:
            nombre_usuario = request.POST.get('nombre_usuario')
            nombre_completo = request.POST.get('nombre_completo')
            email = request.POST.get('email')
            password = request.POST.get('password')
            id_rol = request.POST.get('id_rol')
            tipo_menu = request.POST.get('tipo_menu', 'horizontal')
            
            # Validaciones básicas
            if not all([nombre_usuario, nombre_completo, email, password]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('usuarios:crear_usuario')
            
            # Verificar si ya existe el usuario
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM usuarios WHERE nombreUsuario = %s OR email = %s", 
                             [nombre_usuario, email])
                if cursor.fetchone():
                    messages.error(request, 'Ya existe un usuario con ese nombre de usuario o email.')
                    return redirect('usuarios:crear_usuario')
                
                # Crear hash de la contraseña
                import hashlib
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                
                # Insertar nuevo usuario
                cursor.execute("""
                    INSERT INTO usuarios (nombreUsuario, nombreCompleto, email, contrasenaHash, 
                                        idRol, activo, tipoMenu, anulado, creadoDate)
                    VALUES (%s, %s, %s, %s, %s, 1, %s, 0, NOW())
                """, [nombre_usuario, nombre_completo, email, password_hash, id_rol or None, tipo_menu])
                
                messages.success(request, f'Usuario {nombre_completo} creado exitosamente.')
                return redirect('usuarios:lista_usuarios')
                
        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
    
    # Obtener roles para el formulario
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, nombre, descripcion FROM roles WHERE anulado = 0 ORDER BY nombre")
            roles = [{'id': row[0], 'nombre': row[1], 'descripcion': row[2]} 
                    for row in cursor.fetchall()]
    except:
        roles = []
    
    return render(request, 'usuarios/crear_usuario.html', {'roles': roles})

@login_required 
def editar_usuario(request, usuario_id):
    """Editar usuario existente"""
    from .forms import UsuarioSistemaForm
    from .models import UsuarioSistema
    from django.contrib.auth.hashers import make_password
    from django.utils import timezone
    
    try:
        # Obtener el usuario desde el modelo
        try:
            usuario = UsuarioSistema.objects.get(pk=usuario_id)
        except UsuarioSistema.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
            return redirect('usuarios:lista_usuarios')
        
        if request.method == 'POST':
            form = UsuarioSistemaForm(request.POST, instance=usuario, is_edit=True)
            
            if form.is_valid():
                # Guardar sin commit para manejar campos adicionales
                usuario_actualizado = form.save(commit=False)
                
                # Actualizar contraseña si se proporcionó
                nueva_password = form.cleaned_data.get('contrasena')
                if nueva_password:
                    usuario_actualizado.contrasena_hash = make_password(nueva_password)
                
                # Campos de auditoría
                usuario_actualizado.editado_date = timezone.now()
                if hasattr(request.user, 'usuario_sistema_id'):
                    usuario_actualizado.editado_por = request.user.usuario_sistema_id
                
                usuario_actualizado.save()
                
                messages.success(request, f'Usuario {usuario_actualizado.nombre_completo} actualizado exitosamente.')
                return redirect('usuarios:lista_usuarios')
        else:
            # Crear formulario con instancia existente
            form = UsuarioSistemaForm(instance=usuario, is_edit=True)
        
        return render(request, 'usuarios/editar_usuario.html', {
            'form': form,
            'usuario': usuario,
            'titulo': 'Editar Usuario',
            'accion': 'Actualizar Usuario'
        })
        
    except Exception as e:
        messages.error(request, f'Error al editar usuario: {str(e)}')
        return redirect('usuarios:lista_usuarios')

@login_required
def detalle_usuario(request, usuario_id):
    """Ver detalles de un usuario específico"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.nombreUsuario, u.nombreCompleto, u.email, 
                       r.nombre as rol, u.activo, u.anulado, u.CreadoDate,
                        r.descripcion as rol_descripcion
                FROM usuarios u
                LEFT JOIN roles r ON u.idRol = r.id
                WHERE u.id = %s
            """, [usuario_id])
            
            row = cursor.fetchone()
            if not row:
                messages.error(request, 'Usuario no encontrado.')
                return redirect('usuarios:lista_usuarios')
            
            usuario = {
                'id': row[0],
                'nombre_usuario': row[1],
                'nombre_completo': row[2],
                'email': row[3],
                'rol': row[4] or 'Sin rol',
                'activo': bool(row[5]),
                'anulado': bool(row[6]),
                'creado_date': row[7],
                'rol_descripcion': row[8]
            }
        
        return render(request, 'usuarios/detalle_usuario.html', {'usuario': usuario})
        
    except Exception as e:
        messages.error(request, f'Error al cargar usuario: {str(e)}')
        return redirect('usuarios:lista_usuarios')

@login_required
def cambiar_estado_usuario(request, usuario_id):
    """Cambiar estado activo/inactivo de un usuario"""
    try:
        with connection.cursor() as cursor:
            # Obtener estado actual
            cursor.execute("SELECT nombreCompleto, activo FROM usuarios WHERE id = %s", [usuario_id])
            row = cursor.fetchone()
            
            if not row:
                messages.error(request, 'Usuario no encontrado.')
                return redirect('usuarios:lista_usuarios')
            
            nombre_completo = row[0]
            estado_actual = bool(row[1])
            nuevo_estado = not estado_actual
            
            # Cambiar estado
            cursor.execute("UPDATE usuarios SET activo = %s WHERE id = %s", 
                         [nuevo_estado, usuario_id])
            
            if nuevo_estado:
                messages.success(request, f'Usuario {nombre_completo} activado exitosamente.')
            else:
                messages.warning(request, f'Usuario {nombre_completo} desactivado exitosamente.')
    
    except Exception as e:
        messages.error(request, f'Error al cambiar estado: {str(e)}')
    
    return redirect('usuarios:lista_usuarios')

@login_required
def anular_usuario(request, usuario_id):
    """Anular un usuario (soft delete)"""
    try:
        with connection.cursor() as cursor:
            # Obtener datos del usuario
            cursor.execute("SELECT nombreCompleto, anulado FROM usuarios WHERE id = %s", [usuario_id])
            row = cursor.fetchone()
            
            if not row:
                messages.error(request, 'Usuario no encontrado.')
                return redirect('usuarios:lista_usuarios')
            
            nombre_completo = row[0]
            ya_anulado = bool(row[1])
            
            if ya_anulado:
                messages.warning(request, f'El usuario {nombre_completo} ya está anulado.')
            else:
                # Anular usuario
                cursor.execute("UPDATE usuarios SET anulado = 1, activo = 0 WHERE id = %s", 
                             [usuario_id])
                messages.success(request, f'Usuario {nombre_completo} anulado exitosamente.')
    
    except Exception as e:
        messages.error(request, f'Error al anular usuario: {str(e)}')
    
    return redirect('usuarios:lista_usuarios')

# Gestión de roles
@login_required
def lista_roles(request):
    """Lista todos los roles del sistema con sus permisos"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.id, r.nombre, r.descripcion, (NOT r.anulado) as activo, r.creadoDate,
                       COUNT(DISTINCT u.id) as total_usuarios,
                       COUNT(DISTINCT rp.id) as total_permisos
                FROM roles r
                LEFT JOIN usuarios u ON r.id = u.idRol AND u.anulado = 0
                LEFT JOIN rol_permisos rp ON r.id = rp.idRol
                GROUP BY r.id, r.nombre, r.descripcion, r.anulado, r.creadoDate
                ORDER BY r.nombre
            """)
            
            roles = []
            for row in cursor.fetchall():
                roles.append({
                    'id': row[0],
                    'nombre': row[1],
                    'descripcion': row[2],
                    'activo': bool(row[3]),
                    'fecha_creacion': row[4],
                    'total_usuarios': row[5],
                    'total_permisos': row[6] or 0
                })
        
        return render(request, 'usuarios/lista_roles.html', {
            'roles': roles,
            'titulo': 'Gestión de Roles'
        })
        
    except Exception as e:
        print(f"Error en lista_roles: {e}")
        messages.error(request, f'Error al cargar roles: {str(e)}')
        return redirect('usuarios:dashboard')
        messages.error(request, f'Error al cargar roles: {str(e)}')
        return redirect('usuarios:dashboard')

@login_required
def crear_rol(request):
    """Crear nuevo rol con permisos"""
    # Definir todos los permisos disponibles organizados por módulo
    PERMISOS_DISPONIBLES = {
        'productos': [
            {'nombre': 'listar_productos', 'descripcion': 'Ver lista de productos'},
            {'nombre': 'crear_producto', 'descripcion': 'Crear productos'},
            {'nombre': 'editar_producto', 'descripcion': 'Editar productos'},
            {'nombre': 'eliminar_producto', 'descripcion': 'Eliminar productos'},
        ],
        'ventas': [
            {'nombre': 'crear_venta', 'descripcion': 'Crear ventas'},
            {'nombre': 'listar_ventas', 'descripcion': 'Ver historial de ventas'},
            {'nombre': 'anular_venta', 'descripcion': 'Anular ventas'},
        ],
        'caja': [
            {'nombre': 'abrir_caja', 'descripcion': 'Abrir caja'},
            {'nombre': 'cerrar_caja', 'descripcion': 'Cerrar caja'},
            {'nombre': 'movimientos_caja', 'descripcion': 'Ver movimientos de caja'},
        ],
        'clientes': [
            {'nombre': 'listar_clientes', 'descripcion': 'Ver lista de clientes'},
            {'nombre': 'crear_cliente', 'descripcion': 'Crear clientes'},
            {'nombre': 'editar_cliente', 'descripcion': 'Editar clientes'},
        ],
        'inventario': [
            {'nombre': 'kardex', 'descripcion': 'Ver kardex'},
            {'nombre': 'ajustes', 'descripcion': 'Realizar ajustes de inventario'},
            {'nombre': 'stock_minimo', 'descripcion': 'Configurar stock mínimo'},
            {'nombre': 'transferencias', 'descripcion': 'Gestionar transferencias'},
            {'nombre': 'ubicaciones', 'descripcion': 'Gestionar ubicaciones'},
        ],
        'proveedores': [
            {'nombre': 'listar_proveedores', 'descripcion': 'Ver lista de proveedores'},
            {'nombre': 'crear_proveedor', 'descripcion': 'Crear proveedores'},
        ],
        'cotizaciones': [
            {'nombre': 'crear_cotizacion', 'descripcion': 'Crear cotizaciones'},
            {'nombre': 'listar_cotizaciones', 'descripcion': 'Ver cotizaciones'},
        ],
        'reportes': [
            {'nombre': 'ventas', 'descripcion': 'Reportes de ventas'},
            {'nombre': 'productos_caducados', 'descripcion': 'Productos caducados'},
            {'nombre': 'inventario', 'descripcion': 'Reporte de inventario'},
            {'nombre': 'kardex', 'descripcion': 'Reporte de kardex'},
        ],
        'contabilidad': [
            {'nombre': 'gastos', 'descripcion': 'Gestionar gastos'},
            {'nombre': 'cuentas_por_cobrar', 'descripcion': 'Cuentas por cobrar'},
            {'nombre': 'cuentas_por_pagar', 'descripcion': 'Cuentas por pagar'},
        ],
        'usuarios': [
            {'nombre': 'listar_usuarios', 'descripcion': 'Ver usuarios'},
            {'nombre': 'crear_usuario', 'descripcion': 'Crear usuarios'},
            {'nombre': 'editar_usuario', 'descripcion': 'Editar usuarios'},
            {'nombre': 'gestionar_permisos', 'descripcion': 'Gestionar permisos'},
        ],
        'roles': [
            {'nombre': 'listar_roles', 'descripcion': 'Ver roles'},
            {'nombre': 'crear_rol', 'descripcion': 'Crear roles'},
            {'nombre': 'editar_rol', 'descripcion': 'Editar roles'},
        ],
    }
    
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion', '')
            
            if not nombre:
                messages.error(request, 'El nombre del rol es obligatorio.')
                return redirect('usuarios:crear_rol')
            
            usuario_id = request.session.get('usuario_sistema_id')
            
            with connection.cursor() as cursor:
                # Verificar si ya existe
                cursor.execute("SELECT id FROM roles WHERE nombre = %s AND anulado = 0", [nombre])
                if cursor.fetchone():
                    messages.error(request, 'Ya existe un rol con ese nombre.')
                    return redirect('usuarios:crear_rol')
                
                # Crear rol
                cursor.execute("""
                    INSERT INTO roles (nombre, descripcion, anulado, creadoPor, creadoDate)
                    VALUES (%s, %s, 0, %s, NOW())
                """, [nombre, descripcion, usuario_id])
                
                # Obtener el ID del rol recién creado
                cursor.execute("SELECT LAST_INSERT_ID()")
                rol_id = cursor.fetchone()[0]
                
                # Insertar permisos seleccionados
                for modulo, permisos in PERMISOS_DISPONIBLES.items():
                    for permiso_item in permisos:
                        permiso_key = permiso_item['nombre']
                        
                        # Verificar si el checkbox está marcado
                        if request.POST.get(f'permiso_{modulo}_{permiso_key}'):
                            puede_ver = request.POST.get(f'ver_{modulo}_{permiso_key}') == 'on'
                            puede_crear = request.POST.get(f'crear_{modulo}_{permiso_key}') == 'on'
                            puede_editar = request.POST.get(f'editar_{modulo}_{permiso_key}') == 'on'
                            puede_eliminar = request.POST.get(f'eliminar_{modulo}_{permiso_key}') == 'on'
                            
                            cursor.execute("""
                                INSERT INTO rol_permisos 
                                (idRol, modulo, permiso, puede_ver, puede_crear, puede_editar, puede_eliminar, creadoPor, creadoDate)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            """, [rol_id, modulo, permiso_key, puede_ver, puede_crear, puede_editar, puede_eliminar, usuario_id])
                
                messages.success(request, f'Rol {nombre} creado exitosamente.')
                return redirect('usuarios:lista_roles')
                
        except Exception as e:
            messages.error(request, f'Error al crear rol: {str(e)}')
            print(f"Error detallado: {e}")
    
    return render(request, 'usuarios/crear_rol.html', {
        'permisos_disponibles': PERMISOS_DISPONIBLES
    })

@login_required
def editar_rol(request, rol_id):
    """Editar rol existente con sus permisos"""
    PERMISOS_DISPONIBLES = {
        'productos': [
            {'nombre': 'listar_productos', 'descripcion': 'Ver lista de productos'},
            {'nombre': 'crear_producto', 'descripcion': 'Crear productos'},
            {'nombre': 'editar_producto', 'descripcion': 'Editar productos'},
            {'nombre': 'eliminar_producto', 'descripcion': 'Eliminar productos'},
        ],
        'ventas': [
            {'nombre': 'crear_venta', 'descripcion': 'Crear ventas'},
            {'nombre': 'listar_ventas', 'descripcion': 'Ver historial de ventas'},
            {'nombre': 'anular_venta', 'descripcion': 'Anular ventas'},
        ],
        'caja': [
            {'nombre': 'abrir_caja', 'descripcion': 'Abrir caja'},
            {'nombre': 'cerrar_caja', 'descripcion': 'Cerrar caja'},
            {'nombre': 'movimientos_caja', 'descripcion': 'Ver movimientos de caja'},
        ],
        'clientes': [
            {'nombre': 'listar_clientes', 'descripcion': 'Ver lista de clientes'},
            {'nombre': 'crear_cliente', 'descripcion': 'Crear clientes'},
            {'nombre': 'editar_cliente', 'descripcion': 'Editar clientes'},
        ],
        'inventario': [
            {'nombre': 'kardex', 'descripcion': 'Ver kardex'},
            {'nombre': 'ajustes', 'descripcion': 'Realizar ajustes de inventario'},
            {'nombre': 'stock_minimo', 'descripcion': 'Configurar stock mínimo'},
            {'nombre': 'transferencias', 'descripcion': 'Gestionar transferencias'},
            {'nombre': 'ubicaciones', 'descripcion': 'Gestionar ubicaciones'},
        ],
        'proveedores': [
            {'nombre': 'listar_proveedores', 'descripcion': 'Ver lista de proveedores'},
            {'nombre': 'crear_proveedor', 'descripcion': 'Crear proveedores'},
        ],
        'cotizaciones': [
            {'nombre': 'crear_cotizacion', 'descripcion': 'Crear cotizaciones'},
            {'nombre': 'listar_cotizaciones', 'descripcion': 'Ver cotizaciones'},
        ],
        'reportes': [
            {'nombre': 'ventas', 'descripcion': 'Reportes de ventas'},
            {'nombre': 'productos_caducados', 'descripcion': 'Productos caducados'},
            {'nombre': 'inventario', 'descripcion': 'Reporte de inventario'},
            {'nombre': 'kardex', 'descripcion': 'Reporte de kardex'},
        ],
        'contabilidad': [
            {'nombre': 'gastos', 'descripcion': 'Gestionar gastos'},
            {'nombre': 'cuentas_por_cobrar', 'descripcion': 'Cuentas por cobrar'},
            {'nombre': 'cuentas_por_pagar', 'descripcion': 'Cuentas por pagar'},
        ],
        'usuarios': [
            {'nombre': 'listar_usuarios', 'descripcion': 'Ver usuarios'},
            {'nombre': 'crear_usuario', 'descripcion': 'Crear usuarios'},
            {'nombre': 'editar_usuario', 'descripcion': 'Editar usuarios'},
            {'nombre': 'gestionar_permisos', 'descripcion': 'Gestionar permisos'},
        ],
        'roles': [
            {'nombre': 'listar_roles', 'descripcion': 'Ver roles'},
            {'nombre': 'crear_rol', 'descripcion': 'Crear roles'},
            {'nombre': 'editar_rol', 'descripcion': 'Editar roles'},
        ],
    }
    
    try:
        # Obtener datos del rol
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, nombre, descripcion, (NOT anulado) as activo FROM roles WHERE id = %s", [rol_id])
            row = cursor.fetchone()
            
            if not row:
                messages.error(request, 'Rol no encontrado.')
                return redirect('usuarios:lista_roles')
            
            rol = {
                'id': row[0],
                'nombre': row[1],
                'descripcion': row[2],
                'activo': bool(row[3])
            }
            
            # Obtener permisos actuales del rol
            cursor.execute("""
                SELECT modulo, permiso, puede_ver, puede_crear, puede_editar, puede_eliminar
                FROM rol_permisos
                WHERE idRol = %s
            """, [rol_id])
            
            permisos_actuales = {}
            for perm_row in cursor.fetchall():
                key = f"{perm_row[0]}_{perm_row[1]}"
                permisos_actuales[key] = {
                    'ver': bool(perm_row[2]),
                    'crear': bool(perm_row[3]),
                    'editar': bool(perm_row[4]),
                    'eliminar': bool(perm_row[5])
                }
        
        if request.method == 'POST':
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion', '')
            usuario_id = request.session.get('usuario_sistema_id')
            
            with connection.cursor() as cursor:
                # Verificar nombre único (excluyendo el rol actual)
                cursor.execute("SELECT id FROM roles WHERE nombre = %s AND id != %s AND anulado = 0", 
                             [nombre, rol_id])
                if cursor.fetchone():
                    messages.error(request, 'Ya existe otro rol con ese nombre.')
                    return redirect('usuarios:editar_rol', rol_id=rol_id)
                
                # Actualizar rol
                cursor.execute("""
                    UPDATE roles 
                    SET nombre = %s, descripcion = %s, editadoPor = %s, editadoDate = NOW()
                    WHERE id = %s
                """, [nombre, descripcion, usuario_id, rol_id])
                
                # Eliminar permisos antiguos
                cursor.execute("DELETE FROM rol_permisos WHERE idRol = %s", [rol_id])
                
                # Insertar nuevos permisos
                for modulo, permisos in PERMISOS_DISPONIBLES.items():
                    for permiso_item in permisos:
                        permiso_key = permiso_item['nombre']
                        
                        if request.POST.get(f'permiso_{modulo}_{permiso_key}'):
                            puede_ver = request.POST.get(f'ver_{modulo}_{permiso_key}') == 'on'
                            puede_crear = request.POST.get(f'crear_{modulo}_{permiso_key}') == 'on'
                            puede_editar = request.POST.get(f'editar_{modulo}_{permiso_key}') == 'on'
                            puede_eliminar = request.POST.get(f'eliminar_{modulo}_{permiso_key}') == 'on'
                            
                            cursor.execute("""
                                INSERT INTO rol_permisos 
                                (idRol, modulo, permiso, puede_ver, puede_crear, puede_editar, puede_eliminar, creadoPor, creadoDate)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            """, [rol_id, modulo, permiso_key, puede_ver, puede_crear, puede_editar, puede_eliminar, usuario_id])
                
                messages.success(request, f'Rol {nombre} actualizado exitosamente.')
                return redirect('usuarios:lista_roles')
        
        # Convertir permisos_actuales a JSON para JavaScript
        import json
        permisos_actuales_json = json.dumps(permisos_actuales)
        
        return render(request, 'usuarios/editar_rol.html', {
            'rol': rol,
            'permisos_disponibles': PERMISOS_DISPONIBLES,
            'permisos_actuales': permisos_actuales_json
        })
        
    except Exception as e:
        messages.error(request, f'Error al editar rol: {str(e)}')
        print(f"Error detallado: {e}")
        return redirect('usuarios:lista_roles')

@login_required
def lista_auditoria(request):
    """Lista todos los registros de auditoría con filtros y paginación"""
    try:
        from django.core.paginator import Paginator
        
        # Obtener parámetros de filtro
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        usuario_filtro = request.GET.get('usuario', '')
        modulo_filtro = request.GET.get('modulo', '')
        accion_filtro = request.GET.get('accion', '')
        page_number = request.GET.get('page', 1)
        
        # Construir query con filtros
        query = """
            SELECT a.id, a.fecha, a.usuario, a.modulo, a.accion, a.entidad, 
                   a.idEntidad, a.descripcion, a.ip, a.origen
            FROM auditoria a
            WHERE 1=1
        """
        params = []
        
        if fecha_desde:
            query += " AND DATE(a.fecha) >= %s"
            params.append(fecha_desde)
        
        if fecha_hasta:
            query += " AND DATE(a.fecha) <= %s"
            params.append(fecha_hasta)
        
        if usuario_filtro:
            query += " AND a.usuario LIKE %s"
            params.append(f'%{usuario_filtro}%')
        
        if modulo_filtro:
            query += " AND a.modulo = %s"
            params.append(modulo_filtro)
        
        if accion_filtro:
            query += " AND a.accion = %s"
            params.append(accion_filtro)
        
        query += " ORDER BY a.fecha DESC"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            
            registros = []
            for row in cursor.fetchall():
                registros.append({
                    'id': row[0],
                    'fecha': row[1],
                    'usuario': row[2],
                    'modulo': row[3],
                    'accion': row[4],
                    'entidad': row[5],
                    'id_entidad': row[6],
                    'descripcion': row[7],
                    'ip': row[8],
                    'origen': row[9],
                })
            
            # Obtener listado de módulos y acciones para filtros
            cursor.execute("SELECT DISTINCT modulo FROM auditoria ORDER BY modulo")
            modulos = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT DISTINCT accion FROM auditoria WHERE accion IS NOT NULL ORDER BY accion")
            acciones = [row[0] for row in cursor.fetchall()]
        
        # Aplicar paginación
        paginator = Paginator(registros, 50)  # 50 registros por página
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'usuarios/lista_auditoria.html', {
            'page_obj': page_obj,
            'modulos': modulos,
            'acciones': acciones,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'usuario_filtro': usuario_filtro,
            'modulo_filtro': modulo_filtro,
            'accion_filtro': accion_filtro,
            'total_registros': len(registros),
        })
        
    except Exception as e:
        messages.error(request, f'Error al cargar auditoría: {str(e)}')
        print(f"Error en lista_auditoria: {e}")
        return redirect('usuarios:dashboard')

@login_required
def detalle_auditoria(request, auditoria_id):
    """Muestra el detalle completo de un registro de auditoría"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT a.id, a.fecha, a.idUsuario, a.usuario, a.modulo, a.accion,
                       a.entidad, a.idEntidad, a.descripcion, a.ip, a.host, 
                       a.origen, a.extra
                FROM auditoria a
                WHERE a.id = %s
            """, [auditoria_id])
            
            row = cursor.fetchone()
            if not row:
                messages.error(request, 'Registro de auditoría no encontrado')
                return redirect('usuarios:lista_auditoria')
            
            registro = {
                'id': row[0],
                'fecha': row[1],
                'id_usuario': row[2],
                'usuario': row[3],
                'modulo': row[4],
                'accion': row[5],
                'entidad': row[6],
                'id_entidad': row[7],
                'descripcion': row[8],
                'ip': row[9],
                'host': row[10],
                'origen': row[11],
                'extra': row[12],
            }
            
            # Parsear extra si es JSON
            if registro['extra']:
                try:
                    import json
                    registro['extra_json'] = json.loads(registro['extra'])
                except:
                    registro['extra_json'] = None
        
        return render(request, 'usuarios/detalle_auditoria.html', {'registro': registro})
        
    except Exception as e:
        messages.error(request, f'Error al cargar detalle: {str(e)}')
        return redirect('usuarios:lista_auditoria')

@login_required
def perfil_usuario(request):
    """Ver y editar perfil del usuario actual"""
    try:
        if not hasattr(request.user, 'usuario_sistema_id'):
            messages.error(request, 'No se pudo acceder al perfil.')
            return redirect('usuarios:dashboard')
            
        usuario_id = request.user.usuario_sistema_id
        
        # Obtener datos del usuario actual
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.nombreUsuario, u.nombreCompleto, u.email, 
                       r.nombre as rol, u.CreadoDate,
                       r.descripcion as rol_descripcion
                FROM usuarios u
                LEFT JOIN roles r ON u.idRol = r.id
                WHERE u.id = %s
            """, [usuario_id])
            
            row = cursor.fetchone()
            if not row:
                messages.error(request, 'No se encontró información del usuario.')
                return redirect('usuarios:dashboard')
            
            usuario = {
                'id': row[0],
                'nombre_usuario': row[1],
                'nombre_completo': row[2],
                'email': row[3],
                'rol': row[4] or 'Sin rol',
                'creado_date': row[5],
                'rol_descripcion': row[6] if len(row) > 6 else ''
            }
        
        if request.method == 'POST':
            nombre_completo = request.POST.get('nombre_completo')
            email = request.POST.get('email')
            password_actual = request.POST.get('password_actual')
            nueva_password = request.POST.get('nueva_password')
            confirmar_password = request.POST.get('confirmar_password')
            
            # Validaciones
            if not all([nombre_completo, email]):
                messages.error(request, 'Nombre completo y email son obligatorios.')
                return redirect('usuarios:perfil_usuario')
            
            # Si quiere cambiar contraseña
            if nueva_password:
                if not password_actual:
                    messages.error(request, 'Debes proporcionar tu contraseña actual.')
                    return redirect('usuarios:perfil_usuario')
                
                if nueva_password != confirmar_password:
                    messages.error(request, 'Las nuevas contraseñas no coinciden.')
                    return redirect('usuarios:perfil_usuario')
                
                # Verificar contraseña actual
                import hashlib
                password_hash_actual = hashlib.sha256(password_actual.encode()).hexdigest()
                
                with connection.cursor() as cursor:
                    cursor.execute("SELECT password FROM usuarios WHERE id = %s", [usuario_id])
                    password_bd = cursor.fetchone()[0]
                    
                    # Verificar tanto SHA-256 como Django hash
                    from django.contrib.auth.hashers import check_password
                    password_valida = (password_bd == password_hash_actual or 
                                     check_password(password_actual, password_bd))
                    
                    if not password_valida:
                        messages.error(request, 'La contraseña actual es incorrecta.')
                        return redirect('usuarios:perfil_usuario')
                    
                    # Actualizar con nueva contraseña
                    nueva_password_hash = hashlib.sha256(nueva_password.encode()).hexdigest()
                    cursor.execute("""
                        UPDATE usuarios 
                        SET nombreCompleto = %s, email = %s, password = %s
                        WHERE id = %s
                    """, [nombre_completo, email, nueva_password_hash, usuario_id])
                    
                    messages.success(request, 'Perfil y contraseña actualizados exitosamente.')
            else:
                # Solo actualizar perfil
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE usuarios 
                        SET nombreCompleto = %s, email = %s
                        WHERE id = %s
                    """, [nombre_completo, email, usuario_id])
                    
                    messages.success(request, 'Perfil actualizado exitosamente.')
            
            return redirect('usuarios:perfil_usuario')
        
        return render(request, 'usuarios/perfil_usuario.html', {'usuario': usuario})
        
    except Exception as e:
        messages.error(request, f'Error al cargar perfil: {str(e)}')
        return redirect('usuarios:dashboard')

def cambiar_password(request):
    """Redirigir al perfil para cambiar contraseña"""
    messages.info(request, 'Puedes cambiar tu contraseña desde tu perfil.')
    return redirect('usuarios:perfil_usuario')


@login_required
def usuario_info(request):
    """API endpoint para obtener información del usuario actual"""
    if not hasattr(request.user, 'usuario_sistema_id'):
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                 SELECT u.nombreCompleto, u.email, u.nombreUsuario, r.nombre as rol,
                       u.CreadoDate
                FROM usuarios u
                LEFT JOIN roles r ON u.idRol = r.id
                WHERE u.id = %s AND u.activo = 1
            """, [request.user.usuario_sistema_id])
            
            row = cursor.fetchone()
            if row:
                usuario_data = {
                    'nombre_completo': row[0],
                    'email': row[1],
                    'usuario': row[2],
                    'rol': row[3] or 'Sin rol asignado',
                    'creado_date': row[4].strftime('%d/%m/%Y') if row[4] else ''
                }
                
                return JsonResponse({
                    'success': True,
                    'usuario': usuario_data
                })
            else:
                return JsonResponse({'success': False, 'error': 'Usuario no encontrado en la base de datos'})
                
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def configuracion_empresa(request):
    """Configuración de la empresa usando tabla empresas existente"""
    try:
        # Obtener o crear configuración de empresa
        config = ConfiguracionEmpresa.obtener_configuracion()
        
        if not config:
            # Crear configuración por defecto si no existe
            config = ConfiguracionEmpresa.objects.create(
                ruc="",
                razon_social="Mi Empresa",
                nombre_comercial="Mi Empresa",
                direccion_matriz="",
                telefono="",
                email="",
                activo=True
            )
        
        if request.method == 'POST':
            form = ConfiguracionEmpresaForm(request.POST, request.FILES, instance=config)
            if form.is_valid():
                form.save()
                messages.success(request, 'Configuración de empresa actualizada exitosamente.')
                return redirect('usuarios:configuracion_empresa')
            else:
                messages.error(request, 'Por favor corrige los errores en el formulario.')
        else:
            form = ConfiguracionEmpresaForm(instance=config)
        
        context = {
            'form': form,
            'config': config,
            'titulo': 'Configuración de Empresa'
        }
        
        return render(request, 'configuracion/empresa_nueva_ui.html', context)
        
    except Exception as e:
        messages.error(request, f'Error en configuración de empresa: {str(e)}')
        return redirect('usuarios:dashboard')

# Función de test para verificar acceso
def test_usuarios(request):
    """Vista de test sin autenticación requerida"""
    try:
        with connection.cursor() as cursor:
            # Verificar conexión y tabla
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            total_usuarios_db = cursor.fetchone()[0]
            
            # Obtener primeros 3 usuarios
            cursor.execute("""
                SELECT u.id, u.nombreUsuario, u.nombreCompleto, u.email, 
                       r.nombre as rol, u.activo, u.anulado
                FROM usuarios u
                LEFT JOIN roles r ON u.idRol = r.id
                ORDER BY u.id DESC
                LIMIT 3
            """)
            
            usuarios = []
            for row in cursor.fetchall():
                usuarios.append({
                    'id': row[0],
                    'nombre_usuario': row[1],
                    'nombre_completo': row[2],
                    'email': row[3],
                    'rol': row[4] or 'Sin rol',
                    'activo': row[5],
                    'anulado': row[6],
                })
        
        return render(request, 'usuarios/test.html', {
            'usuario_autenticado': request.user.is_authenticated,
            'usuario_id': getattr(request.user, 'usuario_sistema_id', 'No disponible'),
            'usuario_nombre': getattr(request.user, 'username', 'No disponible'),
            'total_usuarios_db': total_usuarios_db,
            'usuarios_muestra': usuarios
        })
        
    except Exception as e:
        return render(request, 'usuarios/test.html', {
            'usuario_autenticado': request.user.is_authenticated,
            'error': str(e),
            'total_usuarios_db': 0,
            'usuarios_muestra': []
        })

# Versión de test de lista_usuarios sin @login_required
def lista_usuarios_debug(request):
    """Lista todos los usuarios - versión debug"""
    print("DEBUG: Iniciando lista_usuarios_debug")
    try:
        with connection.cursor() as cursor:
            # Verificar que existan las tablas
            cursor.execute("SHOW TABLES LIKE 'usuarios'")
            usuarios_table = cursor.fetchone()
            print(f"DEBUG: Tabla usuarios existe: {usuarios_table is not None}")
            
            cursor.execute("SHOW TABLES LIKE 'roles'")
            roles_table = cursor.fetchone()
            print(f"DEBUG: Tabla roles existe: {roles_table is not None}")
            
            # Consulta simple primero
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            total = cursor.fetchone()[0]
            print(f"DEBUG: Total usuarios en DB: {total}")
            
            # Consulta completa
            cursor.execute("""
                SELECT u.id, u.nombreUsuario, u.nombreCompleto, u.email, 
                       r.nombre as rol, u.activo, u.anulado
                FROM usuarios u
                LEFT JOIN roles r ON u.idRol = r.id
                ORDER BY u.id DESC
            """)
            
            usuarios = []
            rows = cursor.fetchall()
            print(f"DEBUG: Encontradas {len(rows)} filas en la consulta")
            
            for row in rows:
                print(f"DEBUG: Procesando usuario: {row}")
                usuarios.append({
                    'id': row[0],
                    'nombre_usuario': row[1],
                    'nombre_completo': row[2],
                    'email': row[3],
                    'rol': row[4] or 'Sin rol',
                    'activo': bool(row[5]) if row[5] is not None else True,
                    'anulado': bool(row[6]) if row[6] is not None else False,
                    'fecha_creacion': None,
                    'ultimo_acceso': None
                })
        
        print(f"DEBUG: Total usuarios procesados: {len(usuarios)}")
        
        context = {
            'usuarios': usuarios,
            'total_usuarios': len(usuarios),
            'activos': len([u for u in usuarios if u['activo'] and not u['anulado']]),
            'inactivos': len([u for u in usuarios if not u['activo'] or u['anulado']]),
            'debug_info': {
                'usuarios_table': usuarios_table is not None,
                'roles_table': roles_table is not None,
                'total_db': total
            }
        }
        
        print(f"DEBUG: Enviando contexto con {len(usuarios)} usuarios")
        
        return render(request, 'usuarios/debug.html', context)
        
    except Exception as e:
        print(f"DEBUG: Error en lista_usuarios_debug: {str(e)}")
        import traceback
        traceback.print_exc()
        return render(request, 'usuarios/debug.html', {
            'usuarios': [],
            'total_usuarios': 0,
            'error': str(e)
        })