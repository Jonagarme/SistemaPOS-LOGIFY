"""
Vista mejorada para nueva compra con detección de duplicados
Integrar estas funciones en inventario/views.py
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from productos.utils_duplicados import (
    buscar_producto_por_codigo_exacto,
    buscar_productos_similares
)
import uuid
import json


@login_required
def nueva_compra_con_deteccion(request):
    """
    Vista de nueva compra con detección automática de duplicados
    """
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
                impuesto = subtotal_con_descuento * 0.15
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
        'proveedores': proveedores,
        'usar_detector_duplicados': True  # Flag para activar el detector
    }
    return render(request, 'inventario/nueva_compra.html', context)


@login_required
def api_verificar_producto_factura(request):
    """
    API para verificar si un producto de factura ya existe antes de agregarlo
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip()
        nombre = data.get('nombre', '').strip()
        
        if not nombre:
            return JsonResponse({
                'success': False,
                'error': 'El nombre del producto es requerido'
            })
        
        # Primero buscar por código exacto
        if codigo:
            producto_exacto = buscar_producto_por_codigo_exacto(codigo)
            if producto_exacto:
                return JsonResponse({
                    'success': True,
                    'existe': True,
                    'tipo': 'exacto',
                    'producto': {
                        'id': producto_exacto.id,
                        'nombre': producto_exacto.nombre,
                        'codigo_principal': producto_exacto.codigo_principal,
                        'stock': float(producto_exacto.stock),
                        'precio_venta': float(producto_exacto.precio_venta),
                        'costo_unidad': float(producto_exacto.costo_unidad)
                    },
                    'mensaje': f'El código {codigo} ya está registrado'
                })
        
        # Buscar productos similares
        similares = buscar_productos_similares(nombre, codigo, umbral_similitud=0.75)
        
        if similares:
            return JsonResponse({
                'success': True,
                'existe': False,
                'tiene_similares': True,
                'similares': [{
                    'id': s['producto'].id,
                    'nombre': s['producto'].nombre,
                    'codigo_principal': s['producto'].codigo_principal,
                    'stock': float(s['producto'].stock),
                    'precio_venta': float(s['producto'].precio_venta),
                    'score_total': s['score_total'],
                    'tipo_coincidencia': s['tipo_coincidencia']
                } for s in similares[:5]]  # Máximo 5 similares
            })
        
        # No hay duplicados ni similares
        return JsonResponse({
            'success': True,
            'existe': False,
            'tiene_similares': False,
            'mensaje': 'Producto nuevo, sin similares'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
