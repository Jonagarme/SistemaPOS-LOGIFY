from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash, authenticate, login, logout
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from .models import PerfilUsuario, ConfiguracionEmpresa, Rol, Usuario
from .forms import PerfilUsuarioForm, ConfiguracionEmpresaForm, CustomPasswordChangeForm, RolForm

# NOTA: Funciones que usan UsuarioSistema están temporalmente comentadas 
# hasta completar la migración al modelo Usuario personalizado


@login_required
def dashboard(request):
    """Dashboard principal del sistema"""
    from django.db import connection
    from datetime import datetime, date
    from productos.models import Producto
    from ventas.models import FacturaVenta
    
    # Verificar si hay una caja abierta para el usuario actual
    caja_abierta = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, idCaja FROM cierres_caja 
                WHERE idUsuarioApertura = %s AND estado = 'ABIERTA'
            """, [request.user.id])
            caja_data = cursor.fetchone()
            if caja_data:
                caja_abierta = {'id': caja_data[0], 'idCaja': caja_data[1]}
    except Exception:
        caja_abierta = None
    
    # Obtener datos reales del dashboard
    hoy = date.today()
    
    # Ventas de hoy usando SQL directo
    ventas_hoy = 0
    total_ventas_hoy = 0
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(total), 0) 
                FROM facturas_venta 
                WHERE DATE(fechaEmision) = %s AND estado != 'ANULADA' AND anulado = 0
            """, [hoy])
            result = cursor.fetchone()
            if result:
                ventas_hoy = result[0] or 0
                total_ventas_hoy = float(result[1] or 0)
    except Exception as e:
        print(f"Error obteniendo ventas de hoy: {e}")
    
    # Total de productos activos
    total_productos = 0
    try:
        total_productos = Producto.objects.filter(activo=True, anulado=False).count()
    except Exception as e:
        print(f"Error obteniendo total productos: {e}")
    
    # Productos bajo stock mínimo
    productos_bajo_stock = 0
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM productos 
                WHERE activo = 1 AND anulado = 0 AND stock <= stockMinimo AND stockMinimo > 0
            """)
            result = cursor.fetchone()
            if result:
                productos_bajo_stock = result[0] or 0
    except Exception as e:
        print(f"Error obteniendo productos bajo stock: {e}")
    
    # Últimas 5 ventas
    ultimas_ventas = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT fv.numeroFactura, fv.total, fv.fechaEmision, 
                       COALESCE(CONCAT(c.nombres, ' ', c.apellidos), c.razonSocial, 'Cliente General') as cliente_nombre
                FROM facturas_venta fv
                LEFT JOIN clientes c ON fv.idCliente = c.id
                WHERE fv.estado != 'ANULADA' AND fv.anulado = 0
                ORDER BY fv.fechaEmision DESC 
                LIMIT 5
            """)
            for row in cursor.fetchall():
                ultimas_ventas.append({
                    'numero': row[0],
                    'total': float(row[1]),
                    'fecha': row[2],
                    'cliente': row[3]
                })
    except Exception as e:
        print(f"Error obteniendo últimas ventas: {e}")
        # Si hay error, mostrar datos de ejemplo
        if not ultimas_ventas:
            ultimas_ventas = [
                {
                    'numero': 'Ejemplo-001',
                    'total': 0.00,
                    'fecha': hoy,
                    'cliente': 'No hay ventas registradas'
                }
            ]
    
    # Productos más vendidos (top 5)
    productos_top = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.nombre, SUM(dv.cantidad) as total_vendido, SUM(dv.subtotal) as total_ingresos
                FROM facturas_venta_detalle dv
                INNER JOIN productos p ON dv.idProducto = p.id
                INNER JOIN facturas_venta fv ON dv.idFactura = fv.id
                WHERE fv.estado != 'ANULADA' AND fv.anulado = 0
                  AND DATE(fv.fechaEmision) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY p.id, p.nombre
                ORDER BY total_vendido DESC
                LIMIT 5
            """)
            for row in cursor.fetchall():
                productos_top.append({
                    'nombre': row[0],
                    'cantidad': float(row[1]),
                    'ingresos': float(row[2])
                })
    except Exception as e:
        print(f"Error obteniendo productos top: {e}")
        # Si hay error, mostrar datos de ejemplo
        if not productos_top:
            productos_top = [
                {
                    'nombre': 'No hay datos de ventas',
                    'cantidad': 0,
                    'ingresos': 0.00
                }
            ]
    
    context = {
        'titulo': 'Dashboard',
        'ventas_hoy': ventas_hoy,
        'total_ventas_hoy': total_ventas_hoy,
        'total_productos': total_productos,
        'productos_bajo_stock': productos_bajo_stock,
        'caja_abierta': caja_abierta,
        'ultimas_ventas': ultimas_ventas,
        'productos_top': productos_top
    }
    return render(request, 'dashboard.html', context)


@login_required
def lista_usuarios(request):
    """Lista todos los usuarios del sistema"""
    usuarios = User.objects.filter(is_active=True).select_related('perfilusuario')
    
    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'titulo': 'Usuarios del Sistema'
    }
    return render(request, 'usuarios/lista.html', context)


@login_required
def crear_usuario(request):
    """Crear nuevo usuario"""
    if request.method == 'POST':
        # Lógica para crear usuario
        messages.success(request, 'Usuario creado exitosamente')
        return redirect('usuarios:lista')
    
    context = {
        'titulo': 'Crear Usuario'
    }
    return render(request, 'usuarios/crear.html', context)


@login_required
def editar_usuario(request, pk):
    """Editar usuario existente"""
    usuario = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        # Lógica para editar usuario
        messages.success(request, 'Usuario actualizado exitosamente')
        return redirect('usuarios:lista')
    
    context = {
        'usuario': usuario,
        'titulo': 'Editar Usuario'
    }
    return render(request, 'usuarios/editar.html', context)


@login_required
def detalle_usuario(request, pk):
    """Ver detalles de un usuario"""
    usuario = get_object_or_404(User, pk=pk)
    
    context = {
        'usuario': usuario,
        'titulo': 'Detalle de Usuario'
    }
    return render(request, 'usuarios/detalle.html', context)


@login_required
def perfil_usuario(request):
    """Ver y editar mi perfil"""
    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado exitosamente')
            return redirect('usuarios:perfil')
    else:
        form = PerfilUsuarioForm(instance=request.user)
    
    context = {
        'form': form,
        'titulo': 'Mi Perfil'
    }
    return render(request, 'perfil/perfil.html', context)


@login_required
def cambiar_password(request):
    """Cambiar contraseña del usuario"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantener la sesión activa
            messages.success(request, 'Tu contraseña ha sido actualizada exitosamente')
            return redirect('usuarios:perfil')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'titulo': 'Cambiar Contraseña'
    }
    return render(request, 'perfil/cambiar_password.html', context)


