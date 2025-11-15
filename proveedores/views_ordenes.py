"""
Vistas para gestión de órdenes de compra a proveedores
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal
import json

from .models import Proveedor, OrdenCompraProveedor, DetalleOrdenProveedor
from productos.models import Producto


@login_required
@require_http_methods(["GET"])
def lista_ordenes_proveedor(request):
    """Lista todas las órdenes de compra a proveedores"""
    estado = request.GET.get('estado', '')
    proveedor_id = request.GET.get('proveedor', '')
    
    ordenes = OrdenCompraProveedor.objects.select_related('proveedor').filter(anulado=False)
    
    if estado:
        ordenes = ordenes.filter(estado=estado)
    if proveedor_id:
        ordenes = ordenes.filter(proveedor_id=proveedor_id)
    
    proveedores = Proveedor.objects.filter(estado=True, anulado=False)
    
    context = {
        'ordenes': ordenes,
        'proveedores': proveedores,
        'estado_seleccionado': estado,
        'proveedor_seleccionado': proveedor_id,
    }
    
    return render(request, 'proveedores/ordenes/lista.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def crear_orden_proveedor(request):
    """Crear nueva orden de compra a proveedor"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            proveedor_id = data.get('proveedor_id')
            productos = data.get('productos', [])
            observaciones = data.get('observaciones', '')
            fecha_entrega = data.get('fecha_entrega')
            
            if not proveedor_id:
                return JsonResponse({'success': False, 'error': 'Debe seleccionar un proveedor'})
            
            if not productos:
                return JsonResponse({'success': False, 'error': 'Debe agregar al menos un producto'})
            
            proveedor = get_object_or_404(Proveedor, id=proveedor_id, estado=True, anulado=False)
            
            # Generar número de orden
            ultimo_numero = OrdenCompraProveedor.objects.filter(
                numero_orden__startswith=f'ORD-{timezone.now().year}-'
            ).count()
            numero_orden = f'ORD-{timezone.now().year}-{str(ultimo_numero + 1).zfill(4)}'
            
            # Crear orden
            orden = OrdenCompraProveedor.objects.create(
                numero_orden=numero_orden,
                proveedor=proveedor,
                observaciones=observaciones,
                fecha_entrega_estimada=fecha_entrega if fecha_entrega else None,
                creado_por=request.user.id
            )
            
            # Crear detalles
            for item in productos:
                producto = get_object_or_404(Producto, id=item['producto_id'])
                DetalleOrdenProveedor.objects.create(
                    orden=orden,
                    producto=producto,
                    cantidad=Decimal(str(item['cantidad'])),
                    precio_unitario=Decimal(str(item.get('precio', producto.costo_unidad or 0)))
                )
            
            # Calcular totales
            orden.calcular_totales()
            
            return JsonResponse({
                'success': True,
                'orden_id': orden.id,
                'numero_orden': orden.numero_orden,
                'message': f'Orden {orden.numero_orden} creada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET - Mostrar formulario
    proveedores = Proveedor.objects.filter(estado=True, anulado=False).order_by('razon_social')
    
    context = {
        'proveedores': proveedores,
    }
    
    return render(request, 'proveedores/ordenes/crear.html', context)


@login_required
@require_http_methods(["GET"])
def detalle_orden_proveedor(request, pk):
    """Ver detalle de una orden de compra"""
    orden = get_object_or_404(OrdenCompraProveedor, pk=pk)
    detalles = orden.detalles.select_related('producto').all()
    
    context = {
        'orden': orden,
        'detalles': detalles,
        'creado_por_user': orden.get_creado_por_user(),
        'editado_por_user': orden.get_editado_por_user(),
    }
    
    return render(request, 'proveedores/ordenes/detalle.html', context)


@login_required
@require_http_methods(["POST"])
def cambiar_estado_orden(request, pk):
    """Cambiar estado de una orden"""
    orden = get_object_or_404(OrdenCompraProveedor, pk=pk)
    nuevo_estado = request.POST.get('estado')
    
    if nuevo_estado in dict(OrdenCompraProveedor.ESTADO_CHOICES):
        orden.estado = nuevo_estado
        orden.editado_por = request.user.id
        orden.save()
        
        messages.success(request, f'Estado de la orden actualizado a {orden.get_estado_display()}')
    else:
        messages.error(request, 'Estado inválido')
    
    return redirect('proveedores:detalle_orden_proveedor', pk=pk)


# ==================== APIs AJAX ====================

@login_required
@require_http_methods(["GET"])
def api_buscar_productos(request):
    """
    API para buscar productos en tiempo real.
    Busca por nombre o código mientras el usuario escribe.
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'productos': []})
    
    # Buscar por nombre o código
    productos = Producto.objects.filter(
        Q(nombre__icontains=query) | Q(codigo_principal__icontains=query),
        activo=True
    ).values(
        'id', 'nombre', 'codigo_principal', 'costo_unidad', 
        'precio_venta', 'stock'
    )[:50]  # Limitar a 50 resultados
    
    productos_list = list(productos)
    
    # Formatear para respuesta
    for p in productos_list:
        p['precio_compra'] = float(p['costo_unidad'] or 0)  # Usar costo_unidad como precio de compra
        p['precio_venta'] = float(p['precio_venta'] or 0)
        p['stock'] = float(p['stock'] or 0)
        # Eliminar costo_unidad del resultado ya que lo renombramos
        p.pop('costo_unidad', None)
    
    return JsonResponse({'productos': productos_list})


@login_required
@require_http_methods(["GET"])
def api_datos_proveedor(request, pk):
    """Obtener datos de un proveedor para mostrar en el formulario"""
    proveedor = get_object_or_404(Proveedor, pk=pk, estado=True, anulado=False)
    
    return JsonResponse({
        'id': proveedor.id,
        'ruc': proveedor.ruc,
        'razon_social': proveedor.razon_social,
        'nombre_comercial': proveedor.nombre_comercial,
        'direccion': proveedor.direccion,
        'telefono': proveedor.telefono,
        'email': proveedor.email,
        'whatsapp_formateado': proveedor.whatsapp_formateado,
        'tiene_whatsapp': proveedor.tiene_whatsapp,
    })
