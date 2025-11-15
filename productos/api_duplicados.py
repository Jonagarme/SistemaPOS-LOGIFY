"""
Vistas API para detección de productos duplicados
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from productos.models import Producto
from productos.utils_duplicados import (
    buscar_productos_similares,
    vincular_codigo_alternativo,
    obtener_producto_con_alternativo
)
import json


@login_required
@require_http_methods(["POST"])
def api_buscar_similares(request):
    """
    API para buscar productos similares
    
    POST params:
        - nombre: Nombre del producto
        - codigo: Código del producto (opcional)
        - umbral: Umbral de similitud 0-1 (opcional, default 0.75)
    """
    try:
        data = json.loads(request.body)
        nombre = data.get('nombre', '').strip()
        codigo = data.get('codigo', '').strip()
        umbral = float(data.get('umbral', 0.75))
        
        if not nombre:
            return JsonResponse({
                'success': False,
                'error': 'El nombre del producto es requerido'
            }, status=400)
        
        # Buscar productos similares
        similares = buscar_productos_similares(nombre, codigo, umbral)
        
        # Formatear respuesta
        resultados = []
        for item in similares:
            producto = item['producto']
            resultados.append({
                'id': producto.id,
                'nombre': producto.nombre,
                'codigo_principal': producto.codigo_principal,
                'codigo_auxiliar': producto.codigo_auxiliar or '',
                'stock': float(producto.stock),
                'precio': float(producto.precio_venta),
                'similitud_nombre': item['similitud_nombre'],
                'similitud_codigo': item['similitud_codigo'],
                'score_total': item['score_total'],
                'tipo_coincidencia': item['tipo_coincidencia'],
                'mensaje': item['mensaje']
            })
        
        return JsonResponse({
            'success': True,
            'encontrados': len(resultados),
            'productos': resultados
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_vincular_codigo(request):
    """
    API para vincular un código alternativo a un producto existente
    
    POST params:
        - producto_id: ID del producto
        - codigo: Código alternativo
        - nombre_proveedor: Nombre según proveedor (opcional)
        - id_proveedor: ID del proveedor (opcional)
    """
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        codigo = data.get('codigo', '').strip()
        nombre_proveedor = data.get('nombre_proveedor', '').strip()
        id_proveedor = data.get('id_proveedor')
        
        if not producto_id or not codigo:
            return JsonResponse({
                'success': False,
                'error': 'producto_id y codigo son requeridos'
            }, status=400)
        
        # Vincular el código
        success, mensaje, codigo_alt = vincular_codigo_alternativo(
            producto_id, codigo, nombre_proveedor, id_proveedor
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'mensaje': mensaje,
                'codigo_alternativo': {
                    'id': codigo_alt.id,
                    'codigo': codigo_alt.codigo,
                    'producto_id': codigo_alt.producto.id,
                    'producto_nombre': codigo_alt.producto.nombre
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': mensaje
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_obtener_por_codigo(request, codigo):
    """
    API para obtener un producto por cualquier tipo de código
    GET /api/producto/codigo/<codigo>/
    """
    try:
        producto, tipo_codigo = obtener_producto_con_alternativo(codigo)
        
        if producto:
            return JsonResponse({
                'success': True,
                'producto': {
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'codigo_principal': producto.codigo_principal,
                    'codigo_auxiliar': producto.codigo_auxiliar or '',
                    'stock': float(producto.stock),
                    'precio_venta': float(producto.precio_venta),
                    'costo_unidad': float(producto.costo_unidad),
                    'tipo_codigo': tipo_codigo
                },
                'mensaje': f'Producto encontrado por código {tipo_codigo}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'No se encontró producto con código: {codigo}'
            }, status=404)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_buscar_similares_lote(request):
    """
    API optimizada para buscar similares de múltiples productos a la vez
    
    POST params:
        - productos: Array de objetos con {nombre, codigo}
        - umbral: Umbral de similitud 0-1 (opcional, default 0.75)
        - solo_nombre: Si true, solo busca por nombre (más rápido)
    
    Returns:
        {
            success: true,
            resultados: [
                {
                    codigo_entrada: "...",
                    nombre_entrada: "...",
                    similares: [...],
                    tiene_similares: true/false
                }
            ]
        }
    """
    try:
        data = json.loads(request.body)
        productos_entrada = data.get('productos', [])
        umbral = float(data.get('umbral', 0.75))
        solo_nombre = data.get('solo_nombre', True)  # Por defecto solo buscar por nombre
        
        if not productos_entrada:
            return JsonResponse({
                'success': False,
                'error': 'Se requiere al menos un producto'
            }, status=400)
        
        resultados = []
        
        for prod_entrada in productos_entrada:
            nombre = prod_entrada.get('nombre', '').strip()
            codigo = prod_entrada.get('codigo', '').strip()
            
            if not nombre:
                continue
            
            # Buscar productos similares
            # Si solo_nombre=True, pasamos código vacío para que no busque por código
            codigo_busqueda = '' if solo_nombre else codigo
            similares = buscar_productos_similares(nombre, codigo_busqueda, umbral)
            
            # Formatear similares
            similares_formateados = []
            for item in similares:
                producto = item['producto']
                similares_formateados.append({
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'codigo_principal': producto.codigo_principal,
                    'stock': float(producto.stock),
                    'precio': float(producto.precio_venta),
                    'score_total': item['score_total'],
                    'tipo_coincidencia': item['tipo_coincidencia']
                })
            
            resultados.append({
                'codigo_entrada': codigo,
                'nombre_entrada': nombre,
                'similares': similares_formateados,
                'tiene_similares': len(similares_formateados) > 0
            })
        
        return JsonResponse({
            'success': True,
            'total_procesados': len(resultados),
            'resultados': resultados
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
