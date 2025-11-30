from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from .models import (
    Producto, Categoria, Marca, Laboratorio, TipoProducto, 
    ClaseProducto, Subcategoria, SubnivelProducto
)


def lista_productos_simple(request):
    """Lista todos los productos desde la base de datos MySQL (sin autenticación)"""
    search = request.GET.get('search', '')
    categoria_id = request.GET.get('categoria', '')
    marca_id = request.GET.get('marca', '')
    laboratorio_id = request.GET.get('laboratorio', '')
    
    # Filtrar productos activos y no anulados
    productos = Producto.objects.filter(
        activo=True, 
        anulado=False
    ).select_related(
        'id_categoria', 'id_marca', 'id_laboratorio', 
        'id_tipo_producto', 'id_clase_producto'
    )[:50]  # Limitamos a 50 para probar
    
    # Aplicar filtros de búsqueda
    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) |
            Q(codigo_principal__icontains=search) |
            Q(codigo_auxiliar__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    if categoria_id:
        productos = productos.filter(id_categoria_id=categoria_id)
    
    if marca_id:
        productos = productos.filter(id_marca_id=marca_id)
        
    if laboratorio_id:
        productos = productos.filter(id_laboratorio_id=laboratorio_id)
    
    # Obtener datos para filtros
    categorias = Categoria.objects.all().order_by('nombre')[:20]
    marcas = Marca.objects.all().order_by('nombre')[:20]
    laboratorios = Laboratorio.objects.all().order_by('nombre')[:20]
    
    context = {
        'productos': productos,
        'categorias': categorias,
        'marcas': marcas,
        'laboratorios': laboratorios,
        'search': search,
        'categoria_id': categoria_id,
        'marca_id': marca_id,
        'laboratorio_id': laboratorio_id,
        'titulo': 'Catálogo de Productos LogiPharm'
    }
    return render(request, 'productos/lista_completa.html', context)


@login_required
def lista_productos(request):
    """Lista completa de productos con filtros avanzados"""
    search = request.GET.get('search', '')
    categoria_id = request.GET.get('categoria', '')
    marca_id = request.GET.get('marca', '')
    laboratorio_id = request.GET.get('laboratorio', '')
    vista = request.GET.get('vista', 'cards')  # cards o table
    
    # Filtrar productos activos y no anulados
    productos = Producto.objects.filter(
        activo=True, 
        anulado=False
    ).select_related(
        'id_categoria', 'id_marca', 'id_laboratorio', 
        'id_tipo_producto', 'id_clase_producto'
    )
    
    # Aplicar filtros de búsqueda
    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) |
            Q(codigo_principal__icontains=search) |
            Q(codigo_auxiliar__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    if categoria_id:
        productos = productos.filter(id_categoria_id=categoria_id)
    
    if marca_id:
        productos = productos.filter(id_marca_id=marca_id)
        
    if laboratorio_id:
        productos = productos.filter(id_laboratorio_id=laboratorio_id)
    
    # Limitar resultados para mejor rendimiento
    productos = productos[:100]
    
    # Estadísticas
    total_productos = Producto.objects.filter(activo=True, anulado=False).count()
    productos_en_stock = Producto.objects.filter(activo=True, anulado=False, stock__gt=0).count()
    productos_stock_bajo = Producto.objects.filter(activo=True, anulado=False, stock__lte=F('stock_minimo')).count()
    total_categorias = Categoria.objects.count()
    
    # Obtener datos para filtros
    categorias = Categoria.objects.all().order_by('nombre')[:50]
    marcas = Marca.objects.all().order_by('nombre')[:50] 
    laboratorios = Laboratorio.objects.all().order_by('nombre')[:50]
    
    context = {
        'productos': productos,
        'categorias': categorias,
        'marcas': marcas,
        'laboratorios': laboratorios,
        'total_productos': total_productos,
        'productos_en_stock': productos_en_stock,
        'productos_stock_bajo': productos_stock_bajo,
        'total_categorias': total_categorias,
        'vista': vista,
        'titulo': 'Gestión de Productos'
    }
    
    return render(request, 'productos/lista_completa.html', context)


@login_required
def detalle_producto(request, producto_id):
    """Mostrar detalle de un producto específico"""
    producto = get_object_or_404(
        Producto.objects.select_related(
            'id_categoria', 'id_marca', 'id_laboratorio',
            'id_tipo_producto', 'id_clase_producto', 'id_subcategoria'
        ), 
        id=producto_id, 
        activo=True, 
        anulado=False
    )
    
    context = {
        'producto': producto,
        'titulo': f'Producto: {producto.nombre}'
    }
    return render(request, 'productos/detalle.html', context)


@login_required
def productos_con_stock_bajo(request):
    """Lista productos que necesitan reabastecimiento"""
    productos = Producto.objects.filter(
        activo=True,
        anulado=False
    ).annotate(
        necesita_restock=F('stock') <= F('stock_minimo')
    ).filter(necesita_restock=True).select_related(
        'id_categoria', 'id_marca', 'id_laboratorio'
    )
    
    context = {
        'productos': productos,
        'titulo': 'Productos con Stock Bajo'
    }
    return render(request, 'productos/stock_bajo.html', context)


@login_required
def buscar_productos_api(request):
    """API para búsqueda rápida de productos (para autocomplete)"""
    term = request.GET.get('term', '')
    query_type = request.GET.get('type', 'autocomplete')  # autocomplete o search
    limit = int(request.GET.get('limit', 10))
    
    if len(term) < 2:
        return JsonResponse({'results': []})
    
    # Usar SQL directo para incluir información de ubicación
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.codigoPrincipal, p.codigoAuxiliar, p.nombre, p.precioVenta, p.stock,
                   c.nombre as categoria, m.nombre as marca, l.nombre as laboratorio,
                   p.esPsicotropico, p.requiereCadenaFrio, p.requiereSeguimiento,
                   u.fila, u.columna, pr.nombre as percha_nombre, s.nombre as seccion_nombre, s.color as seccion_color
            FROM productos p
            LEFT JOIN categorias c ON p.idCategoria = c.id
            LEFT JOIN marcas m ON p.idMarca = m.id
            LEFT JOIN laboratorios l ON p.idLaboratorio = l.id
            LEFT JOIN productos_ubicacionproducto u ON p.id = u.producto_id AND u.activo = 1
            LEFT JOIN productos_percha pr ON u.percha_id = pr.id
            LEFT JOIN productos_seccion s ON pr.seccion_id = s.id
            WHERE (p.nombre LIKE %s OR p.codigoPrincipal LIKE %s OR p.codigoAuxiliar LIKE %s)
            AND p.activo = 1 AND p.anulado = 0
            LIMIT %s
        """, [f'%{term}%', f'%{term}%', f'%{term}%', limit])
        
        columns = [col[0] for col in cursor.description]
        productos = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    if query_type == 'search':
        # Respuesta detallada para búsquedas
        results = []
        for producto in productos:
            # Formatear ubicación
            if producto.get('fila') and producto.get('columna'):
                ubicacion = f"{producto.get('seccion_nombre', 'N/A')} - {producto.get('percha_nombre', 'N/A')} (F{producto['fila']}C{producto['columna']})"
                tiene_ubicacion = True
            else:
                ubicacion = 'Sin ubicar'
                tiene_ubicacion = False
            
            results.append({
                'id': producto['id'],
                'codigo_principal': producto['codigoPrincipal'],
                'codigo_auxiliar': producto.get('codigoAuxiliar') or '',
                'nombre': producto['nombre'],
                'precio_venta': float(producto['precioVenta'] or 0),
                'stock': float(producto['stock'] or 0),
                'categoria': producto.get('categoria') or '',
                'marca': producto.get('marca') or '',
                'laboratorio': producto.get('laboratorio') or '',
                'es_psicotropico': producto.get('esPsicotropico') or False,
                'requiere_cadena_frio': producto.get('requiereCadenaFrio') or False,
                'requiere_seguimiento': producto.get('requiereSeguimiento') or False,
                'ubicacion': ubicacion,
                'tiene_ubicacion': tiene_ubicacion,
                'seccion_color': producto.get('seccion_color'),
            })
        return JsonResponse({'productos': results})
    else:
        # Respuesta simple para autocomplete
        results = []
        for producto in productos:
            # Formatear ubicación para autocomplete
            if producto.get('fila') and producto.get('columna'):
                ubicacion_texto = f" 📍 {producto.get('seccion_nombre', 'N/A')} F{producto['fila']}C{producto['columna']}"
            else:
                ubicacion_texto = " ❓ Sin ubicar"
            
            results.append({
                'id': producto['id'],
                'text': f"{producto['codigoPrincipal']} - {producto['nombre']}{ubicacion_texto}",
                'precio': float(producto['precioVenta'] or 0),
                'stock': float(producto['stock'] or 0)
            })
        return JsonResponse({'results': results})


def validar_datos_producto(request, producto_id=None):
    """Función auxiliar para validar datos del producto"""
    errores = []
    
    # Validaciones obligatorias
    if not request.POST.get('codigo_principal', '').strip():
        errores.append('El código principal es obligatorio')
    
    if not request.POST.get('nombre', '').strip():
        errores.append('El nombre del producto es obligatorio')
    
    if not request.POST.get('id_categoria'):
        errores.append('La categoría es obligatoria')
        
    if not request.POST.get('id_marca'):
        errores.append('La marca es obligatoria')
    
    if not request.POST.get('id_tipo_producto'):
        errores.append('El tipo de producto es obligatorio')
        
    if not request.POST.get('id_clase_producto'):
        errores.append('La clase de producto es obligatoria')
    
    # Validaciones de precios
    try:
        costo = float(request.POST.get('costo_unidad', 0))
        precio = float(request.POST.get('precio_venta', 0))
        
        if costo <= 0:
            errores.append('El costo por unidad debe ser mayor a 0')
            
        if precio <= 0:
            errores.append('El precio de venta debe ser mayor a 0')
            
        if precio <= costo:
            errores.append('El precio de venta debe ser mayor que el costo')
            
    except ValueError:
        errores.append('Los precios deben ser números válidos')
    
    # Validaciones de stock
    try:
        stock = float(request.POST.get('stock', 0))
        stock_min = float(request.POST.get('stock_minimo', 0))
        stock_max = float(request.POST.get('stock_maximo', 0))
        
        if stock < 0:
            errores.append('El stock no puede ser negativo')
            
        if stock_min < 0:
            errores.append('El stock mínimo no puede ser negativo')
            
        if stock_max > 0 and stock_min >= stock_max:
            errores.append('El stock mínimo debe ser menor que el stock máximo')
            
    except ValueError:
        errores.append('Los valores de stock deben ser números válidos')
    
    # Validación de código único
    codigo = request.POST.get('codigo_principal', '').strip()
    query = Producto.objects.filter(codigo_principal=codigo)
    if producto_id:
        query = query.exclude(pk=producto_id)
        
    if query.exists():
        errores.append(f'Ya existe un producto con el código "{codigo}"')
    
    # Validación de registro sanitario si es psicotrópico
    if 'es_psicotropico' in request.POST and not request.POST.get('registro_sanitario'):
        errores.append('Los productos psicotrópicos requieren registro sanitario')
    
    return errores


@login_required
@login_required
def crear_producto(request):
    """Crear nuevo producto"""
    if request.method == 'POST':
        # Validar datos
        errores = validar_datos_producto(request)
        
        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            try:
                # Crear nuevo producto con los datos del formulario
                producto = Producto()
                
                # Información básica
                producto.codigo_principal = request.POST.get('codigo_principal').strip()
                producto.codigo_auxiliar = request.POST.get('codigo_auxiliar', '').strip() or None
                producto.nombre = request.POST.get('nombre').strip()
                producto.descripcion = request.POST.get('descripcion', '').strip() or None
                producto.observaciones = request.POST.get('observaciones', '').strip() or None
                producto.registro_sanitario = request.POST.get('registro_sanitario', '').strip() or None
                
                # Clasificación
                producto.id_tipo_producto_id = request.POST.get('id_tipo_producto')
                producto.id_clase_producto_id = request.POST.get('id_clase_producto')
                producto.id_categoria_id = request.POST.get('id_categoria')
                producto.id_marca_id = request.POST.get('id_marca')
                producto.id_laboratorio_id = request.POST.get('id_laboratorio') or None
                producto.clasificacion_abc = request.POST.get('clasificacion_abc') or None
                
                # Precios y costos
                producto.costo_unidad = float(request.POST.get('costo_unidad', 0))
                producto.costo_caja = float(request.POST.get('costo_caja', 0))
                producto.pvp_unidad = float(request.POST.get('pvp_unidad', 0))
                producto.precio_venta = float(request.POST.get('precio_venta', 0))
                
                # Inventario
                producto.stock = float(request.POST.get('stock', 0))
                producto.stock_minimo = float(request.POST.get('stock_minimo', 0))
                producto.stock_maximo = float(request.POST.get('stock_maximo', 0))
                
                # Características farmacéuticas (checkboxes)
                producto.es_divisible = 'es_divisible' in request.POST
                producto.es_psicotropico = 'es_psicotropico' in request.POST
                producto.requiere_cadena_frio = 'requiere_cadena_frio' in request.POST
                producto.requiere_seguimiento = 'requiere_seguimiento' in request.POST
                producto.calculo_abc_manual = 'calculo_abc_manual' in request.POST
                producto.activo = 'activo' in request.POST
                producto.anulado = False
                
                # Guardar el producto
                producto.save()
                
                messages.success(request, f'Producto "{producto.nombre}" creado exitosamente con código {producto.codigo_principal}')
                return redirect('productos:lista')
                
            except Exception as e:
                messages.error(request, f'Error al crear el producto: {str(e)}')
    
    # Cargar datos para formulario
    context = {
        'categorias': Categoria.objects.all().order_by('nombre'),
        'marcas': Marca.objects.all().order_by('nombre'),
        'laboratorios': Laboratorio.objects.all().order_by('nombre'),
        'tipos_producto': TipoProducto.objects.all().order_by('nombre'),
        'clases_producto': ClaseProducto.objects.all().order_by('nombre'),
        'titulo': 'Crear Nuevo Producto'
    }
    return render(request, 'productos/crear.html', context)


@login_required
def editar_producto(request, producto_id):
    """Editar producto existente"""
    producto = get_object_or_404(Producto, pk=producto_id)
    
    if request.method == 'POST':
        # Validar datos (pasando el ID del producto para excluirlo de la validación de código único)
        errores = validar_datos_producto(request, producto_id)
        
        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            try:
                # Actualizar datos del producto
                producto.codigo_principal = request.POST.get('codigo_principal').strip()
                producto.codigo_auxiliar = request.POST.get('codigo_auxiliar', '').strip() or None
                producto.nombre = request.POST.get('nombre').strip()
                producto.descripcion = request.POST.get('descripcion', '').strip() or None
                producto.observaciones = request.POST.get('observaciones', '').strip() or None
                producto.registro_sanitario = request.POST.get('registro_sanitario', '').strip() or None
                
                # Fecha de caducidad
                fecha_caducidad = request.POST.get('fecha_caducidad', '').strip()
                producto.fecha_caducidad = fecha_caducidad if fecha_caducidad else None
                
                # Clasificación
                producto.id_tipo_producto_id = request.POST.get('id_tipo_producto')
                producto.id_clase_producto_id = request.POST.get('id_clase_producto')
                producto.id_categoria_id = request.POST.get('id_categoria')
                producto.id_marca_id = request.POST.get('id_marca')
                producto.id_laboratorio_id = request.POST.get('id_laboratorio') or None
                producto.clasificacion_abc = request.POST.get('clasificacion_abc') or None
                
                # Precios y costos
                producto.costo_unidad = float(request.POST.get('costo_unidad', 0))
                producto.costo_caja = float(request.POST.get('costo_caja', 0))
                producto.pvp_unidad = float(request.POST.get('pvp_unidad', 0))
                producto.precio_venta = float(request.POST.get('precio_venta', 0))
                
                # Inventario
                producto.stock = float(request.POST.get('stock', 0))
                producto.stock_minimo = float(request.POST.get('stock_minimo', 0))
                producto.stock_maximo = float(request.POST.get('stock_maximo', 0))
                
                # Características farmacéuticas
                producto.es_divisible = 'es_divisible' in request.POST
                producto.es_psicotropico = 'es_psicotropico' in request.POST
                producto.requiere_cadena_frio = 'requiere_cadena_frio' in request.POST
                producto.requiere_seguimiento = 'requiere_seguimiento' in request.POST
                producto.calculo_abc_manual = 'calculo_abc_manual' in request.POST
                producto.activo = 'activo' in request.POST
                
                # Guardar cambios
                producto.save()
                
                messages.success(request, f'Producto "{producto.nombre}" actualizado exitosamente')
                return redirect('productos:lista')
                
            except Exception as e:
                messages.error(request, f'Error al actualizar el producto: {str(e)}')
    
    # Cargar datos para formulario
    context = {
        'producto': producto,
        'categorias': Categoria.objects.all().order_by('nombre'),
        'marcas': Marca.objects.all().order_by('nombre'),
        'laboratorios': Laboratorio.objects.all().order_by('nombre'),
        'tipos_producto': TipoProducto.objects.all().order_by('nombre'),
        'clases_producto': ClaseProducto.objects.all().order_by('nombre'),
        'titulo': f'Editar Producto: {producto.nombre}'
    }
    return render(request, 'productos/crear.html', context)


@login_required
def eliminar_producto(request, pk):
    """Eliminar producto (marcar como inactivo)"""
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        producto.activo = False
        producto.save()
        messages.success(request, 'Producto eliminado exitosamente')
        return redirect('productos:lista')
    
    context = {
        'producto': producto,
        'titulo': 'Eliminar Producto'
    }
    return render(request, 'productos/eliminar.html', context)


# Views para categorías
@login_required
def lista_categorias(request):
    """Lista todas las categorías"""
    categorias = Categoria.objects.filter(activo=True)
    
    context = {
        'categorias': categorias,
        'titulo': 'Categorías'
    }
    return render(request, 'productos/categorias.html', context)


@login_required
def crear_categoria(request):
    """Crear nueva categoría"""
    if request.method == 'POST':
        # Lógica para crear categoría
        messages.success(request, 'Categoría creada exitosamente')
        return redirect('productos:categorias')
    
    context = {
        'titulo': 'Crear Categoría'
    }
    return render(request, 'productos/crear_categoria.html', context)


@login_required
def editar_categoria(request, pk):
    """Editar categoría existente"""
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        activa = request.POST.get('activa') == 'on'
        
        if not nombre:
            messages.error(request, 'El nombre de la categoría es obligatorio')
        else:
            try:
                categoria.nombre = nombre
                if hasattr(categoria, 'descripcion'):
                    categoria.descripcion = descripcion
                if hasattr(categoria, 'activa'):
                    categoria.activa = activa
                categoria.save()
                
                messages.success(request, f'Categoría "{nombre}" actualizada exitosamente')
                return redirect('productos:categorias')
            except Exception as e:
                messages.error(request, f'Error al actualizar la categoría: {str(e)}')
    
    context = {
        'categoria': categoria,
        'titulo': 'Editar Categoría'
    }
    return render(request, 'productos/editar_categoria.html', context)


# Views para marcas
@login_required
def lista_marcas(request):
    """Lista todas las marcas"""
    marcas = Marca.objects.filter(activo=True)
    
    context = {
        'marcas': marcas,
        'titulo': 'Marcas'
    }
    return render(request, 'productos/marcas.html', context)


@login_required
def crear_marca(request):
    """Crear nueva marca"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        activa = request.POST.get('activa') == 'on'
        
        if not nombre:
            messages.error(request, 'El nombre de la marca es obligatorio')
        else:
            try:
                # Verificar si ya existe una marca con ese nombre
                if Marca.objects.filter(nombre__iexact=nombre).exists():
                    messages.warning(request, f'Ya existe una marca con el nombre "{nombre}"')
                else:
                    marca = Marca(nombre=nombre)
                    if hasattr(Marca, 'descripcion'):
                        marca.descripcion = descripcion
                    if hasattr(Marca, 'activa'):
                        marca.activa = activa
                    marca.save()
                    
                    messages.success(request, f'Marca "{nombre}" creada exitosamente')
                    return redirect('productos:marcas')
            except Exception as e:
                messages.error(request, f'Error al crear la marca: {str(e)}')
    
    context = {
        'titulo': 'Crear Marca'
    }
    return render(request, 'productos/crear_marca.html', context)


@login_required
def editar_marca(request, pk):
    """Editar marca existente"""
    marca = get_object_or_404(Marca, pk=pk)
    
    if request.method == 'POST':
        # Lógica para editar marca
        messages.success(request, 'Marca actualizada exitosamente')
        return redirect('productos:marcas')
    
    context = {
        'marca': marca,
        'titulo': 'Editar Marca'
    }
    return render(request, 'productos/editar_marca.html', context)


# Views para unidades de medida
@login_required
def lista_unidades(request):
    """Lista todas las unidades de medida"""
    # TODO: Implementar modelo UnidadMedida si es necesario
    # unidades = UnidadMedida.objects.filter(activo=True)
    unidades = []  # Placeholder hasta implementar UnidadMedida
    
    context = {
        'unidades': unidades,
        'titulo': 'Unidades de Medida'
    }
    return render(request, 'productos/unidades.html', context)


@login_required
def crear_unidad(request):
    """Crear nueva unidad de medida"""
    if request.method == 'POST':
        # Lógica para crear unidad
        messages.success(request, 'Unidad de medida creada exitosamente')
        return redirect('productos:unidades')
    
    context = {
        'titulo': 'Crear Unidad de Medida'
    }
    return render(request, 'productos/crear_unidad.html', context)


@login_required
def editar_unidad(request, pk):
    """Editar unidad de medida existente"""
    # TODO: Implementar modelo UnidadMedida si es necesario
    # unidad = get_object_or_404(UnidadMedida, pk=pk)
    
    if request.method == 'POST':
        # Lógica para editar unidad
        messages.success(request, 'Unidad de medida actualizada exitosamente')
        return redirect('productos:unidades')
    
    context = {
        # 'unidad': unidad,
        'titulo': 'Editar Unidad de Medida'
    }
    return render(request, 'productos/editar_unidad.html', context)


# Reportes
@login_required
def reporte_stock(request):
    """Reporte de stock de productos"""
    productos = Producto.objects.filter(activo=True).select_related('categoria', 'marca')
    
    context = {
        'productos': productos,
        'titulo': 'Reporte de Stock'
    }
    return render(request, 'productos/reporte_stock.html', context)


@login_required
def productos_bajo_stock(request):
    """Productos que necesitan restock - NUEVA IMPLEMENTACIÓN CON PAGINACIÓN"""
    try:
        productos_list = Producto.objects.filter(
            activo=True,
            stock__lte=F('stock_minimo')
        ).select_related('id_categoria', 'id_marca').order_by('stock', 'nombre')
        
        # Paginación
        paginator = Paginator(productos_list, 20)  # 20 productos por página
        page_number = request.GET.get('page')
        productos = paginator.get_page(page_number)
        
        # Estadísticas
        total_productos = productos_list.count()
        productos_agotados = productos_list.filter(stock=0).count()
        productos_bajo_minimo = productos_list.filter(stock__gt=0, stock__lte=F('stock_minimo')).count()
        
        context = {
            'productos': productos,
            'titulo': 'Productos Bajo Stock',
            'total_productos': total_productos,
            'productos_agotados': productos_agotados,
            'productos_bajo_minimo': productos_bajo_minimo,
        }
        return render(request, 'productos/bajo_stock.html', context)
    except Exception as e:
        print(f"Error en productos_bajo_stock: {e}")
        context = {
            'productos': [],
            'titulo': 'Productos Bajo Stock',
            'error': str(e),
            'total_productos': 0,
            'productos_agotados': 0,
            'productos_bajo_minimo': 0,
        }
        return render(request, 'productos/bajo_stock.html', context)


# Vistas básicas para categorías y marcas
@login_required
def lista_categorias(request):
    """Lista todas las categorías"""
    categorias = Categoria.objects.all().order_by('nombre')
    
    context = {
        'categorias': categorias,
        'titulo': 'Categorías de Productos'
    }
    return render(request, 'productos/categorias.html', context)


@login_required
def crear_categoria(request):
    """Crear nueva categoría"""
    if request.method == 'POST':
        messages.info(request, 'Funcionalidad en desarrollo')
        return redirect('productos:categorias')
    
    context = {
        'titulo': 'Nueva Categoría'
    }
    return render(request, 'productos/crear_categoria.html', context)


@login_required
def lista_marcas(request):
    """Lista todas las marcas"""
    marcas = Marca.objects.all().order_by('nombre')
    
    context = {
        'marcas': marcas,
        'titulo': 'Marcas de Productos'
    }
    return render(request, 'productos/marcas.html', context)


# =====================================
# API PARA CACHE OFFLINE DE PRODUCTOS
# =====================================

def productos_cache_api(request):
    """
    API para obtener todos los productos para cache offline
    Retorna información completa para IndexedDB
    """
    try:
        print("=== INICIANDO API CACHE DE PRODUCTOS ===")
        
        # Obtener TODOS los productos activos (sin límite)
        productos = Producto.objects.filter(
            activo=True, 
            anulado=False
        ).select_related(
            'id_categoria', 'id_marca', 'id_laboratorio',
            'id_tipo_producto', 'id_clase_producto'
        )
        
        total_productos_disponibles = productos.count()
        print(f"Total de productos activos encontrados: {total_productos_disponibles}")
        
        # Preparar datos para cache
        productos_cache = []
        for producto in productos:
            try:
                # Usar pvp_unidad como precio principal
                precio_venta = float(getattr(producto, 'pvp_unidad', 0) or getattr(producto, 'precio_venta', 0) or 0)
                
                producto_cache = {
                    'id': producto.id,
                    'codigo_principal': producto.codigo_principal or '',
                    'codigo_auxiliar': producto.codigo_auxiliar or '',
                    'nombre': producto.nombre or '',
                    'descripcion': producto.descripcion or '',
                    'observaciones': getattr(producto, 'observaciones', '') or '',
                    'registro_sanitario': getattr(producto, 'registro_sanitario', '') or '',
                    
                    # Precios - usar pvp_unidad como principal
                    'precio_venta': precio_venta,
                    'pvp_unidad': float(getattr(producto, 'pvp_unidad', 0) or 0),
                    'precio_compra': float(getattr(producto, 'costo_unidad', 0) or 0),
                    'costo_unidad': float(getattr(producto, 'costo_unidad', 0) or 0),
                    'costo_caja': float(getattr(producto, 'costo_caja', 0) or 0),
                    
                    # Stock
                    'stock': float(producto.stock or 0),
                    'stock_minimo': float(producto.stock_minimo or 0),
                    'stock_maximo': float(producto.stock_maximo or 0),
                    
                    # Estados
                    'activo': bool(producto.activo),
                    'anulado': bool(producto.anulado),
                    'es_divisible': bool(getattr(producto, 'es_divisible', False)),
                    'es_psicotropico': bool(getattr(producto, 'es_psicotropico', False)),
                    'requiere_cadena_frio': bool(getattr(producto, 'requiere_cadena_frio', False)),
                    'requiere_seguimiento': bool(getattr(producto, 'requiere_seguimiento', False)),
                    
                    # Clasificación
                    'clasificacion_abc': getattr(producto, 'clasificacion_abc', '') or '',
                    
                    # Información de relaciones
                    'categoria': {
                        'id': producto.id_categoria.id if producto.id_categoria else 0,
                        'nombre': producto.id_categoria.nombre if producto.id_categoria else ''
                    },
                    'marca': {
                        'id': producto.id_marca.id if producto.id_marca else 0,
                        'nombre': producto.id_marca.nombre if producto.id_marca else ''
                    },
                    'laboratorio': {
                        'id': producto.id_laboratorio.id if producto.id_laboratorio else 0,
                        'nombre': producto.id_laboratorio.nombre if producto.id_laboratorio else ''
                    },
                    'tipo_producto': {
                        'id': producto.id_tipo_producto.id if producto.id_tipo_producto else 0,
                        'nombre': producto.id_tipo_producto.nombre if producto.id_tipo_producto else ''
                    },
                    'clase_producto': {
                        'id': producto.id_clase_producto.id if producto.id_clase_producto else 0,
                        'nombre': producto.id_clase_producto.nombre if producto.id_clase_producto else ''
                    },
                    
                    # Campos calculados para búsqueda
                    'searchable_text': f"{producto.codigo_principal or ''} {producto.codigo_auxiliar or ''} {producto.nombre or ''} {producto.descripcion or ''}".lower(),
                    'bajo_stock': float(producto.stock or 0) <= float(producto.stock_minimo or 0),
                    'agotado': float(producto.stock or 0) <= 0,
                    
                    # Metadatos del cache
                    'cache_timestamp': request.GET.get('timestamp', ''),
                    'cache_version': '1.0'
                }
                productos_cache.append(producto_cache)
                
            except Exception as e:
                print(f"Error procesando producto {producto.id}: {str(e)}")
                continue
        
        # Obtener categorías, marcas y laboratorios para filtros
        try:
            categorias = list(Categoria.objects.values('id', 'nombre').order_by('nombre'))
        except Exception as e:
            print(f"Error obteniendo categorías: {e}")
            categorias = []
            
        try:
            marcas = list(Marca.objects.values('id', 'nombre').order_by('nombre'))
        except Exception as e:
            print(f"Error obteniendo marcas: {e}")
            marcas = []
            
        try:
            laboratorios = list(Laboratorio.objects.values('id', 'nombre').order_by('nombre'))
        except Exception as e:
            print(f"Error obteniendo laboratorios: {e}")
            laboratorios = []
        
        response_data = {
            'success': True,
            'productos': productos_cache,
            'metadata': {
                'total_productos': len(productos_cache),
                'total_productos_disponibles': total_productos_disponibles,
                'productos_procesados_correctamente': len(productos_cache),
                'productos_con_errores': total_productos_disponibles - len(productos_cache),
                'categorias': categorias,
                'marcas': marcas,
                'laboratorios': laboratorios,
                'cache_version': '1.0',
                'timestamp': request.GET.get('timestamp', ''),
                'generated_at': datetime.now().isoformat()
            }
        }
        
        print(f"API Cache: Retornando {len(productos_cache)} de {total_productos_disponibles} productos disponibles")
        if len(productos_cache) < total_productos_disponibles:
            productos_con_errores = total_productos_disponibles - len(productos_cache)
            print(f"ADVERTENCIA: {productos_con_errores} productos tuvieron errores al procesarse")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        # Log detallado del error
        print(f"ERROR COMPLETO en productos_cache_api: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': f'Error obteniendo productos para cache: {str(e)}',
            'error_type': type(e).__name__,
            'productos': [],
            'metadata': {}
        }, status=500)


