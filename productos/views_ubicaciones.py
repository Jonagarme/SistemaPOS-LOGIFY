from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, connection
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import Producto
import json


@login_required
def ubicaciones_productos(request):
    """Vista principal del módulo de ubicaciones de productos"""
    
    # Obtener productos sin ubicación
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.codigoPrincipal, p.nombre, p.stock
            FROM productos p
            LEFT JOIN productos_ubicacionproducto u ON p.id = u.producto_id AND u.activo = 1
            WHERE p.activo = 1 AND p.anulado = 0 AND u.id IS NULL
            ORDER BY p.nombre
            LIMIT 20
        """)
        productos_sin_ubicacion = cursor.fetchall()
    
    # Obtener estadísticas
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT p.id) as total_productos,
                COUNT(DISTINCT u.id) as productos_ubicados,
                COUNT(DISTINCT s.id) as total_secciones,
                COUNT(DISTINCT pr.id) as total_perchas
            FROM productos p
            LEFT JOIN productos_ubicacionproducto u ON p.id = u.producto_id AND u.activo = 1
            LEFT JOIN productos_percha pr ON u.percha_id = pr.id AND pr.activo = 1
            LEFT JOIN productos_seccion s ON pr.seccion_id = s.id AND s.activo = 1
            WHERE p.activo = 1 AND p.anulado = 0
        """)
        estadisticas = cursor.fetchone()
    
    # Obtener secciones para el selector
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, nombre, color, 
                   (SELECT COUNT(*) FROM productos_percha WHERE seccion_id = s.id AND activo = 1) as perchas
            FROM productos_seccion s 
            WHERE activo = 1 
            ORDER BY orden, nombre
        """)
        secciones = cursor.fetchall()
    
    context = {
        'productos_sin_ubicacion': productos_sin_ubicacion,
        'estadisticas': {
            'total_productos': estadisticas[0] if estadisticas else 0,
            'productos_ubicados': estadisticas[1] if estadisticas else 0,
            'productos_sin_ubicar': (estadisticas[0] - estadisticas[1]) if estadisticas else 0,
            'total_secciones': estadisticas[2] if estadisticas else 0,
            'total_perchas': estadisticas[3] if estadisticas else 0,
        },
        'secciones': secciones,
        'titulo': 'Ubicaciones de Productos'
    }
    return render(request, 'productos/ubicaciones/index.html', context)


@login_required
def gestionar_secciones(request):
    """Gestión de secciones del establecimiento"""
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        color = request.POST.get('color', '#007bff')
        orden = int(request.POST.get('orden', 0))
        
        if nombre:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO productos_seccion (nombre, descripcion, color, activo, orden)
                        VALUES (%s, %s, %s, 1, %s)
                    """, [nombre, descripcion, color, orden])
                
                return JsonResponse({'success': True, 'message': f'Sección "{nombre}" creada exitosamente'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
    
    # Obtener estadísticas generales
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM productos_seccion WHERE activo = 1")
        total_secciones = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM productos_percha WHERE activo = 1")
        total_perchas = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM productos_ubicacionproducto WHERE activo = 1")
        productos_ubicados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1 AND anulado = 0")
        total_productos = cursor.fetchone()[0]
        productos_sin_ubicar = total_productos - productos_ubicados
        
        print(f"=== ESTADÍSTICAS DEBUG ===")
        print(f"Total secciones: {total_secciones}")
        print(f"Total perchas: {total_perchas}")
        print(f"Productos ubicados: {productos_ubicados}")
        print(f"Total productos: {total_productos}")
        
        # Obtener secciones existentes
        cursor.execute("""
            SELECT s.id, s.nombre, s.descripcion, s.color, s.orden,
                   COUNT(DISTINCT p.id) as total_perchas,
                   COUNT(DISTINCT u.id) as productos_ubicados
            FROM productos_seccion s
            LEFT JOIN productos_percha p ON s.id = p.seccion_id AND p.activo = 1
            LEFT JOIN productos_ubicacionproducto u ON p.id = u.percha_id AND u.activo = 1
            WHERE s.activo = 1
            GROUP BY s.id, s.nombre, s.descripcion, s.color, s.orden
            ORDER BY s.orden, s.nombre
        """)
        
        secciones_raw = cursor.fetchall()
        print(f"Secciones encontradas: {len(secciones_raw)}")
        
        secciones = []
        for seccion in secciones_raw:
            print(f"Sección: {seccion[1]} - Perchas: {seccion[5]} - Productos: {seccion[6]}")
            secciones.append({
                'id': seccion[0],
                'nombre': seccion[1],
                'descripcion': seccion[2],
                'color': seccion[3],
                'orden': seccion[4],
                'total_perchas': seccion[5],
                'productos_ubicados': seccion[6]
            })
    
    context = {
        'secciones': secciones,
        'total_secciones': total_secciones,
        'total_perchas': total_perchas,
        'productos_ubicados': productos_ubicados,
        'productos_sin_ubicar': productos_sin_ubicar,
        'titulo': 'Gestionar Secciones'
    }
    return render(request, 'productos/ubicaciones/secciones.html', context)


@login_required
def gestionar_perchas(request, seccion_id):
    """Gestión de perchas dentro de una sección"""
    
    # Verificar que la sección existe
    with connection.cursor() as cursor:
        cursor.execute("SELECT nombre, color FROM productos_seccion WHERE id = %s AND activo = 1", [seccion_id])
        seccion = cursor.fetchone()
        
        if not seccion:
            messages.error(request, 'Sección no encontrada')
            return redirect('productos:gestionar_secciones')
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        filas = int(request.POST.get('filas', 5))
        columnas = int(request.POST.get('columnas', 10))
        
        if nombre:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO productos_percha (seccion_id, nombre, descripcion, filas, columnas, activo)
                    VALUES (%s, %s, %s, %s, %s, 1)
                """, [seccion_id, nombre, descripcion, filas, columnas])
            
            messages.success(request, f'Percha "{nombre}" creada exitosamente')
            return redirect('productos:gestionar_perchas', seccion_id=seccion_id)
    
    # Obtener perchas de la sección
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.nombre, p.descripcion, p.filas, p.columnas,
                   COUNT(u.id) as productos_ubicados,
                   (p.filas * p.columnas) as capacidad_total
            FROM productos_percha p
            LEFT JOIN productos_ubicacionproducto u ON p.id = u.percha_id AND u.activo = 1
            WHERE p.seccion_id = %s AND p.activo = 1
            GROUP BY p.id, p.nombre, p.descripcion, p.filas, p.columnas
            ORDER BY p.nombre
        """, [seccion_id])
        perchas = cursor.fetchall()
        
        print(f"=== PERCHAS SECCIÓN {seccion_id} ===")
        for i, percha in enumerate(perchas):
            print(f"Percha {i}: ID={percha[0]}, Nombre={percha[1]}")

    context = {
        'seccion': {'id': seccion_id, 'nombre': seccion[0], 'color': seccion[1]},
        'perchas': perchas,
        'titulo': f'Perchas - {seccion[0]}'
    }
    return render(request, 'productos/ubicaciones/perchas.html', context)


@login_required
def mapa_percha(request, percha_id):
    """Mapa visual de una percha específica"""
    
    # Obtener información de la percha
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.nombre, p.descripcion, p.filas, p.columnas,
                   s.id as seccion_id, s.nombre as seccion_nombre, s.color as seccion_color
            FROM productos_percha p
            JOIN productos_seccion s ON p.seccion_id = s.id
            WHERE p.id = %s AND p.activo = 1
        """, [percha_id])
        percha = cursor.fetchone()
        
        if not percha:
            messages.error(request, 'Percha no encontrada')
            return redirect('productos:ubicaciones_productos')
    
    # Obtener productos ubicados en esta percha
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT u.fila, u.columna, u.producto_id, 
                   pr.codigoPrincipal, pr.nombre as producto_nombre, pr.stock
            FROM productos_ubicacionproducto u
            JOIN productos pr ON u.producto_id = pr.id
            WHERE u.percha_id = %s AND u.activo = 1
            ORDER BY u.fila, u.columna
        """, [percha_id])
        ubicaciones = cursor.fetchall()
    
    # Crear matriz de la percha
    filas, columnas = percha[2], percha[3]
    mapa_percha = []
    
    for fila in range(1, filas + 1):
        fila_data = []
        for columna in range(1, columnas + 1):
            # Buscar si hay producto en esta posición
            producto_en_posicion = None
            for ubicacion in ubicaciones:
                if ubicacion[0] == fila and ubicacion[1] == columna:
                    producto_en_posicion = {
                        'producto_id': ubicacion[2],
                        'codigo': ubicacion[3],
                        'nombre': ubicacion[4],
                        'stock': ubicacion[5]
                    }
                    break
            
            fila_data.append({
                'fila': fila,
                'columna': columna,
                'producto': producto_en_posicion,
                'ocupado': producto_en_posicion is not None
            })
        mapa_percha.append(fila_data)
    
    context = {
        'percha': {
            'id': percha_id,
            'nombre': percha[0],
            'descripcion': percha[1],
            'filas': percha[2],
            'columnas': percha[3],
            'seccion': {
                'id': percha[4],
                'nombre': percha[5],
                'color': percha[6]
            }
        },
        'mapa_percha': mapa_percha,
        'range_filas': range(1, percha[2] + 1),
        'range_columnas': range(1, percha[3] + 1),
        'productos_ubicados': len([pos for fila in mapa_percha for pos in fila if pos['ocupado']]),
        'posiciones_libres': (percha[2] * percha[3]) - len([pos for fila in mapa_percha for pos in fila if pos['ocupado']]),
        'titulo': f'Mapa - {percha[0]}'
    }
    return render(request, 'productos/ubicaciones/mapa_percha.html', context)


