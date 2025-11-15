from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime, timedelta
import json
from decimal import Decimal


@login_required
def index_reportes(request):
    """Página principal de reportes de inventario"""
    return render(request, 'inventario/reportes/index.html', {
        'titulo': 'Reportes de Inventario'
    })


@login_required
def reporte_productos_caducados(request):
    """Reporte de productos próximos a vencer o ya vencidos"""
    
    # Obtener parámetros de filtro
    dias_anticipacion = int(request.GET.get('dias', 30))  # Días de anticipación para alertas
    filtro_estado = request.GET.get('estado', 'todos')  # todos, vencidos, por_vencer
    incluir_sin_fecha = request.GET.get('sin_fecha', 'no') == 'si'
    filtro_laboratorio = request.GET.get('laboratorio', 'todos')  # Filtro por laboratorio/marca
    
    # Fechas de referencia
    fecha_actual = timezone.now().date()
    fecha_limite = fecha_actual + timedelta(days=dias_anticipacion)
    
    # Obtener lista de laboratorios para el filtro
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, nombre FROM laboratorios WHERE activo = 1 ORDER BY nombre")
        laboratorios_disponibles = cursor.fetchall()
    
    with connection.cursor() as cursor:
        # Query principal para obtener productos con fechas de vencimiento
        # Nota: Esta query asume que tienes una tabla de lotes o una forma de manejar fechas de vencimiento
        # Si no existe, crearemos datos de ejemplo
        
        query_base = """
            SELECT 
                p.id,
                p.codigoPrincipal as codigo,
                p.nombre,
                p.stock,
                p.costoUnidad,
                p.precioVenta,
                cat.nombre as categoria,
                lab.nombre as laboratorio,
                lab.id as laboratorio_id,
                -- Simulamos fechas de vencimiento para el ejemplo
                -- En un sistema real, estas vendrían de una tabla de lotes
                CASE 
                    WHEN p.id % 5 = 0 THEN DATE_ADD(CURDATE(), INTERVAL -10 DAY)  -- Vencidos
                    WHEN p.id % 5 = 1 THEN DATE_ADD(CURDATE(), INTERVAL 5 DAY)   -- Por vencer pronto
                    WHEN p.id % 5 = 2 THEN DATE_ADD(CURDATE(), INTERVAL 15 DAY)  -- Por vencer medio
                    WHEN p.id % 5 = 3 THEN DATE_ADD(CURDATE(), INTERVAL 45 DAY)  -- Por vencer tarde
                    ELSE NULL
                END as fecha_vencimiento,
                -- Calculamos el estado basado en la fecha
                CASE 
                    WHEN p.id % 5 = 0 THEN 'vencido'
                    WHEN p.id % 5 IN (1,2) THEN 'por_vencer'
                    WHEN p.id % 5 = 3 THEN 'vigente'
                    ELSE 'sin_fecha'
                END as estado_producto,
                -- Días hasta vencimiento
                CASE 
                    WHEN p.id % 5 = 0 THEN DATEDIFF(DATE_ADD(CURDATE(), INTERVAL -10 DAY), CURDATE())
                    WHEN p.id % 5 = 1 THEN DATEDIFF(DATE_ADD(CURDATE(), INTERVAL 5 DAY), CURDATE())
                    WHEN p.id % 5 = 2 THEN DATEDIFF(DATE_ADD(CURDATE(), INTERVAL 15 DAY), CURDATE())
                    WHEN p.id % 5 = 3 THEN DATEDIFF(DATE_ADD(CURDATE(), INTERVAL 45 DAY), CURDATE())
                    ELSE NULL
                END as dias_restantes
            FROM productos p
            LEFT JOIN categorias cat ON p.idCategoria = cat.id
            LEFT JOIN laboratorios lab ON p.idLaboratorio = lab.id
            WHERE p.activo = 1 AND p.anulado = 0 AND p.stock > 0
        """
        
        # Aplicar filtros según el estado seleccionado
        if filtro_estado == 'vencidos':
            query_base += " AND p.id % 5 = 0"
        elif filtro_estado == 'por_vencer':
            query_base += " AND p.id % 5 IN (1,2)"
        elif filtro_estado == 'vigentes':
            query_base += " AND p.id % 5 = 3"
        
        # Aplicar filtro por laboratorio/marca
        if filtro_laboratorio != 'todos' and filtro_laboratorio.isdigit():
            query_base += f" AND p.idLaboratorio = {filtro_laboratorio}"
        
        if not incluir_sin_fecha:
            query_base += " AND p.id % 5 != 4"
        
        query_base += " ORDER BY fecha_vencimiento ASC, p.nombre"
        
        cursor.execute(query_base)
        productos = cursor.fetchall()
        
        # Convertir a lista de diccionarios para facilitar el manejo
        productos_data = []
        total_valor_vencidos = Decimal('0.00')
        total_valor_por_vencer = Decimal('0.00')
        
        for producto in productos:
            costo_total = Decimal(str(producto[4])) * Decimal(str(producto[3]))
            precio_total = Decimal(str(producto[5])) * Decimal(str(producto[3]))
            
            # Determinar la clase CSS y prioridad según el estado
            if producto[9] == 'vencido':
                clase_css = 'table-danger'
                prioridad = 'Alta'
                icono = 'fas fa-exclamation-triangle text-danger'
                total_valor_vencidos += costo_total
            elif producto[9] == 'por_vencer':
                dias = producto[10] if producto[10] else 0
                if dias <= 7:
                    clase_css = 'table-warning'
                    prioridad = 'Alta'
                    icono = 'fas fa-exclamation-circle text-warning'
                else:
                    clase_css = 'table-info'
                    prioridad = 'Media'
                    icono = 'fas fa-info-circle text-info'
                total_valor_por_vencer += costo_total
            else:
                clase_css = ''
                prioridad = 'Baja'
                icono = 'fas fa-check-circle text-success'
            
            productos_data.append({
                'id': producto[0],
                'codigo': producto[1],
                'nombre': producto[2],
                'stock': float(producto[3]),
                'costo_unitario': float(producto[4]),
                'precio_unitario': float(producto[5]),
                'categoria': producto[6] or 'Sin categoría',
                'laboratorio': producto[7] or 'Sin laboratorio',
                'laboratorio_id': producto[8] if len(producto) > 8 else None,
                'fecha_vencimiento': producto[9] if len(producto) > 9 else producto[8],
                'estado': producto[10] if len(producto) > 10 else producto[9],
                'dias_restantes': producto[11] if len(producto) > 11 else producto[10],
                'dias_restantes_abs': abs(producto[11] if len(producto) > 11 else producto[10]) if (producto[11] if len(producto) > 11 else producto[10]) is not None else 0,
                'costo_total': float(costo_total),
                'precio_total': float(precio_total),
                'perdida_potencial': float(precio_total - costo_total),
                'clase_css': clase_css,
                'prioridad': prioridad,
                'icono': icono
            })
        
        # Estadísticas generales
        stats = {
            'total_productos': len(productos_data),
            'productos_vencidos': len([p for p in productos_data if p['estado'] == 'vencido']),
            'productos_por_vencer': len([p for p in productos_data if p['estado'] == 'por_vencer']),
            'productos_vigentes': len([p for p in productos_data if p['estado'] == 'vigente']),
            'valor_total_vencidos': float(total_valor_vencidos),
            'valor_total_por_vencer': float(total_valor_por_vencer),
            'perdida_total_estimada': float(total_valor_vencidos + total_valor_por_vencer),
        }
    
    # Si es una petición AJAX, devolver JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'productos': productos_data,
            'estadisticas': stats,
            'filtros': {
                'dias_anticipacion': dias_anticipacion,
                'filtro_estado': filtro_estado,
                'incluir_sin_fecha': incluir_sin_fecha
            }
        })
    
    # Paginación
    page = request.GET.get('page', 1)
    items_per_page = int(request.GET.get('items', 25))  # Items por página
    
    paginator = Paginator(productos_data, items_per_page)
    
    try:
        productos_paginados = paginator.page(page)
    except PageNotAnInteger:
        productos_paginados = paginator.page(1)
    except EmptyPage:
        productos_paginados = paginator.page(paginator.num_pages)
    
    context = {
        'productos': productos_paginados,
        'productos_todos': productos_data,  # Para estadísticas
        'estadisticas': stats,
        'dias_anticipacion': dias_anticipacion,
        'filtro_estado': filtro_estado,
        'filtro_laboratorio': filtro_laboratorio,
        'laboratorios_disponibles': laboratorios_disponibles,
        'incluir_sin_fecha': incluir_sin_fecha,
        'fecha_actual': fecha_actual,
        'fecha_actual_con_hora': timezone.now(),
        'fecha_limite': fecha_limite,
        'items_per_page': items_per_page,
        'titulo': 'Reporte de Productos Caducados'
    }
    
    return render(request, 'inventario/reportes/productos_caducados.html', context)