def buscar_productos_api(request):
    """
    API para búsqueda de productos (funciona online y offline)
    Compatible con el sistema de cache offline
    """
    query = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '')
    marca_id = request.GET.get('marca', '')
    limit = int(request.GET.get('limit', 20))
    
    try:
        if not query and not categoria_id and not marca_id:
            return JsonResponse({
                'success': True,
                'productos': [],
                'count': 0,
                'query': query
            })
        
        # Filtrar productos usando los nombres correctos de campos
        productos = Producto.objects.filter(
            activo=True, 
            anulado=False
        ).select_related(
            'id_categoria', 'id_marca', 'id_laboratorio'
        )
        
        # Búsqueda por texto - usar los nombres correctos de campos
        if query:
            productos = productos.filter(
                Q(nombre__icontains=query) |
                Q(codigo_principal__icontains=query) |
                Q(codigo_auxiliar__icontains=query) |
                Q(descripcion__icontains=query)
            )
        
        # Filtros adicionales
        if categoria_id:
            productos = productos.filter(id_categoria_id=categoria_id)
        if marca_id:
            productos = productos.filter(id_marca_id=marca_id)
        
        # Limitar resultados
        productos = productos[:limit]
        
        # Formatear resultados
        productos_data = []
        for producto in productos:
            try:
                # Usar pvp_unidad como precio principal
                precio_venta = float(getattr(producto, 'pvp_unidad', 0) or getattr(producto, 'precio_venta', 0) or 0)
                
                productos_data.append({
                    'id': producto.id,
                    'codigo_principal': producto.codigo_principal or '',
                    'codigo_auxiliar': producto.codigo_auxiliar or '',
                    'nombre': producto.nombre,
                    'descripcion': producto.descripcion or '',
                    'precio_venta': precio_venta,
                    'pvp_unidad': float(getattr(producto, 'pvp_unidad', 0) or 0),
                    'stock': float(producto.stock or 0),
                    'categoria': producto.id_categoria.nombre if producto.id_categoria else '',
                    'marca': producto.id_marca.nombre if producto.id_marca else '',
                    'laboratorio': producto.id_laboratorio.nombre if producto.id_laboratorio else '',
                    'bajo_stock': float(producto.stock or 0) <= float(producto.stock_minimo or 0),
                    'agotado': float(producto.stock or 0) <= 0,
                    'es_psicotropico': bool(getattr(producto, 'es_psicotropico', False)),
                    'requiere_cadena_frio': bool(getattr(producto, 'requiere_cadena_frio', False))
                })
            except Exception as e:
                print(f"Error procesando producto en búsqueda {producto.id}: {str(e)}")
                continue
        
        return JsonResponse({
            'success': True,
            'productos': productos_data,
            'count': len(productos_data),
            'query': query,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        # Log del error para debugging
        print(f"Error en buscar_productos_api: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': f'Error en búsqueda: {str(e)}',
            'productos': [],
            'count': 0,
            'query': query
        }, status=500)
