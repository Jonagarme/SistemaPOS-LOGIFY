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
                
                # Guardar información del usuario en sesión para modo offline
                request.session['usuario_offline'] = {
                    'id': user.id,
                    'username': user.username,
                    'nombre_completo': nombre_completo,
                    'rol_nombre': rol_nombre,
                    'usuario_sistema_id': getattr(user, 'usuario_sistema_id', None)
                }
                
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
                messages.error(request, 'Usuario o contraseña incorrectos, o tu cuenta está desactivada.')
        else:
            messages.error(request, 'Por favor, completa todos los campos.')
    
    return render(request, 'usuarios/custom_login.html')


def custom_logout(request):
    """Vista de logout personalizada con mensaje personalizado"""
    nombre_usuario = ""
    rol_usuario = ""
    
    # Obtener información del usuario antes del logout
    if request.user.is_authenticated:
        if hasattr(request.user, 'nombre_completo'):
            nombre_usuario = request.user.nombre_completo
        else:
            nombre_usuario = request.user.get_full_name() or request.user.username
        
        # Obtener rol si está disponible
        if hasattr(request.user, 'rol_nombre'):
            rol_usuario = request.user.rol_nombre
        
        # Si tenemos ID del usuario del sistema, obtener datos actualizados
        if hasattr(request.user, 'usuario_sistema_id'):
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
    """Lista todos los roles del sistema"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.id, r.nombre, r.descripcion, (NOT r.anulado) as activo, r.creadoDate,
                       COUNT(u.id) as total_usuarios
                FROM roles r
                LEFT JOIN usuarios u ON r.id = u.idRol AND u.anulado = 0
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
                    'total_usuarios': row[5]
                })
        
        return render(request, 'usuarios/lista_roles.html', {'roles': roles})
        
    except Exception as e:
        messages.error(request, f'Error al cargar roles: {str(e)}')
        return redirect('usuarios:dashboard')

@login_required
def crear_rol(request):
    """Crear nuevo rol"""
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion', '')
            
            if not nombre:
                messages.error(request, 'El nombre del rol es obligatorio.')
                return redirect('usuarios:crear_rol')
            
            with connection.cursor() as cursor:
                # Verificar si ya existe
                cursor.execute("SELECT id FROM roles WHERE nombre = %s", [nombre])
                if cursor.fetchone():
                    messages.error(request, 'Ya existe un rol con ese nombre.')
                    return redirect('usuarios:crear_rol')
                
                # Crear rol
                cursor.execute("""
                    INSERT INTO roles (nombre, descripcion, anulado, creadoDate)
                    VALUES (%s, %s, 0, NOW())
                """, [nombre, descripcion])
                
                messages.success(request, f'Rol {nombre} creado exitosamente.')
                return redirect('usuarios:lista_roles')
                
        except Exception as e:
            messages.error(request, f'Error al crear rol: {str(e)}')
    
    return render(request, 'usuarios/crear_rol.html')

@login_required
def editar_rol(request, rol_id):
    """Editar rol existente"""
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
        
        if request.method == 'POST':
            nombre = request.POST.get('nombre')
            descripcion = request.POST.get('descripcion', '')
            activo = request.POST.get('activo') == 'on'
            
            with connection.cursor() as cursor:
                # Verificar nombre único (excluyendo el rol actual)
                cursor.execute("SELECT id FROM roles WHERE nombre = %s AND id != %s", 
                             [nombre, rol_id])
                if cursor.fetchone():
                    messages.error(request, 'Ya existe otro rol con ese nombre.')
                    return redirect('usuarios:editar_rol', rol_id=rol_id)
                
                # Actualizar rol
                cursor.execute("""
                    UPDATE roles 
                    SET nombre = %s, descripcion = %s, activo = %s
                    WHERE id = %s
                """, [nombre, descripcion, activo, rol_id])
                
                messages.success(request, f'Rol {nombre} actualizado exitosamente.')
                return redirect('usuarios:lista_roles')
        
        return render(request, 'usuarios/editar_rol.html', {'rol': rol})
        
    except Exception as e:
        messages.error(request, f'Error al editar rol: {str(e)}')
        return redirect('usuarios:lista_roles')

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