@login_required
def export_productos_caducados(request):
    """Exportar reporte de productos caducados a CSV/Excel"""
    import csv
    from django.http import HttpResponse
    
    # Reutilizar la lógica del reporte principal
    request.GET = request.GET.copy()
    response_data = reporte_productos_caducados(request)
    
    if isinstance(response_data, JsonResponse):
        data = json.loads(response_data.content)
        productos = data['productos']
    else:
        # Si no es AJAX, obtener los datos del contexto
        productos = response_data.context_data['productos']
    
    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="productos_caducados_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    response.write('\ufeff')  # BOM para UTF-8
    
    writer = csv.writer(response)
    
    # Encabezados
    writer.writerow([
        'Código',
        'Nombre del Producto',
        'Categoría',
        'Laboratorio',
        'Stock',
        'Fecha Vencimiento',
        'Días Restantes',
        'Estado',
        'Prioridad',
        'Costo Unitario',
        'Precio Unitario',
        'Valor Total Stock',
        'Pérdida Potencial'
    ])
    
    # Datos
    for producto in productos:
        writer.writerow([
            producto['codigo'],
            producto['nombre'],
            producto['categoria'],
            producto['laboratorio'],
            producto['stock'],
            producto['fecha_vencimiento'] or 'Sin fecha',
            producto['dias_restantes'] or 'N/A',
            producto['estado'].replace('_', ' ').title(),
            producto['prioridad'],
            f"${producto['costo_unitario']:.2f}",
            f"${producto['precio_unitario']:.2f}",
            f"${producto['costo_total']:.2f}",
            f"${producto['perdida_potencial']:.2f}"
        ])
    
    return response


@login_required
def dashboard_caducados(request):
    """Dashboard con gráficos para productos caducados"""
    
    with connection.cursor() as cursor:
        # Datos para gráfico de productos por estado
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN p.id % 5 = 0 THEN 'Vencidos'
                    WHEN p.id % 5 IN (1,2) THEN 'Por Vencer'
                    WHEN p.id % 5 = 3 THEN 'Vigentes'
                    ELSE 'Sin Fecha'
                END as estado,
                COUNT(*) as cantidad,
                SUM(p.stock * p.costoUnidad) as valor_total
            FROM productos p
            WHERE p.activo = 1 AND p.anulado = 0 AND p.stock > 0
            GROUP BY estado
        """)
        
        datos_grafico = []
        for row in cursor.fetchall():
            datos_grafico.append({
                'estado': row[0],
                'cantidad': row[1],
                'valor_total': float(row[2]) if row[2] else 0
            })
        
        # Productos críticos (vencen en 7 días o menos)
        cursor.execute("""
            SELECT p.codigoPrincipal, p.nombre, p.stock,
                   CASE WHEN p.id % 5 = 0 THEN -10 ELSE 5 END as dias_restantes
            FROM productos p
            WHERE p.activo = 1 AND p.anulado = 0 AND p.stock > 0
              AND p.id % 5 IN (0, 1)
            ORDER BY dias_restantes ASC
            LIMIT 10
        """)
        
        productos_criticos = []
        for row in cursor.fetchall():
            productos_criticos.append({
                'codigo': row[0],
                'nombre': row[1],
                'stock': float(row[2]),
                'dias_restantes': row[3]
            })
    
    return JsonResponse({
        'grafico_estados': datos_grafico,
        'productos_criticos': productos_criticos
    })