@login_required
def configuracion_empresa(request):
    """Configuración de la empresa - Cargar datos desde tabla empresas"""
    from django.db import connection
    
    # Obtener datos de la tabla empresas
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, ruc, razon_social, nombre_comercial, direccion_matriz, 
                   telefono, email, contribuyente_especial, obligado_contabilidad,
                   activo, creado_en, actualizado_en
            FROM empresas 
            WHERE activo = 1 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        empresa_data = cursor.fetchone()
    
    # Estructura de datos de la empresa
    empresa = None
    if empresa_data:
        empresa = {
            'id': empresa_data[0],
            'ruc': empresa_data[1],
            'razon_social': empresa_data[2], 
            'nombre_comercial': empresa_data[3],
            'direccion_matriz': empresa_data[4],
            'telefono': empresa_data[5],
            'email': empresa_data[6],
            'contribuyente_especial': empresa_data[7],
            'obligado_contabilidad': empresa_data[8],
            'activo': empresa_data[9],
            'creado_en': empresa_data[10],
            'actualizado_en': empresa_data[11],
        }
    
    # Mantener compatibilidad con el formulario original si es necesario
    config = ConfiguracionEmpresa.obtener_configuracion()
    
    if request.method == 'POST':
        form = ConfiguracionEmpresaForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración de empresa actualizada exitosamente')
            return redirect('usuarios:configuracion_empresa')
    else:
        form = ConfiguracionEmpresaForm(instance=config)
    
    context = {
        'form': form,
        'config': config,
        'empresa': empresa,  # Datos de la tabla empresas
        'titulo': 'Configuración de Empresa'
    }
    return render(request, 'configuracion/empresa.html', context)


