# -*- coding: utf-8 -*-
"""
API endpoints para consultar stock por ubicación
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from inventario.models import StockUbicacion, Ubicacion
from productos.models import Producto
import json


@login_required
@require_http_methods(["GET"])
def api_stock_por_ubicacion(request, producto_id):
    """
    Obtiene el stock de un producto en todas las ubicaciones
    
    GET /inventario/api/stock-ubicacion/<producto_id>/
    
    Response:
    {
        "success": true,
        "producto": {...},
        "stocks": [
            {
                "ubicacion_id": 1,
                "ubicacion_nombre": "Sucursal Principal",
                "ubicacion_tipo": "sucursal",
                "cantidad": 100.00,
                "stock_minimo": 10.00,
                "requiere_reorden": false,
                "stock_bajo": false
            },
            ...
        ],
        "total": 150.00
    }
    """
    try:
        producto = Producto.objects.get(id=producto_id)
        
        # Obtener stocks en todas las ubicaciones activas
        stocks = StockUbicacion.objects.filter(
            producto=producto,
            ubicacion__activo=True
        ).select_related('ubicacion')
        
        stocks_data = []
        total_stock = 0
        
        for stock in stocks:
            stocks_data.append({
                'ubicacion_id': stock.ubicacion.id,
                'ubicacion_nombre': stock.ubicacion.nombre,
                'ubicacion_codigo': stock.ubicacion.codigo,
                'ubicacion_tipo': stock.ubicacion.get_tipo_display(),
                'cantidad': float(stock.cantidad),
                'stock_minimo': float(stock.stock_minimo),
                'stock_maximo': float(stock.stock_maximo),
                'punto_reorden': float(stock.punto_reorden),
                'requiere_reorden': stock.requiere_reorden,
                'stock_bajo': stock.stock_bajo,
                'stock_excedido': stock.stock_excedido,
                'ultima_actualizacion': stock.ultima_actualizacion.strftime('%Y-%m-%d %H:%M:%S')
            })
            total_stock += float(stock.cantidad)
        
        return JsonResponse({
            'success': True,
            'producto': {
                'id': producto.id,
                'nombre': producto.nombre,
                'codigo': producto.codigo_principal
            },
            'stocks': stocks_data,
            'total_global': total_stock
        })
        
    except Producto.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Producto no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_productos_con_stock(request, ubicacion_id):
    """
    Obtiene todos los productos que tienen stock en una ubicación específica
    
    GET /inventario/api/productos-ubicacion/<ubicacion_id>/?busqueda=...
    
    Query params:
    - busqueda: término de búsqueda (opcional)
    - solo_disponibles: true/false (default: false)
    """
    try:
        ubicacion = Ubicacion.objects.get(id=ubicacion_id)
        busqueda = request.GET.get('busqueda', '').strip()
        solo_disponibles = request.GET.get('solo_disponibles', 'false').lower() == 'true'
        
        # Query base
        stocks = StockUbicacion.objects.filter(
            ubicacion=ubicacion
        ).select_related('producto')
        
        # Filtrar solo productos con stock disponible
        if solo_disponibles:
            stocks = stocks.filter(cantidad__gt=0)
        
        # Búsqueda por nombre o código
        if busqueda:
            stocks = stocks.filter(
                producto__nombre__icontains=busqueda
            ) | stocks.filter(
                producto__codigo_principal__icontains=busqueda
            )
        
        # Limitar resultados
        stocks = stocks[:50]
        
        productos_data = []
        for stock in stocks:
            productos_data.append({
                'id': stock.producto.id,
                'nombre': stock.producto.nombre,
                'codigo': stock.producto.codigo_principal,
                'stock_disponible': float(stock.cantidad),
                'stock_minimo': float(stock.stock_minimo),
                'precio_venta': float(stock.producto.precio_venta),
                'requiere_reorden': stock.requiere_reorden,
                'stock_bajo': stock.stock_bajo
            })
        
        return JsonResponse({
            'success': True,
            'ubicacion': {
                'id': ubicacion.id,
                'nombre': ubicacion.nombre,
                'tipo': ubicacion.get_tipo_display()
            },
            'productos': productos_data,
            'total_productos': len(productos_data)
        })
        
    except Ubicacion.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Ubicación no encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_resumen_stocks(request):
    """
    Obtiene un resumen de stocks por ubicación
    
    GET /inventario/api/resumen-stocks/
    
    Response:
    {
        "success": true,
        "ubicaciones": [
            {
                "id": 1,
                "nombre": "Sucursal Principal",
                "total_productos": 150,
                "productos_stock_bajo": 15,
                "valor_inventario": 45000.00
            },
            ...
        ]
    }
    """
    try:
        ubicaciones = Ubicacion.objects.filter(activo=True)
        
        resumen_data = []
        for ubicacion in ubicaciones:
            stocks = StockUbicacion.objects.filter(
                ubicacion=ubicacion
            ).select_related('producto')
            
            total_productos = stocks.count()
            productos_con_stock = stocks.filter(cantidad__gt=0).count()
            productos_stock_bajo = stocks.filter(
                cantidad__lte=models.F('stock_minimo'),
                stock_minimo__gt=0
            ).count()
            
            # Calcular valor del inventario
            valor_inventario = 0
            for stock in stocks:
                valor_inventario += float(stock.cantidad) * float(stock.producto.precio_venta)
            
            resumen_data.append({
                'id': ubicacion.id,
                'codigo': ubicacion.codigo,
                'nombre': ubicacion.nombre,
                'tipo': ubicacion.get_tipo_display(),
                'total_productos': total_productos,
                'productos_con_stock': productos_con_stock,
                'productos_stock_bajo': productos_stock_bajo,
                'valor_inventario': round(valor_inventario, 2)
            })
        
        return JsonResponse({
            'success': True,
            'ubicaciones': resumen_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
