import csv
import json
from datetime import datetime
from io import StringIO, BytesIO

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone

# Importaciones para PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# Importar modelos de otras apps de forma segura
try:
    from productos.models import Producto
except ImportError:
    Producto = None

try:
    from clientes.models import Cliente
except ImportError:
    Cliente = None

try:
    from proveedores.models import Proveedor
except ImportError:
    Proveedor = None

try:
    from ventas.models import Venta, DetalleVenta
except ImportError:
    Venta = None
    DetalleVenta = None

try:
    from inventario.models import MovimientoInventario
except ImportError:
    MovimientoInventario = None


@login_required
def dashboard_reportes(request):
    """Dashboard principal de reportes"""
    total_productos = 0
    total_clientes = 0
    total_proveedores = 0
    
    try:
        if Producto:
            # Para productos, usar filtro genérico
            total_productos = Producto.objects.all().count()
    except Exception:
        total_productos = 0
        
    try:
        if Cliente:
            # Para clientes, puede usar estado diferente de anulado o todos
            total_clientes = Cliente.objects.exclude(anulado=True).count()
    except Exception:
        try:
            if Cliente:
                total_clientes = Cliente.objects.all().count()
        except Exception:
            total_clientes = 0
    
    try:
        if Proveedor:
            # Para proveedores, usar filtro genérico
            total_proveedores = Proveedor.objects.exclude(anulado=True).count()
    except Exception:
        try:
            if Proveedor:
                total_proveedores = Proveedor.objects.all().count()
        except Exception:
            total_proveedores = 0
    
    context = {
        'titulo': 'Reportes del Sistema',
        'total_productos': total_productos,
        'total_clientes': total_clientes,
        'total_proveedores': total_proveedores,
    }
    return render(request, 'reportes/dashboard.html', context)


@login_required
def exportar_productos(request):
    """Exportar lista completa de productos"""
    if not Producto:
        return JsonResponse({'error': 'Modelo Producto no disponible'}, status=400)
        
    formato = request.GET.get('formato', 'csv')
    
    # Obtener productos (usar filtro genérico)
    try:
        productos = Producto.objects.all().order_by('nombre')
    except Exception as e:
        return JsonResponse({'error': f'Error al obtener productos: {str(e)}'}, status=500)
    
    if formato == 'csv':
        return exportar_productos_csv(productos)
    elif formato == 'pdf':
        return exportar_productos_pdf(productos)
    elif formato == 'txt':
        return exportar_productos_txt(productos)
    else:
        return JsonResponse({'error': 'Formato no soportado'}, status=400)


def exportar_productos_csv(productos):
    """Exportar productos a CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="productos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Agregar BOM para Excel
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Encabezados
    writer.writerow([
        'ID',
        'Código Principal',
        'Código Auxiliar',
        'Nombre',
        'Descripción',
        'Laboratorio',
        'Marca',
        'Categoría',
        'Costo Unidad',
        'Precio Venta',
        'Stock',
        'Stock Mínimo',
        'Stock Máximo',
        'Activo',
        'Requiere Frío',
        'Psicotrópico'
    ])
    
    # Datos
    for producto in productos:
        writer.writerow([
            getattr(producto, 'id', ''),
            getattr(producto, 'codigo_principal', ''),
            getattr(producto, 'codigo_auxiliar', ''),
            getattr(producto, 'nombre', ''),
            getattr(producto, 'descripcion', ''),
            getattr(producto, 'id_laboratorio', ''),
            getattr(producto, 'id_marca', ''),
            getattr(producto, 'id_categoria', ''),
            f"{getattr(producto, 'costo_unidad', 0):.2f}",
            f"{getattr(producto, 'precio_venta', 0):.2f}",
            getattr(producto, 'stock', 0),
            getattr(producto, 'stock_minimo', 0),
            getattr(producto, 'stock_maximo', 0),
            'Sí' if getattr(producto, 'activo', False) else 'No',
            'Sí' if getattr(producto, 'requiere_cadena_frio', False) else 'No',
            'Sí' if getattr(producto, 'es_psicotropico', False) else 'No'
        ])
    
    return response


def exportar_productos_pdf(productos):
    """Exportar productos a PDF"""
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Obtener estilos
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']
    
    # Título
    title = Paragraph(f"REPORTE DE PRODUCTOS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Preparar datos para la tabla
    data = [['Código Principal', 'Nombre', 'Precio', 'Stock', 'Categoría']]
    
    for producto in productos:
        codigo = getattr(producto, 'codigo_principal', '')[:15]  # Truncar para ajustar
        nombre = getattr(producto, 'nombre', '')[:30]  # Truncar para ajustar
        precio = f"${getattr(producto, 'precio_venta', 0):.2f}"
        stock = str(getattr(producto, 'stock', 0))
        categoria = ''
        if hasattr(producto, 'id_categoria') and producto.id_categoria:
            categoria = getattr(producto.id_categoria, 'nombre', '')[:20]
        
        data.append([codigo, nombre, precio, stock, categoria])
    
    # Crear la tabla
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Construir el PDF
    doc.build(elements)
    
    # Preparar la respuesta
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="productos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response


def exportar_productos_txt(productos):
    """Exportar productos a TXT"""
    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="productos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"'
    
    # Agregar BOM para caracteres especiales
    response.write('\ufeff')
    
    response.write(f"REPORTE DE PRODUCTOS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    response.write("=" * 80 + "\n\n")
    
    for producto in productos:
        response.write(f"Código Principal: {getattr(producto, 'codigo_principal', '')}\n")
        if getattr(producto, 'codigo_auxiliar', ''):
            response.write(f"Código Auxiliar: {producto.codigo_auxiliar}\n")
        response.write(f"Nombre: {getattr(producto, 'nombre', '')}\n")
        if getattr(producto, 'descripcion', ''):
            response.write(f"Descripción: {producto.descripcion}\n")
        if hasattr(producto, 'id_categoria') and producto.id_categoria:
            response.write(f"Categoría: {producto.id_categoria.nombre}\n")
        if hasattr(producto, 'id_laboratorio') and producto.id_laboratorio:
            response.write(f"Laboratorio: {producto.id_laboratorio.nombre}\n")
        if hasattr(producto, 'id_marca') and producto.id_marca:
            response.write(f"Marca: {producto.id_marca.nombre}\n")
        costo = getattr(producto, 'costo_unidad', 0)
        precio = getattr(producto, 'precio_venta', 0)
        response.write(f"Costo Unidad: ${costo:.2f}\n")
        response.write(f"Precio Venta: ${precio:.2f}\n")
        response.write(f"Stock: {getattr(producto, 'stock', 0)}\n")
        response.write(f"Estado: {'Activo' if getattr(producto, 'activo', True) and not getattr(producto, 'anulado', False) else 'Inactivo'}\n")
        response.write("-" * 40 + "\n\n")
    
    return response


@login_required
def exportar_clientes(request):
    """Exportar lista completa de clientes"""
    if not Cliente:
        return JsonResponse({'error': 'Modelo Cliente no disponible'}, status=400)
        
    formato = request.GET.get('formato', 'csv')
    
    # Obtener clientes (usar filtro genérico)
    try:
        clientes = Cliente.objects.exclude(anulado=True).order_by('nombres')
    except Exception:
        try:
            clientes = Cliente.objects.all().order_by('nombres')
        except Exception as e:
            return JsonResponse({'error': f'Error al obtener clientes: {str(e)}'}, status=500)
    
    if formato == 'csv':
        return exportar_clientes_csv(clientes)
    elif formato == 'pdf':
        return exportar_clientes_pdf(clientes)
    elif formato == 'txt':
        return exportar_clientes_txt(clientes)
    else:
        return JsonResponse({'error': 'Formato no soportado'}, status=400)


def exportar_clientes_csv(clientes):
    """Exportar clientes a CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Agregar BOM para Excel
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Encabezados
    writer.writerow([
        'ID',
        'Nombres',
        'Apellidos',
        'Cédula/RUC',
        'Teléfono',
        'Celular',
        'Email',
        'Dirección',
        'Tipo Cliente',
        'Estado',
        'Fecha Registro'
    ])
    
    # Datos
    for cliente in clientes:
        writer.writerow([
            getattr(cliente, 'id', ''),
            getattr(cliente, 'nombres', ''),
            getattr(cliente, 'apellidos', ''),
            getattr(cliente, 'cedula_ruc', ''),
            getattr(cliente, 'telefono', ''),
            getattr(cliente, 'celular', ''),
            getattr(cliente, 'email', ''),
            getattr(cliente, 'direccion', ''),
            getattr(cliente, 'tipo_cliente', ''),
            'Activo' if not getattr(cliente, 'anulado', False) else 'Anulado',
            getattr(cliente, 'creado_date', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response


def exportar_clientes_pdf(clientes):
    """Exportar clientes a PDF"""
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Obtener estilos
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    
    # Título
    title = Paragraph(f"REPORTE DE CLIENTES - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Preparar datos para la tabla
    data = [['Nombres', 'Apellidos', 'Cédula/RUC', 'Teléfono', 'Email']]
    
    for cliente in clientes:
        nombres = getattr(cliente, 'nombres', '')[:20]  # Truncar para ajustar
        apellidos = getattr(cliente, 'apellidos', '')[:20]
        cedula = getattr(cliente, 'cedula_ruc', '')[:15]
        telefono = getattr(cliente, 'telefono', '')[:12]
        email = getattr(cliente, 'email', '')[:25]
        
        data.append([nombres, apellidos, cedula, telefono, email])
    
    # Crear la tabla
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Construir el PDF
    doc.build(elements)
    
    # Preparar la respuesta
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response


def exportar_clientes_txt(clientes):
    """Exportar clientes a TXT"""
    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"'
    
    # Agregar BOM para caracteres especiales
    response.write('\ufeff')
    
    response.write(f"REPORTE DE CLIENTES - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    response.write("=" * 80 + "\n\n")
    
    for cliente in clientes:
        response.write(f"Nombre: {cliente.nombre}\n")
        if hasattr(cliente, 'codigo') and cliente.codigo:
            response.write(f"Código: {cliente.codigo}\n")
        if hasattr(cliente, 'rtn') and cliente.rtn:
            response.write(f"RTN: {cliente.rtn}\n")
        elif hasattr(cliente, 'identidad') and cliente.identidad:
            response.write(f"Identidad: {cliente.identidad}\n")
        if hasattr(cliente, 'telefono') and cliente.telefono:
            response.write(f"Teléfono: {cliente.telefono}\n")
        if hasattr(cliente, 'email') and cliente.email:
            response.write(f"Email: {cliente.email}\n")
        if hasattr(cliente, 'direccion') and cliente.direccion:
            response.write(f"Dirección: {cliente.direccion}\n")
        response.write(f"Estado: {'Activo' if cliente.activo else 'Inactivo'}\n")
        response.write("-" * 40 + "\n\n")
    
    return response


@login_required
def exportar_proveedores(request):
    """Exportar lista completa de proveedores"""
    if not Proveedor:
        return JsonResponse({'error': 'Modelo Proveedor no disponible'}, status=400)
        
    formato = request.GET.get('formato', 'csv')
    
    # Obtener proveedores (usar filtro genérico)
    try:
        proveedores = Proveedor.objects.exclude(anulado=True).order_by('razon_social')
    except Exception:
        try:
            proveedores = Proveedor.objects.all().order_by('razon_social')
        except Exception as e:
            return JsonResponse({'error': f'Error al obtener proveedores: {str(e)}'}, status=500)
    
    if formato == 'csv':
        return exportar_proveedores_csv(proveedores)
    elif formato == 'pdf':
        return exportar_proveedores_pdf(proveedores)
    elif formato == 'txt':
        return exportar_proveedores_txt(proveedores)
    else:
        return JsonResponse({'error': 'Formato no soportado'}, status=400)


def exportar_proveedores_csv(proveedores):
    """Exportar proveedores a CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="proveedores_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Agregar BOM para Excel
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Encabezados
    writer.writerow([
        'ID',
        'RUC',
        'Razón Social',
        'Nombre Comercial',
        'Teléfono',
        'Email',
        'Dirección',
        'Estado',
        'Fecha Registro'
    ])
    
    # Datos
    for proveedor in proveedores:
        writer.writerow([
            getattr(proveedor, 'id', ''),
            getattr(proveedor, 'ruc', ''),
            getattr(proveedor, 'razon_social', ''),
            getattr(proveedor, 'nombre_comercial', ''),
            getattr(proveedor, 'telefono', ''),
            getattr(proveedor, 'email', ''),
            getattr(proveedor, 'direccion', ''),
            'Activo' if not getattr(proveedor, 'anulado', False) else 'Anulado',
            getattr(proveedor, 'creado_date', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response


def exportar_proveedores_pdf(proveedores):
    """Exportar proveedores a PDF"""
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Obtener estilos
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    
    # Título
    title = Paragraph(f"REPORTE DE PROVEEDORES - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Preparar datos para la tabla
    data = [['RUC', 'Razón Social', 'Nombre Comercial', 'Teléfono', 'Email']]
    
    for proveedor in proveedores:
        ruc = getattr(proveedor, 'ruc', '')[:13]
        razon_social = getattr(proveedor, 'razon_social', '')[:25]
        nombre_comercial = getattr(proveedor, 'nombre_comercial', '')[:20]
        telefono = getattr(proveedor, 'telefono', '')[:12]
        email = getattr(proveedor, 'email', '')[:25]
        
        data.append([ruc, razon_social, nombre_comercial, telefono, email])
    
    # Crear la tabla
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Construir el PDF
    doc.build(elements)
    
    # Preparar la respuesta
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="proveedores_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response


def exportar_proveedores_txt(proveedores):
    """Exportar proveedores a TXT"""
    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="proveedores_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"'
    
    # Agregar BOM para caracteres especiales
    response.write('\ufeff')
    
    response.write(f"REPORTE DE PROVEEDORES - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    response.write("=" * 80 + "\n\n")
    
    for proveedor in proveedores:
        response.write(f"RUC: {getattr(proveedor, 'ruc', '')}\n")
        response.write(f"Razón Social: {getattr(proveedor, 'razon_social', '')}\n")
        if getattr(proveedor, 'nombre_comercial', ''):
            response.write(f"Nombre Comercial: {proveedor.nombre_comercial}\n")
        if getattr(proveedor, 'telefono', ''):
            response.write(f"Teléfono: {proveedor.telefono}\n")
        if getattr(proveedor, 'email', ''):
            response.write(f"Email: {proveedor.email}\n")
        if getattr(proveedor, 'direccion', ''):
            response.write(f"Dirección: {proveedor.direccion}\n")
        estado_activo = getattr(proveedor, 'estado', True) and not getattr(proveedor, 'anulado', False)
        response.write(f"Estado: {'Activo' if estado_activo else 'Inactivo'}\n")
        response.write("-" * 40 + "\n\n")
    
    return response


@login_required
def reporte_estadisticas(request):
    """Reporte con estadísticas generales del sistema"""
    try:
        # Estadísticas básicas
        total_productos = 0
        total_clientes = 0
        total_proveedores = 0
        productos_stock_bajo = 0
        
        if Producto:
            total_productos = Producto.objects.filter(activo=True).count()
            
        if Cliente:
            total_clientes = Cliente.objects.filter(activo=True).count()
            
        if Proveedor:
            total_proveedores = Proveedor.objects.filter(activo=True).count()
        
        # Productos con stock bajo
        if Producto:
            try:
                from django.db.models import F
                productos_stock_bajo = Producto.objects.filter(
                    activo=True,
                    stock_actual__lte=F('stock_minimo')
                ).count()
            except Exception:
                # Si no existe el campo, devolver 0
                productos_stock_bajo = 0
        
        context = {
            'titulo': 'Estadísticas del Sistema',
            'total_productos': total_productos,
            'total_clientes': total_clientes,
            'total_proveedores': total_proveedores,
            'productos_stock_bajo': productos_stock_bajo,
            'fecha_reporte': datetime.now()
        }
        
        return render(request, 'reportes/estadisticas.html', context)
        
    except Exception as e:
        return render(request, 'reportes/error.html', {
            'error': f'Error al generar estadísticas: {str(e)}'
        })