# Mantener el método anterior para compatibilidad
@login_required
def mi_perfil(request):
    """Redirigir al nuevo método de perfil"""
    return redirect('usuarios:perfil')


def logout_view(request):
    """Vista de logout que acepta tanto GET como POST"""
    from django.contrib.auth import logout
    from django.conf import settings
    
    if request.method == 'POST':
        # Logout por POST (más seguro)
        logout(request)
        messages.success(request, 'Has cerrado sesión exitosamente.')
    elif request.method == 'GET':
        # Logout por GET (para compatibilidad)
        logout(request)
        messages.info(request, 'Sesión cerrada.')
    
    # Redireccionar según configuración
    redirect_url = getattr(settings, 'LOGOUT_REDIRECT_URL', '/usuarios/login/')
    return redirect(redirect_url)


# Vistas para gestión de usuarios del sistema

@login_required
def lista_usuarios(request):
    """Lista de usuarios del sistema con búsqueda y paginación"""
    search = request.GET.get('search', '')
    rol_filter = request.GET.get('rol', '')
    estado_filter = request.GET.get('estado', '')
    
    # Consulta base
    usuarios = UsuarioSistema.objects.select_related('id_rol').all()
    
    # Filtros
    if search:
        usuarios = usuarios.filter(
            Q(nombre_usuario__icontains=search) |
            Q(nombre_completo__icontains=search) |
            Q(email__icontains=search)
        )
    
    if rol_filter:
        usuarios = usuarios.filter(id_rol__id=rol_filter)
    
    if estado_filter == 'activo':
        usuarios = usuarios.filter(activo=True, anulado=False)
    elif estado_filter == 'inactivo':
        usuarios = usuarios.filter(activo=False, anulado=False)
    elif estado_filter == 'anulado':
        usuarios = usuarios.filter(anulado=True)
    
    # Ordenar por fecha de creación descendente
    usuarios = usuarios.order_by('-creado_date')
    
    # Paginación
    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener roles para el filtro
    roles = Rol.objects.filter(anulado=False).order_by('nombre')
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'rol_filter': rol_filter,
        'estado_filter': estado_filter,
        'roles': roles,
        'titulo': 'Gestión de Usuarios'
    }
    
    return render(request, 'usuarios/lista_usuarios.html', context)


@login_required
def crear_usuario(request):
    """Crear nuevo usuario del sistema"""
    if request.method == 'POST':
        form = UsuarioSistemaForm(request.POST)
        if form.is_valid():
            try:
                usuario = form.save(usuario_actual=request.user)
                messages.success(request, f'Usuario "{usuario.nombre_usuario}" creado exitosamente.')
                return redirect('usuarios:lista_usuarios')
            except Exception as e:
                messages.error(request, f'Error al crear usuario: {str(e)}')
    else:
        form = UsuarioSistemaForm()
    
    context = {
        'form': form,
        'titulo': 'Crear Usuario',
        'accion': 'Crear'
    }
    
    return render(request, 'usuarios/formulario_usuario.html', context)


@login_required
def editar_usuario(request, usuario_id):
    """Editar usuario del sistema"""
    usuario = get_object_or_404(UsuarioSistema, id=usuario_id, anulado=False)
    
    if request.method == 'POST':
        form = UsuarioSistemaForm(request.POST, instance=usuario, is_edit=True)
        if form.is_valid():
            try:
                usuario = form.save(usuario_actual=request.user)
                messages.success(request, f'Usuario "{usuario.nombre_usuario}" actualizado exitosamente.')
                return redirect('usuarios:lista_usuarios')
            except Exception as e:
                messages.error(request, f'Error al actualizar usuario: {str(e)}')
    else:
        form = UsuarioSistemaForm(instance=usuario, is_edit=True)
    
    context = {
        'form': form,
        'usuario': usuario,
        'titulo': f'Editar Usuario: {usuario.nombre_usuario}',
        'accion': 'Actualizar'
    }
    
    return render(request, 'usuarios/formulario_usuario.html', context)


@login_required
def detalle_usuario(request, usuario_id):
    """Ver detalles del usuario"""
    usuario = get_object_or_404(UsuarioSistema, id=usuario_id)
    
    context = {
        'usuario': usuario,
        'titulo': f'Detalles: {usuario.nombre_usuario}'
    }
    
    return render(request, 'usuarios/detalle_usuario.html', context)