@login_required
def buscar_productos_ajax(request):
    """Búsqueda AJAX de productos para ubicar"""
    termino = request.GET.get('termino', '').strip()
    
    if len(termino) < 2:
        return JsonResponse({'productos': []})
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.codigoPrincipal, p.nombre, p.stock,
                   u.id as ubicacion_id,
                   CASE WHEN u.id IS NOT NULL 
                        THEN CONCAT(s.nombre, ' > ', pr.nombre, ' > F', u.fila, 'C', u.columna)
                        ELSE NULL 
                   END as ubicacion_actual
            FROM productos p
            LEFT JOIN productos_ubicacionproducto u ON p.id = u.producto_id AND u.activo = 1
            LEFT JOIN productos_percha pr ON u.percha_id = pr.id AND pr.activo = 1
            LEFT JOIN productos_seccion s ON pr.seccion_id = s.id AND s.activo = 1
            WHERE p.activo = 1 AND p.anulado = 0
              AND (p.codigoPrincipal LIKE %s OR p.nombre LIKE %s)
            ORDER BY p.nombre
            LIMIT 20
        """, [f'%{termino}%', f'%{termino}%'])
        
        productos = []
        for row in cursor.fetchall():
            productos.append({
                'id': row[0],
                'codigo': row[1],
                'nombre': row[2],
                'stock': float(row[3]),
                'tiene_ubicacion': row[4] is not None,
                'ubicacion_actual': row[5]
            })
    
    return JsonResponse({'productos': productos})


@login_required
@require_http_methods(["POST"])
def ubicar_producto(request):
    """Ubicar un producto en una posición específica de una percha"""
    try:
        # Obtener datos del formulario POST
        producto_id = request.POST.get('producto_id')
        percha_id = request.POST.get('percha_id')
        fila = request.POST.get('fila')
        columna = request.POST.get('columna')
        observaciones = request.POST.get('observaciones', '')
        
        print(f"=== UBICAR PRODUCTO ===")
        print(f"Producto ID: {producto_id}")
        print(f"Percha ID: {percha_id}")
        print(f"Fila: {fila}, Columna: {columna}")
        
        # Validaciones
        if not all([producto_id, percha_id, fila, columna]):
            return JsonResponse({'success': False, 'error': 'Datos incompletos'})
        
        # Convertir a enteros
        try:
            producto_id = int(producto_id)
            percha_id = int(percha_id)
            fila = int(fila)
            columna = int(columna)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Datos numéricos inválidos'})
        
        with connection.cursor() as cursor:
            # Verificar que el producto existe
            cursor.execute("SELECT id, codigoPrincipal, nombre FROM productos WHERE id = %s AND activo = 1", [producto_id])
            producto = cursor.fetchone()
            if not producto:
                return JsonResponse({'success': False, 'error': 'Producto no encontrado'})
            
            # Verificar que la percha existe
            cursor.execute("SELECT id, nombre FROM productos_percha WHERE id = %s AND activo = 1", [percha_id])
            percha = cursor.fetchone()
            if not percha:
                return JsonResponse({'success': False, 'error': 'Percha no encontrada'})
            
            # Verificar que la posición esté dentro del rango de la percha
            cursor.execute("SELECT filas, columnas FROM productos_percha WHERE id = %s", [percha_id])
            dimensiones = cursor.fetchone()
            if fila < 1 or fila > dimensiones[0] or columna < 1 or columna > dimensiones[1]:
                return JsonResponse({'success': False, 'error': 'Posición fuera del rango de la percha'})
            
            # Verificar que la posición esté libre
            cursor.execute("""
                SELECT COUNT(*) FROM productos_ubicacionproducto 
                WHERE percha_id = %s AND fila = %s AND columna = %s AND activo = 1
            """, [percha_id, fila, columna])
            
            if cursor.fetchone()[0] > 0:
                return JsonResponse({'success': False, 'error': 'Esta posición ya está ocupada'})
            
            # Verificar que el producto no tenga otra ubicación activa
            cursor.execute("""
                SELECT id FROM productos_ubicacionproducto 
                WHERE producto_id = %s AND activo = 1
            """, [producto_id])
            
            ubicacion_existente = cursor.fetchone()
            if ubicacion_existente:
                # Desactivar ubicación anterior
                cursor.execute("""
                    UPDATE productos_ubicacionproducto 
                    SET activo = 0 
                    WHERE id = %s
                """, [ubicacion_existente[0]])
                print(f"Ubicación anterior desactivada: {ubicacion_existente[0]}")
            
            # Crear nueva ubicación
            cursor.execute("""
                INSERT INTO productos_ubicacionproducto 
                (producto_id, percha_id, fila, columna, observaciones, fecha_ubicacion, activo)
                VALUES (%s, %s, %s, %s, %s, NOW(), 1)
            """, [producto_id, percha_id, fila, columna, observaciones])
            
            print(f"✅ Producto {producto[1]} ubicado en F{fila}C{columna}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Producto {producto[1]} ubicado exitosamente en F{fila}C{columna}'
        })
        
    except Exception as e:
        print(f"❌ Error en ubicar_producto: {e}")
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def quitar_ubicacion(request):
    """Quitar un producto de su ubicación actual"""
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE productos_ubicacionproducto 
                SET activo = 0 
                WHERE producto_id = %s AND activo = 1
            """, [producto_id])
        
        return JsonResponse({'success': True, 'message': 'Ubicación removida exitosamente'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})


