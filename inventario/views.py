from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import (
    Compra, DetalleCompra, Kardex, AjusteInventario, OrdenCompra, DetalleOrdenCompra,
    TransferenciaStock, DetalleTransferencia, Ubicacion, ConfiguracionStock, KardexMovimiento,
    StockUbicacion
)
from productos.models import Producto
from proveedores.models import Proveedor
import uuid


@login_required
def lista_compras(request):
    """Lista todas las compras"""
    compras = Compra.objects.all().select_related('proveedor', 'usuario')
    
    paginator = Paginator(compras, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'titulo': 'Compras'
    }
    return render(request, 'inventario/compras.html', context)


@login_required
def nueva_compra(request):
    """Crear nueva compra"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Crear la compra
                compra = Compra.objects.create(
                    numero_compra=f"COMP-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}",
                    numero_factura_proveedor=request.POST.get('numero_factura_proveedor', ''),
                    fecha_factura=request.POST.get('fecha_factura'),
                    proveedor_id=request.POST.get('proveedor'),
                    usuario=request.user,
                    tipo_pago=request.POST.get('tipo_pago', 'efectivo'),
                    observaciones=request.POST.get('observaciones', '')
                )
                
                # Procesar productos
                subtotal = 0
                productos_data = {}
                
                # Extraer datos de productos del POST
                for key, value in request.POST.items():
                    if key.startswith('productos[') and '][' in key:
                        # Extraer índice y campo
                        parts = key.replace('productos[', '').replace(']', '').split('][')
                        if len(parts) == 2:
                            index, field = parts
                            if index not in productos_data:
                                productos_data[index] = {}
                            productos_data[index][field] = value
                
                # Crear detalles de compra
                for index, producto_data in productos_data.items():
                    if all(key in producto_data for key in ['id', 'cantidad', 'precio']):
                        producto = get_object_or_404(Producto, id=producto_data['id'])
                        cantidad = int(producto_data['cantidad'])
                        precio_unitario = float(producto_data['precio'])
                        
                        detalle = DetalleCompra.objects.create(
                            compra=compra,
                            producto=producto,
                            cantidad=cantidad,
                            precio_unitario=precio_unitario
                        )
                        
                        subtotal += detalle.subtotal
                        
                        # Actualizar stock del producto
                        producto.stock += cantidad
                        producto.save()
                        
                        # Crear registro en Kardex
                        Kardex.objects.create(
                            producto=producto,
                            tipo_movimiento='entrada',
                            cantidad=cantidad,
                            precio_unitario=precio_unitario,
                            motivo=f'Compra {compra.numero_compra}',
                            documento_referencia=compra.numero_compra,
                            usuario=request.user
                        )
                
                # Calcular totales
                descuento = float(request.POST.get('descuento', 0))
                subtotal_con_descuento = subtotal - descuento
                impuesto = subtotal_con_descuento * 0.15  # IVA 15%
                total = subtotal_con_descuento + impuesto
                
                # Actualizar totales de la compra
                compra.subtotal = subtotal
                compra.descuento = descuento
                compra.impuesto = impuesto
                compra.total = total
                compra.save()
                
                messages.success(request, f'Compra {compra.numero_compra} creada exitosamente')
                return redirect('inventario:detalle_compra', pk=compra.pk)
                
        except Exception as e:
            messages.error(request, f'Error al crear la compra: {str(e)}')
    
    # GET request - mostrar formulario
    proveedores = Proveedor.objects.filter(estado=True, anulado=False).order_by('nombre_comercial')
    
    context = {
        'titulo': 'Nueva Compra',
        'proveedores': proveedores
    }
    return render(request, 'inventario/nueva_compra.html', context)


@login_required
def detalle_compra(request, pk):
    """Ver detalles de una compra"""
    compra = get_object_or_404(Compra, pk=pk)
    
    context = {
        'compra': compra,
        'titulo': f'Compra {compra.numero_compra}'
    }
    return render(request, 'inventario/detalle_compra.html', context)


@login_required
def editar_compra(request, pk):
    """Editar compra existente"""
    compra = get_object_or_404(Compra, pk=pk)
    
    if request.method == 'POST':
        # Lógica para editar compra
        messages.success(request, 'Compra actualizada exitosamente')
        return redirect('inventario:compras')
    
    context = {
        'compra': compra,
        'titulo': 'Editar Compra'
    }
    return render(request, 'inventario/editar_compra.html', context)


@login_required
def anular_compra(request, pk):
    """Anular una compra"""
    compra = get_object_or_404(Compra, pk=pk)
    
    if request.method == 'POST':
        compra.estado = 'anulada'
        compra.save()
        messages.success(request, 'Compra anulada exitosamente')
        return redirect('inventario:compras')
    
    context = {
        'compra': compra,
        'titulo': 'Anular Compra'
    }
    return render(request, 'inventario/anular_compra.html', context)


@login_required
@login_required
def kardex_general(request):
    """Vista general del kardex usando tabla kardex_movimientos"""
    # Obtener filtros de la request
    producto_id = request.GET.get('producto_id')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    tipo_movimiento = request.GET.get('tipo_movimiento')
    
    # Query base usando la nueva tabla
    movimientos = KardexMovimiento.objects.all()
    
    # Aplicar filtros
    if producto_id:
        movimientos = movimientos.filter(idProducto=producto_id)
    
    if fecha_desde:
        from datetime import datetime
        fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
        movimientos = movimientos.filter(fecha__gte=fecha_desde_dt)
    
    if fecha_hasta:
        from datetime import datetime
        fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
        movimientos = movimientos.filter(fecha__lte=fecha_hasta_dt)
    
    if tipo_movimiento:
        movimientos = movimientos.filter(tipoMovimiento__icontains=tipo_movimiento)
    
    # Ordenar por fecha descendente
    movimientos = movimientos.order_by('-fecha', '-id')
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(movimientos, 25)  # 25 movimientos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener productos para el filtro
    productos = Producto.objects.filter(activo=True).order_by('nombre')
    
    # Tipos de movimiento únicos para filtro
    tipos_movimiento = ['VENTA', 'COMPRA', 'AJUSTE INGRESO', 'AJUSTE EGRESO', 'DEVOLUCIÓN']
    
    # Calcular estadísticas generales
    # Usar la misma consulta filtrada para las estadísticas
    movimientos_stats = KardexMovimiento.objects.all()
    
    # Aplicar los mismos filtros que se aplicaron arriba
    if producto_id:
        movimientos_stats = movimientos_stats.filter(idProducto=producto_id)
    if fecha_desde:
        movimientos_stats = movimientos_stats.filter(fecha__gte=fecha_desde_dt)
    if fecha_hasta:
        movimientos_stats = movimientos_stats.filter(fecha__lte=fecha_hasta_dt)
    if tipo_movimiento:
        movimientos_stats = movimientos_stats.filter(tipoMovimiento__icontains=tipo_movimiento)
    
    # Calcular totales
    from django.db.models import Sum, Count
    stats = movimientos_stats.aggregate(
        total_movimientos=Count('id'),
        total_entradas=Sum('ingreso'),
        total_salidas=Sum('egreso')
    )
    
    # Contar productos únicos con movimientos
    productos_activos = movimientos_stats.values('idProducto').distinct().count()
    
    context = {
        'page_obj': page_obj,
        'productos': productos,
        'tipos_movimiento': tipos_movimiento,
        'estadisticas': {
            'total_movimientos': stats['total_movimientos'] or 0,
            'total_entradas': stats['total_entradas'] or 0,
            'total_salidas': stats['total_salidas'] or 0,
            'productos_activos': productos_activos
        },
        'filtros': {
            'producto_id': producto_id,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'tipo_movimiento': tipo_movimiento,
        },
        'titulo': 'Kardex General'
    }
    return render(request, 'inventario/kardex_general.html', context)


@login_required
def kardex_producto(request, producto_id):
    """Kardex de un producto específico usando tabla kardex_movimientos"""
    producto = get_object_or_404(Producto, pk=producto_id)
    
    # Obtener filtros adicionales
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    tipo_movimiento = request.GET.get('tipo_movimiento')
    
    # Obtener movimientos del producto específico
    movimientos = KardexMovimiento.objects.filter(idProducto=producto_id)
    
    # Aplicar filtros de fecha
    if fecha_desde:
        from datetime import datetime
        fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
        movimientos = movimientos.filter(fecha__gte=fecha_desde_dt)
    
    if fecha_hasta:
        from datetime import datetime
        fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
        movimientos = movimientos.filter(fecha__lte=fecha_hasta_dt)
    
    if tipo_movimiento:
        movimientos = movimientos.filter(tipoMovimiento__icontains=tipo_movimiento)
    
    # Ordenar por fecha descendente
    movimientos = movimientos.order_by('-fecha', '-id')
    
    # Calcular estadísticas del producto
    total_ingresos = sum([mov.ingreso for mov in movimientos])
    total_egresos = sum([mov.egreso for mov in movimientos])
    saldo_actual = movimientos.first().saldo if movimientos.exists() else 0
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(movimientos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Tipos de movimiento para filtro
    tipos_movimiento = ['VENTA', 'COMPRA', 'AJUSTE INGRESO', 'AJUSTE EGRESO', 'DEVOLUCIÓN']
    
    context = {
        'producto': producto,
        'page_obj': page_obj,
        'tipos_movimiento': tipos_movimiento,
        'estadisticas': {
            'total_ingresos': total_ingresos,
            'total_egresos': total_egresos,
            'saldo_actual': saldo_actual,
            'total_movimientos': movimientos.count()
        },
        'filtros': {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'tipo_movimiento': tipo_movimiento,
        },
        'titulo': f'Kardex: {producto.nombre}'
    }
    return render(request, 'inventario/kardex_producto.html', context)


@login_required
def exportar_kardex(request):
    """Exportar kardex a Excel"""
    # Lógica para exportar
    messages.success(request, 'Kardex exportado exitosamente')
    return redirect('inventario:kardex')


@login_required
def lista_ajustes(request):
    """Lista todos los ajustes de inventario"""
    ajustes = AjusteInventario.objects.all().select_related('usuario')
    
    paginator = Paginator(ajustes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'titulo': 'Ajustes de Inventario'
    }
    return render(request, 'inventario/ajustes.html', context)


@login_required
def nuevo_ajuste(request):
    """Crear nuevo ajuste de inventario"""
    if request.method == 'POST':
        # Lógica para crear ajuste
        messages.success(request, 'Ajuste creado exitosamente')
        return redirect('inventario:ajustes')
    
    context = {
        'productos': Producto.objects.filter(activo=True),
        'titulo': 'Nuevo Ajuste'
    }
    return render(request, 'inventario/nuevo_ajuste.html', context)


@login_required
def detalle_ajuste(request, pk):
    """Ver detalles de un ajuste"""
    ajuste = get_object_or_404(AjusteInventario, pk=pk)
    
    context = {
        'ajuste': ajuste,
        'titulo': f'Ajuste {ajuste.numero_ajuste}'
    }
    return render(request, 'inventario/detalle_ajuste.html', context)


@login_required
def reportes_inventario(request):
    """Reportes de inventario"""
    from django.db import connection
    from productos.models import Producto
    
    # Obtener datos del resumen
    total_productos = 0
    valor_inventario = 0
    bajo_stock = 0
    sin_stock = 0
    
    try:
        # Total de productos activos
        total_productos = Producto.objects.filter(activo=True, anulado=False).count()
        
        # Valor total del inventario
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(SUM(stock * costo_unidad), 0) 
                FROM productos 
                WHERE activo = 1 AND anulado = 0 AND stock > 0
            """)
            result = cursor.fetchone()
            if result:
                valor_inventario = float(result[0] or 0)
        
        # Productos bajo stock
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM productos 
                WHERE activo = 1 AND anulado = 0 AND stock <= stockMinimo AND stockMinimo > 0
            """)
            result = cursor.fetchone()
            if result:
                bajo_stock = result[0] or 0
        
        # Productos sin stock
        sin_stock = Producto.objects.filter(activo=True, anulado=False, stock=0).count()
        
    except Exception as e:
        print(f"Error obteniendo datos del resumen: {e}")
    
    context = {
        'titulo': 'Reportes de Inventario',
        'total_productos': total_productos,
        'valor_inventario': f"{valor_inventario:,.2f}",
        'bajo_stock': bajo_stock,
        'sin_stock': sin_stock,
    }
    return render(request, 'inventario/reportes_simple.html', context)


@login_required
def inventario_valorado(request):
    """Reporte de inventario valorado"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Obtener parámetros de filtrado
    buscar = request.GET.get('buscar', '')
    categoria = request.GET.get('categoria', '')
    ordenar = request.GET.get('ordenar', 'nombre')
    por_pagina = int(request.GET.get('por_pagina', 25))
    
    # Construir consulta
    productos = Producto.objects.filter(activo=True, stock__gt=0)
    
    # Aplicar filtros
    if buscar:
        productos = productos.filter(
            Q(nombre__icontains=buscar) | 
            Q(codigo_principal__icontains=buscar) |
            Q(descripcion__icontains=buscar)
        )
    
    if categoria:
        productos = productos.filter(id_categoria__nombre__icontains=categoria)
    
    # Aplicar ordenamiento
    if ordenar == 'nombre':
        productos = productos.order_by('nombre')
    elif ordenar == 'stock':
        productos = productos.order_by('-stock')
    elif ordenar == 'codigo':
        productos = productos.order_by('codigo_principal')
    elif ordenar == 'valor':
        productos = productos.order_by('-stock')  # Simplificado por ahora
    else:
        productos = productos.order_by('nombre')
    
    # Configurar paginación
    paginator = Paginator(productos, por_pagina)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'productos': page_obj,
        'titulo': 'Inventario Valorado',
        'total_productos': paginator.count,
        'productos_por_pagina': por_pagina,
        'buscar': buscar,
        'categoria': categoria,
        'ordenar': ordenar,
    }
    return render(request, 'inventario/inventario_valorado.html', context)


@login_required
def reporte_movimientos(request):
    """Reporte de movimientos de inventario"""
    movimientos = Kardex.objects.all().select_related('producto', 'usuario')[:100]
    
    context = {
        'movimientos': movimientos,
        'titulo': 'Movimientos de Inventario'
    }
    return render(request, 'inventario/reporte_movimientos.html', context)


# ========================
# ÓRDENES DE COMPRA (PO)
# ========================

@login_required
def lista_ordenes_compra(request):
    """Lista todas las órdenes de compra"""
    ordenes = OrdenCompra.objects.all().select_related('proveedor', 'ubicacion_destino', 'usuario_creacion')
    
    # Filtros
    estado = request.GET.get('estado')
    proveedor_id = request.GET.get('proveedor')
    
    if estado:
        ordenes = ordenes.filter(estado=estado)
    if proveedor_id:
        ordenes = ordenes.filter(proveedor_id=proveedor_id)
    
    paginator = Paginator(ordenes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Para los filtros
    proveedores = Proveedor.objects.filter(estado=True)
    estados = OrdenCompra.ESTADO_ORDEN
    
    context = {
        'page_obj': page_obj,
        'proveedores': proveedores,
        'estados': estados,
        'filtro_estado': estado,
        'filtro_proveedor': proveedor_id,
        'titulo': 'Órdenes de Compra'
    }
    return render(request, 'inventario/ordenes_compra.html', context)


@login_required
def crear_orden_compra(request):
    """Crear nueva orden de compra"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Crear la orden
                orden = OrdenCompra.objects.create(
                    numero_orden=f"OC-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                    proveedor_id=request.POST.get('proveedor'),
                    ubicacion_destino_id=request.POST.get('ubicacion_destino'),
                    fecha_entrega_esperada=request.POST.get('fecha_entrega_esperada') or None,
                    prioridad=request.POST.get('prioridad', 'normal'),
                    observaciones=request.POST.get('observaciones', ''),
                    usuario_creacion=request.user
                )
                
                # Agregar productos (si se enviaron)
                productos_data = request.POST.getlist('productos[]')
                cantidades_data = request.POST.getlist('cantidades[]')
                
                total = 0
                for i, producto_id in enumerate(productos_data):
                    if i < len(cantidades_data) and cantidades_data[i]:
                        producto = Producto.objects.get(id=producto_id)
                        cantidad = int(cantidades_data[i])
                        
                        DetalleOrdenCompra.objects.create(
                            orden=orden,
                            producto=producto,
                            cantidad_solicitada=cantidad,
                            precio_unitario=producto.precio_compra or 0,
                            stock_actual=producto.stock,
                            stock_minimo=getattr(producto, 'stock_minimo', 0)
                        )
                        
                        total += cantidad * (producto.precio_compra or 0)
                
                orden.subtotal = total
                orden.total = total
                orden.save()
                
                messages.success(request, f'Orden de compra {orden.numero_orden} creada exitosamente')
                return redirect('inventario:detalle_orden_compra', pk=orden.pk)
                
        except Exception as e:
            messages.error(request, f'Error al crear la orden: {str(e)}')
    
    # GET request
    proveedores = Proveedor.objects.filter(estado=True)
    ubicaciones = Ubicacion.objects.filter(activo=True)
    productos = Producto.objects.filter(activo=True)
    
    context = {
        'proveedores': proveedores,
        'ubicaciones': ubicaciones,
        'productos': productos,
        'titulo': 'Nueva Orden de Compra'
    }
    return render(request, 'inventario/crear_orden_compra.html', context)


@login_required
def detalle_orden_compra(request, pk):
    """Ver detalles de una orden de compra"""
    orden = get_object_or_404(OrdenCompra, pk=pk)
    
    context = {
        'orden': orden,
        'titulo': f'Orden de Compra {orden.numero_orden}'
    }
    return render(request, 'inventario/detalle_orden_compra.html', context)


@login_required
def enviar_orden_compra(request, pk):
    """Enviar orden de compra al proveedor"""
    orden = get_object_or_404(OrdenCompra, pk=pk)
    
    if orden.puede_ser_enviada:
        orden.marcar_como_enviada(request.user)
        messages.success(request, f'Orden {orden.numero_orden} enviada al proveedor')
    else:
        messages.error(request, 'La orden no puede ser enviada en su estado actual')
    
    return redirect('inventario:detalle_orden_compra', pk=pk)


@login_required
def generar_ordenes_automaticas(request):
    """Generar órdenes de compra automáticas basadas en stock mínimo"""
    if request.method == 'POST':
        try:
            ordenes_generadas = 0
            configuraciones = ConfiguracionStock.objects.filter(
                generar_orden_automatica=True,
                proveedor_preferido__isnull=False
            )
            
            for config in configuraciones:
                # Verificar si necesita reorden (lógica simplificada)
                if config.necesita_reorden:
                    # Crear orden automática
                    orden = OrdenCompra.objects.create(
                        numero_orden=f"OC-AUTO-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                        proveedor=config.proveedor_preferido,
                        ubicacion_destino=config.ubicacion,
                        prioridad='normal',
                        observaciones='Orden generada automáticamente por stock bajo',
                        generada_automaticamente=True,
                        usuario_creacion=request.user
                    )
                    
                    DetalleOrdenCompra.objects.create(
                        orden=orden,
                        producto=config.producto,
                        cantidad_solicitada=config.cantidad_reorden,
                        precio_unitario=config.producto.precio_compra or 0,
                        stock_actual=config.producto.stock,
                        stock_minimo=config.stock_minimo,
                        motivo_solicitud='Stock bajo - Reorden automático'
                    )
                    
                    orden.subtotal = config.cantidad_reorden * (config.producto.precio_compra or 0)
                    orden.total = orden.subtotal
                    orden.save()
                    
                    ordenes_generadas += 1
            
            if ordenes_generadas > 0:
                messages.success(request, f'Se generaron {ordenes_generadas} órdenes de compra automáticas')
            else:
                messages.info(request, 'No se encontraron productos que requieran reorden automático')
                
        except Exception as e:
            messages.error(request, f'Error al generar órdenes automáticas: {str(e)}')
    
    return redirect('inventario:lista_ordenes_compra')


# ============================
# TRANSFERENCIAS DE STOCK
# ============================

@login_required
def lista_transferencias(request):
    """Lista todas las transferencias de stock"""
    transferencias = TransferenciaStock.objects.all().select_related(
        'ubicacion_origen', 'ubicacion_destino', 'usuario_creacion'
    )
    
    # Filtros
    estado = request.GET.get('estado')
    ubicacion_origen = request.GET.get('ubicacion_origen')
    ubicacion_destino = request.GET.get('ubicacion_destino')
    
    if estado:
        transferencias = transferencias.filter(estado=estado)
    if ubicacion_origen:
        transferencias = transferencias.filter(ubicacion_origen_id=ubicacion_origen)
    if ubicacion_destino:
        transferencias = transferencias.filter(ubicacion_destino_id=ubicacion_destino)
    
    paginator = Paginator(transferencias, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Para los filtros
    ubicaciones = Ubicacion.objects.filter(activo=True)
    estados = TransferenciaStock.ESTADO_TRANSFERENCIA
    
    context = {
        'page_obj': page_obj,
        'ubicaciones': ubicaciones,
        'estados': estados,
        'filtro_estado': estado,
        'filtro_ubicacion_origen': ubicacion_origen,
        'filtro_ubicacion_destino': ubicacion_destino,
        'titulo': 'Transferencias de Stock'
    }
    return render(request, 'inventario/transferencias.html', context)


@login_required
def crear_transferencia(request):
    """Crear nueva transferencia de stock"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                ubicacion_origen_id = request.POST.get('ubicacion_origen')
                ubicacion_destino_id = request.POST.get('ubicacion_destino')
                
                # Validaciones básicas
                if not ubicacion_origen_id or not ubicacion_destino_id:
                    messages.error(request, 'Debe seleccionar ubicación origen y destino')
                    return redirect('inventario:crear_transferencia')
                
                if ubicacion_origen_id == ubicacion_destino_id:
                    messages.error(request, 'La ubicación origen y destino no pueden ser la misma')
                    return redirect('inventario:crear_transferencia')
                
                # Crear la transferencia
                transferencia = TransferenciaStock.objects.create(
                    numero_transferencia=f"TR-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                    ubicacion_origen_id=ubicacion_origen_id,
                    ubicacion_destino_id=ubicacion_destino_id,
                    tipo=request.POST.get('tipo', 'manual'),
                    motivo=request.POST.get('motivo', ''),
                    observaciones=request.POST.get('observaciones', ''),
                    usuario_creacion=request.user
                )
                
                # Agregar productos y validar stock
                productos_data = request.POST.getlist('productos[]')
                cantidades_data = request.POST.getlist('cantidades[]')
                
                if not productos_data:
                    raise ValueError('Debe agregar al menos un producto a la transferencia')
                
                for i, producto_id in enumerate(productos_data):
                    if i < len(cantidades_data) and cantidades_data[i]:
                        producto = Producto.objects.get(id=producto_id)
                        cantidad = Decimal(cantidades_data[i])
                        
                        if cantidad <= 0:
                            raise ValueError(f'La cantidad debe ser mayor a 0 para {producto.nombre}')
                        
                        # Obtener stock en ubicación origen
                        try:
                            stock_origen = StockUbicacion.objects.get(
                                producto=producto,
                                ubicacion_id=ubicacion_origen_id
                            )
                            stock_disponible = stock_origen.cantidad
                        except StockUbicacion.DoesNotExist:
                            stock_disponible = 0
                        
                        # Validar stock suficiente
                        if stock_disponible < cantidad:
                            raise ValueError(
                                f'Stock insuficiente de {producto.nombre}. '
                                f'Disponible: {stock_disponible}, Solicitado: {cantidad}'
                            )
                        
                        DetalleTransferencia.objects.create(
                            transferencia=transferencia,
                            producto=producto,
                            cantidad=cantidad,
                            stock_origen_antes=stock_disponible
                        )
                
                messages.success(request, f'Transferencia {transferencia.numero_transferencia} creada exitosamente')
                return redirect('inventario:detalle_transferencia', pk=transferencia.pk)
                
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error al crear la transferencia: {str(e)}')
    
    # GET request
    ubicaciones = Ubicacion.objects.filter(activo=True)
    productos = Producto.objects.filter(activo=True)
    
    context = {
        'ubicaciones': ubicaciones,
        'productos': productos,
        'titulo': 'Nueva Transferencia de Stock'
    }
    return render(request, 'inventario/crear_transferencia.html', context)


@login_required
def detalle_transferencia(request, pk):
    """Ver detalles de una transferencia"""
    transferencia = get_object_or_404(TransferenciaStock, pk=pk)
    
    context = {
        'transferencia': transferencia,
        'titulo': f'Transferencia {transferencia.numero_transferencia}'
    }
    return render(request, 'inventario/detalle_transferencia.html', context)


@login_required
def enviar_transferencia(request, pk):
    """Enviar transferencia (marcar como en tránsito)"""
    transferencia = get_object_or_404(TransferenciaStock, pk=pk)
    
    if transferencia.estado == 'pendiente':
        transferencia.enviar(request.user)
        messages.success(request, f'Transferencia {transferencia.numero_transferencia} enviada')
    else:
        messages.error(request, 'La transferencia no puede ser enviada en su estado actual')
    
    return redirect('inventario:detalle_transferencia', pk=pk)


@login_required
def recibir_transferencia(request, pk):
    """Recibir transferencia completa"""
    transferencia = get_object_or_404(TransferenciaStock, pk=pk)
    
    if transferencia.estado == 'en_transito':
        transferencia.recibir(request.user)
        
        # Marcar todos los productos como recibidos completamente
        for detalle in transferencia.detalles.all():
            detalle.cantidad_recibida = detalle.cantidad
            detalle.save()
        
        messages.success(request, f'Transferencia {transferencia.numero_transferencia} recibida completamente')
    else:
        messages.error(request, 'La transferencia no puede ser recibida en su estado actual')
    
    return redirect('inventario:detalle_transferencia', pk=pk)


# ============================
# CONFIGURACIÓN DE STOCK
# ============================

@login_required
def configuracion_stock(request):
    """Configurar niveles de stock por producto"""
    configuraciones = ConfiguracionStock.objects.all().select_related('producto', 'ubicacion', 'proveedor_preferido')
    
    paginator = Paginator(configuraciones, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'titulo': 'Configuración de Stock'
    }
    return render(request, 'inventario/configuracion_stock.html', context)


@login_required
def crear_configuracion_stock(request):
    """Crear nueva configuración de stock"""
    if request.method == 'POST':
        try:
            ConfiguracionStock.objects.create(
                producto_id=request.POST.get('producto'),
                ubicacion_id=request.POST.get('ubicacion'),
                stock_minimo=int(request.POST.get('stock_minimo', 0)),
                stock_maximo=int(request.POST.get('stock_maximo', 0)),
                punto_reorden=int(request.POST.get('punto_reorden', 0)),
                cantidad_reorden=int(request.POST.get('cantidad_reorden', 0)),
                generar_orden_automatica=request.POST.get('generar_orden_automatica') == 'on',
                proveedor_preferido_id=request.POST.get('proveedor_preferido') or None,
                usuario=request.user
            )
            
            messages.success(request, 'Configuración de stock creada exitosamente')
            return redirect('inventario:configuracion_stock')
            
        except Exception as e:
            messages.error(request, f'Error al crear la configuración: {str(e)}')
    
    # GET request
    productos = Producto.objects.filter(activo=True)
    ubicaciones = Ubicacion.objects.filter(activo=True)
    proveedores = Proveedor.objects.filter(estado=True)
    
    context = {
        'productos': productos,
        'ubicaciones': ubicaciones,
        'proveedores': proveedores,
        'titulo': 'Nueva Configuración de Stock'
    }
    return render(request, 'inventario/crear_configuracion_stock.html', context)


# ============================
# UBICACIONES
# ============================

@login_required
def lista_ubicaciones(request):
    """Lista todas las ubicaciones"""
    ubicaciones = Ubicacion.objects.all()
    
    context = {
        'ubicaciones': ubicaciones,
        'titulo': 'Ubicaciones'
    }
    return render(request, 'inventario/ubicaciones.html', context)


@login_required
def crear_ubicacion(request):
    """Crear nueva ubicación"""
    if request.method == 'POST':
        try:
            Ubicacion.objects.create(
                codigo=request.POST.get('codigo'),
                nombre=request.POST.get('nombre'),
                tipo=request.POST.get('tipo'),
                direccion=request.POST.get('direccion', ''),
                telefono=request.POST.get('telefono', ''),
                responsable=request.POST.get('responsable', ''),
                es_principal=request.POST.get('es_principal') == 'on'
            )
            
            messages.success(request, 'Ubicación creada exitosamente')
            return redirect('inventario:ubicaciones')
            
        except Exception as e:
            messages.error(request, f'Error al crear la ubicación: {str(e)}')
    
    context = {
        'titulo': 'Nueva Ubicación'
    }
    return render(request, 'inventario/crear_ubicacion.html', context)


@login_required
def compras_por_proveedor(request):
    """Reporte de compras por proveedor"""
    context = {
        'titulo': 'Compras por Proveedor'
    }
    return render(request, 'inventario/compras_por_proveedor.html', context)


# Función auxiliar para registrar movimientos en kardex_movimientos
def registrar_movimiento_kardex(producto_id, tipo_movimiento, detalle, ingreso=0, egreso=0, saldo_actual=None):
    """
    Función auxiliar para registrar movimientos en la tabla kardex_movimientos
    
    Args:
        producto_id: ID del producto
        tipo_movimiento: Tipo de movimiento (VENTA, COMPRA, AJUSTE INGRESO, etc.)
        detalle: Descripción del movimiento
        ingreso: Cantidad de ingreso (default 0)
        egreso: Cantidad de egreso (default 0)
        saldo_actual: Saldo actual del producto (si no se proporciona, se calcula)
    """
    from django.db import connection
    
    try:
        # Si no se proporciona saldo actual, obtenerlo de la base de datos
        if saldo_actual is None:
            # Obtener el stock actual del producto
            producto = Producto.objects.get(id=producto_id)
            saldo_actual = producto.stock
        else:
            # Calcular el nuevo saldo basado en el movimiento
            saldo_actual = saldo_actual + ingreso - egreso
        
        # Insertar el movimiento en la tabla kardex_movimientos
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO kardex_movimientos 
                (idProducto, fecha, tipoMovimiento, detalle, ingreso, egreso, saldo)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s)
            """, [producto_id, tipo_movimiento, detalle, ingreso, egreso, saldo_actual])
        
        return True
        
    except Exception as e:
        print(f"Error al registrar movimiento kardex: {e}")
        return False