@login_required
def cambiar_estado_usuario(request, usuario_id):
    """Activar/desactivar usuario via AJAX"""
    if request.method == 'POST':
        usuario = get_object_or_404(UsuarioSistema, id=usuario_id, anulado=False)
        
        # Cambiar estado
        usuario.activo = not usuario.activo
        
        # Auditoría
        from django.utils import timezone
        usuario.editado_date = timezone.now()
        usuario.editado_por = request.user.id
        
        usuario.save()
        
        estado_text = "activado" if usuario.activo else "desactivado"
        
        return JsonResponse({
            'success': True,
            'message': f'Usuario {estado_text} exitosamente.',
            'nuevo_estado': usuario.activo,
            'estado_display': usuario.estado_display
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@login_required
def anular_usuario(request, usuario_id):
    """Anular usuario del sistema"""
    if request.method == 'POST':
        usuario = get_object_or_404(UsuarioSistema, id=usuario_id, anulado=False)
        
        # Anular usuario
        from django.utils import timezone
        usuario.anulado = True
        usuario.anulado_date = timezone.now()
        usuario.anulado_por = request.user.id
        usuario.activo = False  # También desactivar
        
        usuario.save()
        
        messages.success(request, f'Usuario "{usuario.nombre_usuario}" anulado exitosamente.')
        return redirect('usuarios:lista_usuarios')
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


# Vistas para gestión de roles

@login_required
def lista_roles(request):
    """Lista de roles del sistema"""
    search = request.GET.get('search', '')
    
    roles = Rol.objects.filter(anulado=False)
    
    if search:
        roles = roles.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    roles = roles.order_by('nombre')
    
    # Paginación
    paginator = Paginator(roles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'titulo': 'Gestión de Roles'
    }
    
    return render(request, 'usuarios/lista_roles.html', context)


@login_required
def crear_rol(request):
    """Crear nuevo rol"""
    if request.method == 'POST':
        form = RolForm(request.POST)
        if form.is_valid():
            try:
                rol = form.save(usuario_actual=request.user)
                messages.success(request, f'Rol "{rol.nombre}" creado exitosamente.')
                return redirect('usuarios:lista_roles')
            except Exception as e:
                messages.error(request, f'Error al crear rol: {str(e)}')
    else:
        form = RolForm()
    
    context = {
        'form': form,
        'titulo': 'Crear Rol',
        'accion': 'Crear'
    }
    
    return render(request, 'usuarios/formulario_rol.html', context)


@login_required
def editar_rol(request, rol_id):
    """Editar rol"""
    rol = get_object_or_404(Rol, id=rol_id, anulado=False)
    
    if request.method == 'POST':
        form = RolForm(request.POST, instance=rol)
        if form.is_valid():
            try:
                rol = form.save(usuario_actual=request.user)
                messages.success(request, f'Rol "{rol.nombre}" actualizado exitosamente.')
                return redirect('usuarios:lista_roles')
            except Exception as e:
                messages.error(request, f'Error al actualizar rol: {str(e)}')
    else:
        form = RolForm(instance=rol)
    
    context = {
        'form': form,
        'rol': rol,
        'titulo': f'Editar Rol: {rol.nombre}',
        'accion': 'Actualizar'
    }
    
    return render(request, 'usuarios/formulario_rol.html', context)


# Vistas de autenticación personalizada
def custom_login(request):
    """Vista de login personalizada para la tabla usuarios"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            # Autenticar usuario
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido {user.get_full_name()}')
                
                # Redirigir a la página solicitada o al dashboard
                next_url = request.GET.get('next', '/usuarios/dashboard/')
                return redirect(next_url)
            else:
                messages.error(request, 'Usuario o contraseña incorrectos')
        else:
            messages.error(request, 'Por favor ingrese usuario y contraseña')
    
    # Si el usuario ya está autenticado, redirigir al dashboard
    if request.user.is_authenticated:
        return redirect('/usuarios/dashboard/')
    
    return render(request, 'usuarios/custom_login.html', {
        'titulo': 'Iniciar Sesión'
    })


def custom_logout(request):
    """Vista de logout personalizada"""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente')
    return redirect('/usuarios/login/')