@login_required
def obtener_ubicacion_producto(request, producto_id):
    """Obtener la ubicación actual de un producto"""
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT s.nombre as seccion, s.color, pr.nombre as percha, 
                   u.fila, u.columna, u.observaciones,
                   CONCAT(pr.nombre, '-F', u.fila, 'C', u.columna) as codigo_ubicacion
            FROM productos_ubicacionproducto u
            JOIN productos_percha pr ON u.percha_id = pr.id
            JOIN productos_seccion s ON pr.seccion_id = s.id
            WHERE u.producto_id = %s AND u.activo = 1
        """, [producto_id])
        
        ubicacion = cursor.fetchone()
        
        if ubicacion:
            return JsonResponse({
                'tiene_ubicacion': True,
                'seccion': ubicacion[0],
                'color_seccion': ubicacion[1],
                'percha': ubicacion[2],
                'fila': ubicacion[3],
                'columna': ubicacion[4],
                'observaciones': ubicacion[5],
                'codigo_ubicacion': ubicacion[6],
                'ubicacion_completa': f"{ubicacion[0]} > {ubicacion[2]} > Fila {ubicacion[3]}, Columna {ubicacion[4]}"
            })
        else:
            return JsonResponse({'tiene_ubicacion': False})


@login_required
def obtener_perchas_seccion(request, seccion_id):
    """Obtener perchas de una sección en formato JSON"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.nombre, p.descripcion, p.filas, p.columnas
                FROM productos_percha p
                WHERE p.seccion_id = %s AND p.activo = 1
                ORDER BY p.nombre
            """, [seccion_id])
            perchas = cursor.fetchall()
            
            perchas_data = []
            for percha in perchas:
                perchas_data.append({
                    'id': percha[0],
                    'nombre': percha[1],
                    'descripcion': percha[2],
                    'filas': percha[3],
                    'columnas': percha[4]
                })
            
            return JsonResponse({
                'success': True,
                'perchas': perchas_data
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def obtener_secciones_json(request):
    """Obtener todas las secciones en formato JSON"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.nombre, s.descripcion, s.color
                FROM productos_seccion s
                WHERE s.activo = 1
                ORDER BY s.orden, s.nombre
            """)
            secciones = cursor.fetchall()
            
            secciones_data = []
            for seccion in secciones:
                secciones_data.append({
                    'id': seccion[0],
                    'nombre': seccion[1],
                    'descripcion': seccion[2],
                    'color': seccion[3]
                })
            
            return JsonResponse({
                'success': True,
                'secciones': secciones_data
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["GET"])
def obtener_seccion(request, seccion_id):
    """Obtener datos de una sección específica para edición"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, descripcion, color, orden
                FROM productos_seccion 
                WHERE id = %s AND activo = 1
            """, [seccion_id])
            
            seccion_data = cursor.fetchone()
            if not seccion_data:
                return JsonResponse({
                    'success': False,
                    'error': 'Sección no encontrada'
                })
            
            seccion = {
                'id': seccion_data[0],
                'nombre': seccion_data[1],
                'descripcion': seccion_data[2],
                'color': seccion_data[3],
                'orden': seccion_data[4]
            }
            
            return JsonResponse({
                'success': True,
                'seccion': seccion
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def editar_seccion(request, seccion_id):
    """Editar una sección existente"""
    try:
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        color = request.POST.get('color', '#007bff')
        orden = int(request.POST.get('orden', 0))
        
        if not nombre:
            return JsonResponse({
                'success': False,
                'error': 'El nombre es obligatorio'
            })
        
        with connection.cursor() as cursor:
            # Verificar que la sección existe
            cursor.execute("""
                SELECT id FROM productos_seccion 
                WHERE id = %s AND activo = 1
            """, [seccion_id])
            
            if not cursor.fetchone():
                return JsonResponse({
                    'success': False,
                    'error': 'Sección no encontrada'
                })
            
            # Actualizar la sección
            cursor.execute("""
                UPDATE productos_seccion 
                SET nombre = %s, descripcion = %s, color = %s, orden = %s
                WHERE id = %s AND activo = 1
            """, [nombre, descripcion, color, orden, seccion_id])
            
            return JsonResponse({
                'success': True,
                'message': f'Sección "{nombre}" actualizada exitosamente'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def eliminar_seccion(request, seccion_id):
    """Eliminar una sección (soft delete)"""
    try:
        with connection.cursor() as cursor:
            # Verificar que la sección existe
            cursor.execute("""
                SELECT nombre FROM productos_seccion 
                WHERE id = %s AND activo = 1
            """, [seccion_id])
            
            seccion_data = cursor.fetchone()
            if not seccion_data:
                return JsonResponse({
                    'success': False,
                    'error': 'Sección no encontrada'
                })
            
            # Verificar si tiene perchas asociadas
            cursor.execute("""
                SELECT COUNT(*) FROM productos_percha 
                WHERE seccion_id = %s AND activo = 1
            """, [seccion_id])
            
            total_perchas = cursor.fetchone()[0]
            if total_perchas > 0:
                return JsonResponse({
                    'success': False,
                    'error': f'No se puede eliminar la sección porque tiene {total_perchas} perchas asociadas'
                })
            
            # Eliminar la sección (soft delete)
            cursor.execute("""
                UPDATE productos_seccion 
                SET activo = 0 
                WHERE id = %s
            """, [seccion_id])
            
            return JsonResponse({
                'success': True,
                'message': f'Sección "{seccion_data[0]}" eliminada exitosamente'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })