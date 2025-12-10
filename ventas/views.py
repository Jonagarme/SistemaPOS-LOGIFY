from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.db import transaction, OperationalError
from django.views.decorators.http import require_http_methods
from functools import wraps
import json
from decimal import Decimal
from datetime import date, datetime
import uuid
import requests
from django.utils import timezone
from .models import Venta, DetalleVenta, PagoVenta, FacturaVenta, FacturaVentaDetalle
# from .models import DevolucionVenta, DetalleDevolucion  # Comentado temporalmente
from productos.models import Producto, Categoria
from clientes.models import Cliente
from django.db import connection
from django.template.loader import render_to_string
from django.conf import settings


def login_required_offline_safe(view_func):
    """
    Decorador personalizado que permite acceso sin autenticación en modo offline
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Si el middleware ya detectó modo offline, continuar directamente
        if getattr(request, 'modo_offline', False):
            # Verificar si hay usuario en sesión
            usuario_offline = request.session.get('usuario_offline')
            if not usuario_offline:
                # No hay sesión offline, redirigir a login
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            # Hay sesión offline, continuar
            return view_func(request, *args, **kwargs)
        
        # Modo online - verificar autenticación normal
        try:
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
        except (OperationalError, Exception) as e:
            # Error inesperado - permitir acceso en modo offline
            print(f"Error de autenticación: {e}")
            pass
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def obtener_configuracion_empresa():
    """Función centralizada para obtener configuración de la empresa"""
    from usuarios.models import ConfiguracionEmpresa
    
    try:
        empresa_config = ConfiguracionEmpresa.obtener_configuracion()
        
        if empresa_config:
            return {
                'ruc': empresa_config.ruc,
                'razon_social': empresa_config.razon_social,
                'nombre_comercial': empresa_config.nombre_comercial or empresa_config.razon_social,
                'direccion_matriz': empresa_config.direccion_matriz,
                'direccion_establecimiento': empresa_config.direccion_matriz,
                'telefono': empresa_config.telefono or '',
                'email': empresa_config.email or '',
                'contribuyente_especial': empresa_config.contribuyente_especial or '',
                'obligado_contabilidad': 'SI' if empresa_config.obligado_contabilidad else 'NO',
                'activo': empresa_config.activo,
                # Campos adicionales que se pueden configurar en el futuro
                'codigo_establecimiento': '001',  # Por defecto
                'codigo_punto_emision': '001',   # Por defecto
                'ambiente': 'PRODUCCIÓN',        # Por defecto
                'emision': 'NORMAL',            # Por defecto
                'eslogan': 'Tu Bienestar, Nuestra Prioridad',  # Configurable en el futuro
                'verificacion_url': 'https://srienlinea.sri.gob.ec/sri-en-linea/consulta/55',
                'telefono_atencion': empresa_config.telefono or '000-0000',
                'mensaje_final': f'{empresa_config.nombre_comercial or empresa_config.razon_social} TE ESPERA'
            }
        else:
            # Si no hay configuración, devolver valores por defecto
            return {
                'ruc': '9999999999999',
                'razon_social': 'EMPRESA NO CONFIGURADA',
                'nombre_comercial': 'EMPRESA NO CONFIGURADA',
                'direccion_matriz': 'DIRECCIÓN NO CONFIGURADA',
                'direccion_establecimiento': 'DIRECCIÓN NO CONFIGURADA',
                'telefono': '000-0000',
                'email': '',
                'contribuyente_especial': '',
                'obligado_contabilidad': 'NO',
                'activo': True,
                'codigo_establecimiento': '001',
                'codigo_punto_emision': '001',
                'ambiente': 'PRODUCCIÓN',
                'emision': 'NORMAL',
                'eslogan': 'Configure su empresa en el sistema',
                'verificacion_url': 'https://srienlinea.sri.gob.ec/sri-en-linea/consulta/55',
                'telefono_atencion': '000-0000',
                'mensaje_final': 'CONFIGURE SU EMPRESA'
            }
            
    except Exception as e:
        print(f"ERROR al obtener configuración de empresa: {str(e)}")
        # Fallback a configuración por defecto en caso de error
        return {
            'ruc': '0915912604001',
            'razon_social': 'FARMACIA FÉ Y SALUD',
            'nombre_comercial': 'FARMACIA FÉ Y SALUD',
            'direccion_matriz': 'GUAYAQUIL / FEBRES CORDERO / ORIENTE S/N Y 38 AVA',
            'direccion_establecimiento': 'GUAYAQUIL / FEBRES CORDERO / ORIENTE S/N Y 38 AVA',
            'telefono': '0981276460',
            'email': '',
            'contribuyente_especial': '',
            'obligado_contabilidad': 'SI',
            'activo': True,
            'codigo_establecimiento': '001',
            'codigo_punto_emision': '001',
            'ambiente': 'PRODUCCIÓN',
            'emision': 'NORMAL',
            'eslogan': 'Tu Bienestar, Nuestra Prioridad',
            'verificacion_url': 'https://srienlinea.sri.gob.ec/sri-en-linea/consulta/55',
            'telefono_atencion': '0959711555',
            'mensaje_final': 'FARMACIA FÉ Y SALUD TE ESPERA'
        }


# Sistema de Facturas Electrónicas
@login_required
def facturas_electronicas(request):
    """Lista de facturas electrónicas con filtros por fecha y búsqueda siguiendo patrón C#"""
    
    # Parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio', timezone.now().date().strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', timezone.now().date().strftime('%Y-%m-%d'))
    texto_busqueda = request.GET.get('busqueda', '')
    
    # Consulta SQL siguiendo el patrón C#
    with connection.cursor() as cursor:
        sql = """
            SELECT 
                fv.id AS Id,
                fv.numeroFactura AS Factura,
                fv.numeroAutorizacion AS Autorizacion,
                COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS Cliente,
                fv.total AS Total,
                fv.estado AS Estado,
                fv.numeroAutorizacion AS ClaveAcceso,
                fv.fechaEmision AS FechaEmision
            FROM facturas_venta fv
            JOIN clientes c ON fv.idCliente = c.id
            WHERE 
                DATE(fv.fechaEmision) BETWEEN %s AND %s
                AND (COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) LIKE %s 
                     OR fv.numeroFactura LIKE %s 
                     OR fv.numeroAutorizacion LIKE %s)
            ORDER BY fv.fechaEmision DESC
        """
        
        busqueda_param = f"%{texto_busqueda}%"
        cursor.execute(sql, [fecha_inicio, fecha_fin, busqueda_param, busqueda_param, busqueda_param])
        
        # Convertir resultados a diccionarios
        columns = [col[0] for col in cursor.description]
        facturas = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Formatear fechas
        for factura in facturas:
            if factura['FechaEmision']:
                factura['FechaEmision'] = factura['FechaEmision'].strftime('%d/%m/%Y %H:%M')

    context = {
        'facturas': facturas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'texto_busqueda': texto_busqueda,
        'titulo': 'Facturas Electrónicas',
    }
    return render(request, 'ventas/facturas_electronicas_new.html', context)


@login_required
def buscar_facturas_por_numero(request):
    """Buscar facturas por número via AJAX"""
    if request.method == 'GET':
        termino = request.GET.get('termino', '')
        
        if not termino:
            return JsonResponse({'facturas': []})
        
        # Lógica de búsqueda siguiendo el patrón C#
        like = f"%{termino}%"
        solo_digitos = ''.join(filter(str.isdigit, termino))
        like_digits = f"%{solo_digitos}%"
        
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    fv.id AS Id,
                    fv.numeroFactura AS Factura,
                    fv.numeroAutorizacion AS Autorizacion,
                    COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS Cliente,
                    fv.total AS Total,
                    fv.estado AS Estado,
                    fv.numeroAutorizacion AS ClaveAcceso,
                    fv.fechaEmision AS FechaEmision
                FROM facturas_venta fv
                JOIN clientes c ON fv.idCliente = c.id
                WHERE 
                    -- Coincidencia directa o por fragmento
                    fv.numeroFactura LIKE %s
                    OR fv.numeroAutorizacion LIKE %s
                    -- Coincidencia por últimos dígitos ignorando guiones
                    OR REPLACE(fv.numeroFactura, '-', '') LIKE %s
                ORDER BY fv.fechaEmision DESC
                LIMIT 50
            """
            
            cursor.execute(sql, [like, like, like_digits])
            columns = [col[0] for col in cursor.description]
            facturas = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Formatear fechas para JSON
            for factura in facturas:
                if factura['FechaEmision']:
                    factura['FechaEmision'] = factura['FechaEmision'].strftime('%d/%m/%Y %H:%M')
        
        return JsonResponse({'facturas': facturas})
    
    return JsonResponse({'error': 'Método no permitido'})


@login_required
def obtener_factura_detalle(request, factura_id):
    """Obtener encabezado y detalle de factura siguiendo patrón C#"""
    
    # Obtener encabezado
    with connection.cursor() as cursor:
        sql_header = """
            SELECT 
                fv.id,
                fv.numeroFactura                  AS NumeroDocumento,
                fv.fechaEmision                  AS FechaEmision,
                fv.estado                        AS EstadoVenta,
                fv.numeroAutorizacion            AS Autorizacion,
                fv.subtotal                      AS SubtotalFactura,
                fv.descuento                     AS DescuentoFactura,
                fv.iva                           AS IvaFactura,
                fv.total                         AS TotalFactura,
                
                c.cedula_ruc                         AS Identificacion,
                COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS RazonSocial,
                c.direccion                      AS Direccion,
                COALESCE(NULLIF(c.telefono,''), c.celular) AS Telefono
            FROM facturas_venta fv
            JOIN clientes c ON c.id = fv.idCliente
            WHERE fv.id = %s
        """
        
        cursor.execute(sql_header, [factura_id])
        header_row = cursor.fetchone()
        
        if not header_row:
            return JsonResponse({'error': 'Factura no encontrada'}, status=404)
        
        header_columns = [col[0] for col in cursor.description]
        encabezado = dict(zip(header_columns, header_row))
        
        # Formatear fecha
        if encabezado['FechaEmision']:
            encabezado['FechaEmision'] = encabezado['FechaEmision'].strftime('%d/%m/%Y %H:%M')
    
    # Obtener detalle
    with connection.cursor() as cursor:
        sql_detalle = """
            SELECT 
                p.codigoPrincipal           AS Codigo,
                p.nombre           AS Descripcion,
                d.cantidad         AS Cantidad,
                d.precioUnitario   AS PrecioUnitario,
                d.descuentoValor   AS Descuento,
                d.ivaValor         AS Iva,
                (d.total - d.ivaValor) AS Subtotal
            FROM facturas_venta_detalle d
            JOIN productos p ON p.id = d.idProducto
            WHERE d.idFacturaVenta = %s
        """
        
        cursor.execute(sql_detalle, [factura_id])
        detalle_rows = cursor.fetchall()
        detalle_columns = [col[0] for col in cursor.description]
        detalle = [dict(zip(detalle_columns, row)) for row in detalle_rows]
    
    return JsonResponse({
        'encabezado': encabezado,
        'detalle': detalle
    })


@login_required
def obtener_factura_por_numero(request):
    """Obtener factura por número o términos de búsqueda"""
    termino = request.GET.get('termino', '')
    
    if not termino:
        return JsonResponse({'error': 'Término de búsqueda requerido'}, status=400)
    
    like = f"%{termino}%"
    solo_digitos = ''.join(filter(str.isdigit, termino))
    like_digits = f"%{solo_digitos}%"
    
    # Buscar ID de la factura
    with connection.cursor() as cursor:
        sql_id = """
            SELECT fv.id
            FROM facturas_venta fv
            WHERE 
                fv.numeroFactura = %s
                OR REPLACE(fv.numeroFactura, '-', '') = REPLACE(%s, '-', '')
                OR fv.numeroFactura LIKE %s
                OR REPLACE(fv.numeroFactura, '-', '') LIKE %s
            ORDER BY fv.fechaEmision DESC
            LIMIT 1
        """
        
        cursor.execute(sql_id, [termino, termino, like, like_digits])
        result = cursor.fetchone()
        
        if not result:
            return JsonResponse({'error': 'Factura no encontrada'}, status=404)
        
        factura_id = result[0]
    
    # Usar la función de detalle existente
    return obtener_factura_detalle(request, factura_id)


@login_required
def detalle_factura_electronica(request, pk):
    """Detalle completo de una factura electrónica"""
    factura = get_object_or_404(Venta, pk=pk)
    
    # Información adicional
    detalles = factura.detalles.select_related('producto').all()
    pagos = factura.pagos.all()
    
    context = {
        'factura': factura,
        'detalles': detalles,
        'pagos': pagos,
        'titulo': 'FACTURA ELECTRONICA',
        'numero': factura.numero_factura,
        'fecha': factura.fecha,
        'estado': factura.get_estado_display(),
        'autorizacion': '20023456372440',  # Número de autorización ficticio
        'ambiente': 'PRODUCCIÓN',
    }
    return render(request, 'ventas/detalle_factura_electronica.html', context)


@login_required
def anular_factura_electronica(request, pk):
    """Anular una factura electrónica"""
    factura = get_object_or_404(Venta, pk=pk)
    
    if request.method == 'POST':
        # Verificar si se puede anular
        if factura.estado == 'anulada':
            messages.error(request, 'Esta factura ya está anulada')
            return redirect('ventas:facturas_electronicas')
        
        # Restaurar stock de productos
        for detalle in factura.detalles.all():
            producto = detalle.producto
            producto.stock += detalle.cantidad
            producto.save()
        
        # Anular factura
        factura.estado = 'anulada'
        factura.save()
        
        messages.success(request, f'Factura {factura.numero_factura} anulada exitosamente')
        return redirect('ventas:facturas_electronicas')
    
    context = {
        'factura': factura,
        'titulo': 'Anular Factura',
    }
    return render(request, 'ventas/anular_factura.html', context)


@login_required
def reenviar_al_sri(request, pk):
    """Reenviar factura al SRI (simulado)"""
    factura = get_object_or_404(Venta, pk=pk)
    
    # Simular reenvío al SRI
    messages.success(request, f'Factura {factura.numero_factura} reenviada al SRI exitosamente')
    return redirect('ventas:facturas_electronicas')


@login_required
def exportar_facturas(request):
    """Exportar facturas a Excel/PDF"""
    # Esta función se implementaría para exportar datos
    messages.info(request, 'Función de exportación en desarrollo')
    return redirect('ventas:facturas_electronicas')


@login_required
def imprimir_facturas(request):
    """Imprimir facturas seleccionadas"""
    # Esta función se implementaría para imprimir múltiples facturas
    messages.info(request, 'Función de impresión en desarrollo')
    return redirect('ventas:facturas_electronicas')


# Sistema de Ingreso de Productos desde XML
@login_required
def ingreso_productos(request):
    """Pantalla principal para ingreso de productos desde XML o clave de acceso"""
    context = {
        'titulo': 'Ingreso de Productos',
        'subtitulo': 'Importar productos desde factura electrónica XML o clave de acceso'
    }
    return render(request, 'ventas/ingreso_productos.html', context)


@login_required
def procesar_xml_factura(request):
    """Procesar archivo XML de factura electrónica"""
    if request.method == 'POST':
        try:
            import xml.etree.ElementTree as ET
            from decimal import Decimal
            
            # Obtener archivo XML
            xml_file = request.FILES.get('xml_file')
            if not xml_file:
                return JsonResponse({'success': False, 'error': 'No se seleccionó archivo XML'})
            
            # Leer y parsear XML
            xml_content = xml_file.read().decode('utf-8')
            root = ET.fromstring(xml_content)
            
            # Extraer información de la factura
            productos_extraidos = []
            total_factura_xml = Decimal('0')
            
            # Buscar el comprobante dentro del CDATA
            comprobante_cdata = root.find('.//comprobante')
            if comprobante_cdata is not None:
                # Parsear el XML interno del CDATA
                comprobante_xml = ET.fromstring(comprobante_cdata.text)
                
                # Extraer información de la empresa emisora
                info_tributaria = comprobante_xml.find('infoTributaria')
                razon_social = info_tributaria.find('razonSocial').text if info_tributaria.find('razonSocial') is not None else ''
                ruc = info_tributaria.find('ruc').text if info_tributaria.find('ruc') is not None else ''
                
                # Extraer total de la factura desde infoFactura
                info_factura = comprobante_xml.find('infoFactura')
                if info_factura is not None:
                    total_elemento = info_factura.find('importeTotal')
                    if total_elemento is not None:
                        total_factura_xml = Decimal(total_elemento.text or '0')
                
                # Extraer productos de los detalles
                detalles = comprobante_xml.findall('.//detalle')
                
                for detalle in detalles:
                    codigo = detalle.find('codigoPrincipal')
                    descripcion = detalle.find('descripcion')
                    cantidad = detalle.find('cantidad')
                    precio_unitario = detalle.find('precioUnitario')
                    descuento = detalle.find('descuento')
                    precio_total = detalle.find('precioTotalSinImpuesto')
                    
                    # Calcular IVA
                    impuestos = detalle.find('impuestos')
                    iva_valor = Decimal('0')
                    if impuestos:
                        for impuesto in impuestos.findall('impuesto'):
                            codigo_impuesto = impuesto.find('codigo')
                            if codigo_impuesto is not None and codigo_impuesto.text == '2':  # IVA
                                iva_valor = Decimal(impuesto.find('valor').text or '0')
                    
                    producto = {
                        'codigo': codigo.text if codigo is not None else '',
                        'descripcion': descripcion.text if descripcion is not None else '',
                        'cantidad': float(cantidad.text) if cantidad is not None else 1.0,
                        'precio_unitario': float(precio_unitario.text) if precio_unitario is not None else 0.0,
                        'descuento': float(descuento.text) if descuento is not None else 0.0,
                        'subtotal': float(precio_total.text) if precio_total is not None else 0.0,
                        'iva': float(iva_valor),
                        'total': float(precio_total.text) + float(iva_valor) if precio_total is not None else 0.0
                    }
                    productos_extraidos.append(producto)
                
                return JsonResponse({
                    'success': True,
                    'productos': productos_extraidos,
                    'proveedor': {
                        'razon_social': razon_social,
                        'ruc': ruc
                    },
                    'total_factura': float(total_factura_xml),
                    'mensaje': f'Se encontraron {len(productos_extraidos)} productos en el XML'
                })
            
            else:
                return JsonResponse({'success': False, 'error': 'Formato de XML no válido'})
                
        except ET.ParseError:
            return JsonResponse({'success': False, 'error': 'Error al parsear el archivo XML'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al procesar XML: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required  
def consultar_clave_acceso(request):
    """Consultar factura por clave de acceso desde API externa"""
    if request.method == 'POST':
        try:
            import json
            import requests
            import xml.etree.ElementTree as ET
            
            data = json.loads(request.body)
            clave_acceso = data.get('clave_acceso', '').strip()
            
            if not clave_acceso or len(clave_acceso) != 49:
                return JsonResponse({'success': False, 'error': 'Clave de acceso debe tener 49 dígitos'})
            
            # Consultar API externa
            api_url = f'http://127.0.0.1:5001/api/consulta_sri/{clave_acceso}'
            
            try:
                response = requests.get(api_url, timeout=30)
                response.raise_for_status()
                api_data = response.json()
            except requests.exceptions.Timeout:
                return JsonResponse({'success': False, 'error': 'Timeout al consultar el SRI. Intente nuevamente.'})
            except requests.exceptions.ConnectionError:
                return JsonResponse({'success': False, 'error': 'No se pudo conectar al servicio de consulta SRI. Verifique que esté ejecutándose.'})
            except requests.exceptions.RequestException as e:
                return JsonResponse({'success': False, 'error': f'Error al consultar API: {str(e)}'})
            
            # Verificar estado de la autorización
            if api_data.get('estado') != 'AUTORIZADO':
                return JsonResponse({
                    'success': False, 
                    'error': f'Factura no autorizada. Estado: {api_data.get("estado", "DESCONOCIDO")}'
                })
            
            # Extraer XML del comprobante
            xml_content = api_data.get('comprobanteXml', '')
            if not xml_content:
                return JsonResponse({'success': False, 'error': 'No se recibió XML del comprobante'})
            
            # Parsear XML
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError:
                return JsonResponse({'success': False, 'error': 'Error al parsear XML del comprobante'})
            
            # Extraer información del emisor (proveedor)
            info_tributaria = root.find('infoTributaria')
            if info_tributaria is None:
                return JsonResponse({'success': False, 'error': 'XML sin información tributaria'})
            
            proveedor = {
                'ruc': info_tributaria.findtext('ruc', ''),
                'razon_social': info_tributaria.findtext('razonSocial', ''),
                'nombre_comercial': info_tributaria.findtext('nombreComercial', '')
            }
            
            # Extraer información de la factura
            info_factura = root.find('infoFactura')
            total_factura = 0.0
            if info_factura is not None:
                total_factura = float(info_factura.findtext('importeTotal', '0'))
            
            factura_info = {
                'numero': f"{info_tributaria.findtext('estab', '001')}-{info_tributaria.findtext('ptoEmi', '001')}-{info_tributaria.findtext('secuencial', '000000000')}",
                'fecha': info_factura.findtext('fechaEmision', '') if info_factura is not None else '',
                'autorizacion': api_data.get('numeroAutorizacion', clave_acceso),
                'fecha_autorizacion': api_data.get('fechaAutorizacion', ''),
                'total': total_factura
            }
            
            # Extraer productos del XML
            productos = []
            detalles = root.find('detalles')
            
            if detalles is not None:
                for detalle in detalles.findall('detalle'):
                    codigo = detalle.findtext('codigoPrincipal', '')
                    descripcion = detalle.findtext('descripcion', '')
                    cantidad = float(detalle.findtext('cantidad', '0'))
                    precio_unitario = float(detalle.findtext('precioUnitario', '0'))
                    descuento = float(detalle.findtext('descuento', '0'))
                    subtotal = float(detalle.findtext('precioTotalSinImpuesto', '0'))
                    
                    # Extraer IVA del producto
                    iva_valor = 0.0
                    impuestos = detalle.find('impuestos')
                    if impuestos is not None:
                        for impuesto in impuestos.findall('impuesto'):
                            codigo_impuesto = impuesto.findtext('codigo', '')
                            if codigo_impuesto == '2':  # Código 2 = IVA
                                iva_valor = float(impuesto.findtext('valor', '0'))
                                break
                    
                    total = subtotal + iva_valor
                    
                    producto = {
                        'codigo': codigo,
                        'descripcion': descripcion,
                        'cantidad': cantidad,
                        'precio_unitario': precio_unitario,
                        'descuento': descuento,
                        'subtotal': subtotal,
                        'iva': iva_valor,
                        'total': total
                    }
                    
                    productos.append(producto)
            
            if not productos:
                return JsonResponse({'success': False, 'error': 'No se encontraron productos en la factura'})
            
            return JsonResponse({
                'success': True,
                'productos': productos,
                'proveedor': proveedor,
                'factura_info': factura_info,
                'total_factura': total_factura,
                'mensaje': f'Factura consultada exitosamente. Se encontraron {len(productos)} producto(s).',
                'resumen_sri': api_data.get('resumen', {})
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Error en formato de datos'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al consultar clave de acceso: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def procesar_ingreso_productos(request):
    """Procesar el ingreso de productos seleccionados al inventario"""
    if request.method == 'POST':
        try:
            import json
            from productos.models import Producto, Categoria, CodigoAlternativo
            from proveedores.models import Proveedor
            from django.db import connection
            from datetime import datetime
            
            data = json.loads(request.body)
            productos_seleccionados = data.get('productos', [])
            proveedor_data = data.get('proveedor', {})
            
            if not productos_seleccionados:
                return JsonResponse({'success': False, 'error': 'No se seleccionaron productos para ingresar'})
            
            # Buscar o crear proveedor
            proveedor = None
            if proveedor_data.get('ruc'):
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id FROM proveedores WHERE ruc = %s AND anulado = 0 LIMIT 1
                    """, [proveedor_data['ruc']])
                    result = cursor.fetchone()
                    if result:
                        proveedor_id = result[0]
                    else:
                        # Crear proveedor
                        cursor.execute("""
                            INSERT INTO proveedores (ruc, razonSocial, nombreComercial, estado, anulado, creadoPor, creadoDate)
                            VALUES (%s, %s, %s, 1, 0, %s, NOW())
                        """, [
                            proveedor_data['ruc'],
                            proveedor_data.get('razon_social', 'Proveedor Importado'),
                            proveedor_data.get('razon_social', 'Proveedor Importado'),
                            request.user.id
                        ])
                        proveedor_id = cursor.lastrowid
            
            productos_creados = 0
            productos_actualizados = 0
            codigos_vinculados = 0
            productos_ubicados = 0
            
            for producto_data in productos_seleccionados:
                codigo = producto_data.get('codigo', '')
                cantidad = int(producto_data.get('cantidad', 1))
                costo_unidad = float(producto_data.get('costo_unidad', producto_data.get('precio_unitario', 0)))
                precio_venta = float(producto_data.get('precio_venta', costo_unidad * 1.3))
                fecha_caducidad = producto_data.get('fecha_caducidad')  # Puede ser None
                seccion_id = producto_data.get('seccion_id')
                percha_id = producto_data.get('percha_id')
                
                # Verificar si es un producto existente vinculado por el detector de duplicados
                es_existente = producto_data.get('es_existente', False)
                producto_id = producto_data.get('producto_id')
                codigo_vinculado = producto_data.get('codigo_vinculado', False)
                
                if es_existente and producto_id:
                    # Producto vinculado a uno existente - actualizar stock
                    with connection.cursor() as cursor:
                        cursor.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", [cantidad, producto_id])
                    productos_actualizados += 1
                    
                    # Vincular código alternativo si se marcó
                    if codigo_vinculado and codigo:
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT IGNORE INTO codigos_alternativo (producto_id, codigo, activo)
                                VALUES (%s, %s, 1)
                            """, [producto_id, codigo])
                            if cursor.rowcount > 0:
                                codigos_vinculados += 1
                    
                    # Ubicar producto si se proporcionó percha
                    if percha_id:
                        ubicar_producto_en_percha(producto_id, percha_id, cantidad)
                        productos_ubicados += 1
                else:
                    # Producto nuevo - verificar si ya existe por código
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT id FROM productos WHERE codigoPrincipal = %s AND anulado = 0", [codigo])
                        producto_existente = cursor.fetchone()
                        
                        if producto_existente:
                            # Ya existe - actualizar stock
                            cursor.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", [cantidad, producto_existente[0]])
                            productos_actualizados += 1
                            producto_id = producto_existente[0]
                        else:
                            # Crear nuevo producto
                            cursor.execute("""
                                INSERT INTO productos (
                                    codigoPrincipal, nombre, descripcion, fechaCaducidad,
                                    costoUnidad, precioVenta, stock, stockMinimo, stockMaximo,
                                    esDivisible, esPsicotropico, requiereCadenaFrio, requiereSeguimiento,
                                    calculoABCManual, activo, anulado,
                                    idTipoProducto, idClaseProducto, idCategoria, idSubcategoria, idMarca, idLaboratorio
                                ) VALUES (
                                    %s, %s, %s, %s,
                                    %s, %s, %s, 1, 100,
                                    0, 0, 0, 0,
                                    0, 1, 0,
                                    1, 1, 1, 1, 1, 1
                                )
                            """, [
                                codigo,
                                producto_data.get('descripcion', '')[:255],
                                producto_data.get('descripcion', ''),
                                fecha_caducidad if fecha_caducidad else None,
                                costo_unidad,
                                precio_venta,
                                cantidad
                            ])
                            producto_id = cursor.lastrowid
                            productos_creados += 1
                        
                        # Ubicar producto si se proporcionó percha
                        if percha_id and producto_id:
                            ubicar_producto_en_percha(producto_id, percha_id, cantidad)
                            productos_ubicados += 1
            
            # Construir mensaje de respuesta
            mensaje_partes = []
            if productos_creados > 0:
                mensaje_partes.append(f'{productos_creados} producto(s) creado(s)')
            if productos_actualizados > 0:
                mensaje_partes.append(f'{productos_actualizados} producto(s) actualizado(s)')
            if codigos_vinculados > 0:
                mensaje_partes.append(f'{codigos_vinculados} código(s) alternativo(s) vinculado(s)')
            if productos_ubicados > 0:
                mensaje_partes.append(f'{productos_ubicados} producto(s) ubicado(s) en perchas')
            
            mensaje = f"Ingreso procesado exitosamente. {', '.join(mensaje_partes)}." if mensaje_partes else "No se procesaron productos."
            
            return JsonResponse({
                'success': True,
                'mensaje': mensaje,
                'productos_creados': productos_creados,
                'productos_actualizados': productos_actualizados,
                'codigos_vinculados': codigos_vinculados,
                'productos_ubicados': productos_ubicados
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Error en formato de datos'})
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': f'Error al procesar ingreso: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


def ubicar_producto_en_percha(producto_id, percha_id, cantidad):
    """Ubica un producto en una percha específica"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Verificar si ya existe ubicación para este producto
        cursor.execute("""
            SELECT id FROM productos_ubicacionproducto 
            WHERE producto_id = %s AND activo = 1
        """, [producto_id])
        
        ubicacion_existente = cursor.fetchone()
        
        if ubicacion_existente:
            # Actualizar ubicación existente
            cursor.execute("""
                UPDATE productos_ubicacionproducto 
                SET percha_id = %s, cantidad_actual = %s
                WHERE id = %s
            """, [percha_id, cantidad, ubicacion_existente[0]])
        else:
            # Buscar posición disponible en la percha
            cursor.execute("""
                SELECT filas, columnas FROM productos_percha WHERE id = %s
            """, [percha_id])
            percha_info = cursor.fetchone()
            
            if percha_info:
                # Buscar primera posición libre
                cursor.execute("""
                    SELECT fila, columna FROM productos_ubicacionproducto
                    WHERE percha_id = %s AND activo = 1
                """, [percha_id])
                posiciones_ocupadas = cursor.fetchall()
                
                # Encontrar primera posición libre
                fila, columna = 1, 1
                for f in range(1, percha_info[0] + 1):
                    for c in range(1, percha_info[1] + 1):
                        if (f, c) not in posiciones_ocupadas:
                            fila, columna = f, c
                            break
                    if (fila, columna) != (1, 1):
                        break
                
                # Crear ubicación
                cursor.execute("""
                    INSERT INTO productos_ubicacionproducto 
                    (producto_id, percha_id, fila, columna, cantidad_maxima, cantidad_actual, activo)
                    VALUES (%s, %s, %s, %s, 50, %s, 1)
                """, [producto_id, percha_id, fila, columna, cantidad])


@login_required
def lista_ventas(request):
    """Lista de ventas realizadas con filtros por fecha y búsqueda siguiendo patrón C#"""
    
    # Parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    texto_busqueda = request.GET.get('busqueda', '')
    
    # Si no hay parámetros, mostrar ventas de hoy por defecto
    if not fecha_inicio and not fecha_fin and not texto_busqueda:
        fecha_inicio = timezone.now().date().strftime('%Y-%m-%d')
        fecha_fin = timezone.now().date().strftime('%Y-%m-%d')
    elif not fecha_inicio:
        fecha_inicio = '2020-01-01'  # Fecha muy antigua para mostrar todas
    elif not fecha_fin:
        fecha_fin = timezone.now().date().strftime('%Y-%m-%d')
    
    # Consulta SQL siguiendo el patrón C# - Priorizar facturas_venta
    with connection.cursor() as cursor:
        # Si hay búsqueda, hacer la consulta más permisiva con las fechas
        if texto_busqueda:
            # Buscar principalmente en facturas_venta, luego en ventas_venta como respaldo
            sql = """
                (SELECT 
                    fv.id AS Id,
                    fv.numeroFactura AS NumeroVenta,
                    COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS Cliente,
                    fv.total AS Total,
                    fv.estado AS Estado,
                    fv.fechaEmision AS FechaVenta,
                    'ELECTRONICO' AS MetodoPago,
                    CONCAT(IFNULL(u.first_name,''),' ',IFNULL(u.last_name,'')) AS Vendedor,
                    'FACTURA' AS TipoDocumento
                FROM facturas_venta fv
                LEFT JOIN clientes c ON fv.idCliente = c.id
                LEFT JOIN auth_user u ON fv.idUsuario = u.id
                WHERE 
                    (COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) LIKE %s 
                     OR fv.numeroFactura LIKE %s 
                     OR CONCAT(IFNULL(u.first_name,''),' ',IFNULL(u.last_name,'')) LIKE %s))
                
                UNION ALL
                
                (SELECT 
                    v.id AS Id,
                    v.numero_factura AS NumeroVenta,
                    COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS Cliente,
                    v.total AS Total,
                    v.estado AS Estado,
                    v.fecha AS FechaVenta,
                    v.tipo_pago AS MetodoPago,
                    CONCAT(IFNULL(u.first_name,''),' ',IFNULL(u.last_name,'')) AS Vendedor,
                    'VENTA' AS TipoDocumento
                FROM ventas_venta v
                LEFT JOIN clientes c ON v.cliente_id = c.id
                LEFT JOIN auth_user u ON v.vendedor_id = u.id
                WHERE 
                    (COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) LIKE %s 
                     OR v.numero_factura LIKE %s 
                     OR CONCAT(IFNULL(u.first_name,''),' ',IFNULL(u.last_name,'')) LIKE %s))
                
                ORDER BY FechaVenta DESC, Id DESC
                LIMIT 100
            """
            
            busqueda_param = f'%{texto_busqueda}%'
            
            cursor.execute(sql, [
                busqueda_param, busqueda_param, busqueda_param,  # Para facturas_venta
                busqueda_param, busqueda_param, busqueda_param   # Para ventas_venta
            ])
        else:
            # Sin búsqueda, aplicar filtros de fecha normalmente - priorizar facturas_venta
            sql = """
                (SELECT 
                    fv.id AS Id,
                    fv.numeroFactura AS NumeroVenta,
                    COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS Cliente,
                    fv.total AS Total,
                    fv.estado AS Estado,
                    fv.fechaEmision AS FechaVenta,
                    'ELECTRONICO' AS MetodoPago,
                    CONCAT(IFNULL(u.first_name,''),' ',IFNULL(u.last_name,'')) AS Vendedor,
                    'FACTURA' AS TipoDocumento
                FROM facturas_venta fv
                LEFT JOIN clientes c ON fv.idCliente = c.id
                LEFT JOIN auth_user u ON fv.idUsuario = u.id
                WHERE 
                    DATE(fv.fechaEmision) BETWEEN %s AND %s)
                
                UNION ALL
                
                (SELECT 
                    v.id AS Id,
                    v.numero_factura AS NumeroVenta,
                    COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS Cliente,
                    v.total AS Total,
                    v.estado AS Estado,
                    v.fecha AS FechaVenta,
                    v.tipo_pago AS MetodoPago,
                    CONCAT(IFNULL(u.first_name,''),' ',IFNULL(u.last_name,'')) AS Vendedor,
                    'VENTA' AS TipoDocumento
                FROM ventas_venta v
                LEFT JOIN clientes c ON v.cliente_id = c.id
                LEFT JOIN auth_user u ON v.vendedor_id = u.id
                WHERE 
                    DATE(v.fecha) BETWEEN %s AND %s)
                
                ORDER BY FechaVenta DESC, Id DESC
                LIMIT 100
            """
            
            cursor.execute(sql, [fecha_inicio, fecha_fin, fecha_inicio, fecha_fin])
        
        ventas = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        ventas_list = []
        for venta in ventas:
            ventas_list.append({
                'Id': venta[0],
                'NumeroVenta': venta[1],
                'Cliente': venta[2] or 'Sin cliente',
                'Total': venta[3],
                'Estado': venta[4],
                'FechaVenta': venta[5],
                'MetodoPago': venta[6],
                'Vendedor': venta[7] or 'Sin vendedor',
                'TipoDocumento': venta[8] if len(venta) > 8 else 'VENTA'  # Para manejar ambos casos
            })
    
    context = {
        'ventas': ventas_list,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'texto_busqueda': texto_busqueda,
        'titulo': 'Facturas y Ventas Realizadas'
    }
    return render(request, 'ventas/lista_ventas_new.html', context)


@login_required_offline_safe
def nueva_venta(request):
    """Crear nueva venta - Interfaz POS con soporte offline"""
    
    # Modo offline: intentar conectar a la base de datos
    modo_offline = False
    caja_abierta_data = None
    clientes_list = []
    productos_list = []
    categorias_list = []
    
    try:
        # Importar modelos solo cuando se necesiten
        from caja.models import CierreCaja
        from clientes.models import Cliente
        from productos.models import Producto, Categoria
        
        # Verificar si hay caja abierta
        try:
            caja_abierta_data = CierreCaja.obtener_caja_abierta()
            
            if not caja_abierta_data:
                messages.warning(request, 'Debe abrir una caja antes de realizar ventas')
                return redirect('caja:abrir')
                
        except OperationalError as db_error:
            # Error de base de datos al verificar caja - modo offline
            print(f"OperationalError BD verificando caja: {db_error}")
            modo_offline = True
            # En modo offline, usar caja de sesión
            caja_abierta_data = request.session.get('caja_offline')
            if not caja_abierta_data:
                # No hay caja offline, crear una automáticamente
                caja_abierta_data = {
                    'idCaja': 1,
                    'nombre': 'Caja Principal (Offline)',
                    'montoInicial': 0.0,
                    'modo_offline': True,
                    'fechaApertura': str(date.today())
                }
                request.session['caja_offline'] = caja_abierta_data
                messages.info(request, 'MODO OFFLINE: Caja creada automáticamente')
        
        # Intentar cargar datos si no estamos en modo offline
        if not modo_offline:
            try:
                clientes_list = list(Cliente.objects.filter(estado=True, anulado=False).values('id', 'nombres', 'apellidos', 'cedula_ruc'))
                
                # Cargar productos con información de ubicación usando SQL directo
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT p.id, p.codigoPrincipal, p.nombre, p.precioVenta, p.stock,
                               p.idCategoria, p.activo,
                               u.fila, u.columna, pr.nombre as percha_nombre, s.nombre as seccion_nombre, s.color as seccion_color
                        FROM productos p
                        LEFT JOIN productos_ubicacionproducto u ON p.id = u.producto_id AND u.activo = 1
                        LEFT JOIN productos_percha pr ON u.percha_id = pr.id
                        LEFT JOIN productos_seccion s ON pr.seccion_id = s.id
                        WHERE p.activo = 1 AND p.stock > 0
                        ORDER BY p.nombre
                    """)
                    
                    columns = [col[0] for col in cursor.description]
                    todos_productos = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
                    # Formatear ubicación legible
                    for producto in todos_productos:
                        if producto.get('fila') and producto.get('columna'):
                            producto['ubicacion'] = f"{producto.get('seccion_nombre', 'N/A')} - {producto.get('percha_nombre', 'N/A')} (F{producto['fila']}C{producto['columna']})"
                            producto['tiene_ubicacion'] = True
                        else:
                            producto['ubicacion'] = 'Sin ubicar'
                            producto['tiene_ubicacion'] = False
                
                # Solo mostrar primeros 20 productos en la página inicial
                productos_list = todos_productos[:20]
                
                categorias_list = list(Categoria.objects.all().values())
                
                # Guardar TODOS en cache para uso offline
                from django.core.cache import cache
                cache.set('productos_offline', todos_productos, timeout=None)  # Guardar todos
                cache.set('clientes_offline', clientes_list, timeout=None)
                cache.set('categorias_offline', categorias_list, timeout=None)
                
                # Información de paginación
                total_productos = len(todos_productos)
                
            except OperationalError as db_error:
                print(f"OperationalError BD cargando datos: {db_error}")
                modo_offline = True
        
    except OperationalError as e:
        # Error de conexión general - activar modo offline
        print(f"OperationalError de conexión: {e}")
        modo_offline = True
    except Exception as e:
        # Otros errores no relacionados con BD - reportar pero no activar modo offline
        print(f"Error no crítico en nueva_venta: {e}")
        import traceback
        traceback.print_exc()
    
    # Si estamos en modo offline, configurar datos por defecto
    if modo_offline:
        messages.warning(request, 'Modo OFFLINE: Sin conexión a la base de datos. Usando datos locales del navegador.')
        
        # Intentar cargar productos desde cache si existe
        from django.core.cache import cache
        productos_cache = cache.get('productos_offline', [])
        clientes_cache = cache.get('clientes_offline', [])
        categorias_cache = cache.get('categorias_offline', [])
        
        if not caja_abierta_data:
            caja_abierta_data = {
                'idCaja': 1,
                'nombre': 'Caja Principal (Offline)',
                'montoInicial': 0,
                'modo_offline': True
            }
        
        # Usar datos del cache si existen - solo primeros 20 en página
        if productos_cache:
            productos_list = productos_cache[:20]  # Solo 20 para la vista inicial
            total_productos = len(productos_cache)
            messages.info(request, f'{total_productos} productos disponibles en cache (mostrando primeros 20)')
        else:
            total_productos = 0
            messages.info(request, f'{len(productos_cache)} productos cargados desde cache local')
        
        if clientes_cache:
            clientes_list = clientes_cache
            
        if categorias_cache:
            categorias_list = categorias_cache
    
    # Obtener configuración de la empresa
    empresa_config = obtener_configuracion_empresa()
    
    context = {
        'clientes': clientes_list,
        'productos': productos_list,
        'categorias': categorias_list,
        'caja_abierta': caja_abierta_data,
        'modo_offline': modo_offline,
        'empresa': empresa_config,
        'titulo': 'Punto de Venta' + (' - MODO OFFLINE' if modo_offline else '')
    }
    
    return render(request, 'ventas/crear.html', context)


def generar_json_facturacion_electronica_real(factura_venta):
    """Generar JSON para facturación electrónica del SRI usando FacturaVenta"""
    # Obtener configuración de la empresa desde la tabla empresas
    EMPRESA_CONFIG = obtener_configuracion_empresa()
    
    # Obtener secuencial de la factura
    secuencial = str(factura_venta.idFactura).zfill(9)  # Padding con ceros a la izquierda
    
    # Obtener datos del cliente
    cliente = factura_venta.cliente
    
    # Construir JSON según especificación SRI
    json_factura = {
        "empresaRuc": EMPRESA_CONFIG['ruc'],
        "ambiente": 1,  # 1 = Pruebas, 2 = Producción
        "tipoComprobante": "01",  # 01 = Factura
        "infoTributaria": {
            "estab": EMPRESA_CONFIG['codigo_establecimiento'],
            "ptoEmi": EMPRESA_CONFIG['codigo_punto_emision'],
            "secuencial": secuencial,
            "dirMatriz": EMPRESA_CONFIG['direccion_matriz']
        },
        "infoFactura": {
            "fechaEmision": factura_venta.fechaEmision.strftime("%d/%m/%Y"),
            "dirEstablecimiento": EMPRESA_CONFIG['direccion_establecimiento'],
            "obligadoContabilidad": EMPRESA_CONFIG['obligado_contabilidad'],
            "tipoIdentificacionComprador": "05",  # 05 = Cédula
            "razonSocialComprador": cliente.nombre_completo if cliente else "CONSUMIDOR FINAL",
            "identificacionComprador": cliente.cedula_ruc if cliente and cliente.cedula_ruc else "9999999999999",
            "direccionComprador": cliente.direccion if cliente and cliente.direccion else "GUAYAQUIL",
            "totalSinImpuestos": float(factura_venta.subtotal),
            "totalDescuento": float(factura_venta.descuento) if factura_venta.descuento else 0.00,
            "totalConImpuestos": [
                {
                    "codigo": "2",  # Código IVA
                    "codigoPorcentaje": "2",  # 15% IVA
                    "baseImponible": float(factura_venta.subtotal),
                    "valor": float(factura_venta.iva)
                }
            ] if factura_venta.iva > 0 else [],
            "propina": 0.00,
            "importeTotal": float(factura_venta.total),
            "moneda": "DOLAR"
        },
        "detalles": []
    }
    
    # Agregar detalles de productos
    detalles = FacturaVentaDetalle.objects.filter(idFacturaVenta=factura_venta.idFactura)
    
    for detalle in detalles:
        cantidad = float(detalle.cantidad)
        precio_unitario = float(detalle.precioUnitario)
        descuento_detalle = float(detalle.descuentoValor) if detalle.descuentoValor else 0.00
        precio_total_sin_impuesto = cantidad * precio_unitario - descuento_detalle
        
        # Obtener información del producto
        try:
            producto = Producto.objects.get(id=detalle.idProducto)
            codigo_principal = producto.codigo_principal
        except Producto.DoesNotExist:
            codigo_principal = f"PROD-{detalle.idProducto}"
        
        detalle_json = {
            "codigoPrincipal": codigo_principal,
            "descripcion": detalle.productoNombre,
            "cantidad": cantidad,
            "precioUnitario": precio_unitario,
            "descuento": descuento_detalle,
            "precioTotalSinImpuesto": precio_total_sin_impuesto,
            "impuestos": [
                {
                    "codigo": "2",  # Código IVA
                    "codigoPorcentaje": "2",  # 15% IVA
                    "tarifa": 15.00,
                    "baseImponible": precio_total_sin_impuesto,
                    "valor": float(detalle.ivaValor)
                }
            ] if detalle.ivaValor > 0 else []
        }
        
        json_factura["detalles"].append(detalle_json)
    
    return json_factura


def generar_json_facturacion_electronica(venta):
    """Generar JSON para facturación electrónica del SRI y enviarlo a la API"""
    # Obtener configuración de la empresa desde la tabla empresas
    EMPRESA_CONFIG = obtener_configuracion_empresa()
    
    # Obtener secuencial de la factura
    secuencial = str(venta.id).zfill(9)  # Padding con ceros a la izquierda
    
    # Calcular impuestos
    total_sin_impuestos = float(venta.subtotal)
    total_iva = float(venta.impuesto)
    total_con_impuestos = float(venta.total)
    
    # Construir JSON según especificación SRI
    json_factura = {
        "empresaRuc": EMPRESA_CONFIG['ruc'],
        "ambiente": 1,  # 1 = Pruebas, 2 = Producción
        "tipoComprobante": "01",  # 01 = Factura
        "infoTributaria": {
            "estab": EMPRESA_CONFIG['codigo_establecimiento'],
            "ptoEmi": EMPRESA_CONFIG['codigo_punto_emision'],
            "secuencial": secuencial,
            "dirMatriz": EMPRESA_CONFIG['direccion_matriz']
        },
        "infoFactura": {
            "fechaEmision": venta.fecha.strftime("%d/%m/%Y"),
            "dirEstablecimiento": EMPRESA_CONFIG['direccion_establecimiento'],
            "obligadoContabilidad": EMPRESA_CONFIG['obligado_contabilidad'],
            "tipoIdentificacionComprador": "05",  # 05 = Cédula
            "razonSocialComprador": venta.cliente.nombre_completo if venta.cliente else "CONSUMIDOR FINAL",
            "identificacionComprador": venta.cliente.cedula_ruc if venta.cliente and venta.cliente.cedula_ruc else "9999999999999",
            "direccionComprador": venta.cliente.direccion if venta.cliente and venta.cliente.direccion else "GUAYAQUIL",
            "totalSinImpuestos": total_sin_impuestos,
            "totalDescuento": float(venta.descuento) if venta.descuento else 0.00,
            "totalConImpuestos": [
                {
                    "codigo": "2",  # Código IVA
                    "codigoPorcentaje": "4",  # 4 = 15% IVA (código del SRI para 15%)
                    "baseImponible": total_sin_impuestos,
                    "valor": total_iva
                }
            ] if total_iva > 0 else [],
            "propina": 0.00,
            "importeTotal": total_con_impuestos,
            "moneda": "DOLAR"
        },
        "detalles": []
    }
    
    # Agregar detalles de productos
    for detalle in venta.detalleventa_set.all():
        producto = detalle.producto
        cantidad = float(detalle.cantidad)
        precio_unitario = float(detalle.precio_unitario)
        descuento_detalle = float(detalle.descuento) if detalle.descuento else 0.00
        precio_total_sin_impuesto = cantidad * precio_unitario - descuento_detalle
        
        # Calcular impuestos del detalle (IVA 15%)
        tarifa_iva = 15.00
        base_imponible = precio_total_sin_impuesto
        valor_iva = base_imponible * (tarifa_iva / 100)
        
        detalle_json = {
            "codigoPrincipal": producto.codigo_principal,
            "descripcion": producto.nombre,
            "cantidad": cantidad,
            "precioUnitario": precio_unitario,
            "descuento": descuento_detalle,
            "precioTotalSinImpuesto": precio_total_sin_impuesto,
            "impuestos": [
                {
                    "codigo": "2",  # Código IVA
                    "codigoPorcentaje": "4",  # 4 = 15% IVA (código del SRI para 15%)
                    "tarifa": tarifa_iva,
                    "baseImponible": base_imponible,
                    "valor": valor_iva
                }
            ] if tarifa_iva > 0 else []
        }
        
        json_factura["detalles"].append(detalle_json)
    
    # Enviar JSON a la API de facturación electrónica
    try:
        api_url = "http://127.0.0.1:5001/factura"
        response = requests.post(
            api_url,
            json=json_factura,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            resultado = response.json()
            return {
                'success': True,
                'json_enviado': json_factura,
                'respuesta_api': resultado,
                'mensaje': 'Factura electrónica generada exitosamente'
            }
        else:
            return {
                'success': False,
                'json_enviado': json_factura,
                'error': f'Error al enviar factura: {response.status_code}',
                'detalle': response.text
            }
            
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'json_enviado': json_factura,
            'error': 'No se pudo conectar al servicio de facturación electrónica',
            'mensaje': 'Verifique que la API esté ejecutándose en http://127.0.0.1:5001'
        }
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'json_enviado': json_factura,
            'error': 'Timeout al enviar factura electrónica',
            'mensaje': 'La API tardó demasiado en responder'
        }
    except Exception as e:
        return {
            'success': False,
            'json_enviado': json_factura,
            'error': f'Error inesperado: {str(e)}'
        }


@login_required
@require_http_methods(["POST"])
def crear_ajax(request):
    """Crear venta via AJAX - Usando tablas reales facturas_venta"""
    try:
        data = json.loads(request.body)
        
        # Verificar caja abierta usando función centralizada
        from caja.models import CierreCaja
        caja_abierta_data = CierreCaja.obtener_caja_abierta()
        
        if not caja_abierta_data:
            return JsonResponse({'success': False, 'error': 'No hay caja abierta'})
        
        # Convertir a formato que espera el código existente
        caja_abierta = (caja_abierta_data['id'], caja_abierta_data['idCaja'])
        
        with transaction.atomic():
            # --- 1. Calcular totales ---
            subtotal = Decimal('0.00')
            descuento = Decimal('0.00')
            iva_total = Decimal('0.00')
            productos_procesados = []
            
            for item in data['items']:
                producto = Producto.objects.get(id=item['producto_id'])
                cantidad = Decimal(str(item['cantidad']))
                precio_unitario = Decimal(str(item['precio_unitario']))
                
                # Verificar stock
                if producto.stock < cantidad:
                    raise ValueError(f'Stock insuficiente para el producto "{producto.nombre}". Stock disponible: {producto.stock}, solicitado: {cantidad}')
                
                # Calcular valores del producto
                precio_total_sin_impuesto = cantidad * precio_unitario
                descuento_producto = Decimal('0.00')  # Por ahora sin descuento
                iva_producto = precio_total_sin_impuesto * Decimal('0.15')  # IVA 15%
                total_producto = precio_total_sin_impuesto - descuento_producto + iva_producto
                
                subtotal += precio_total_sin_impuesto
                descuento += descuento_producto
                iva_total += iva_producto
                
                productos_procesados.append({
                    'producto': producto,
                    'cantidad': cantidad,
                    'precio_unitario': precio_unitario,
                    'precio_total_sin_impuesto': precio_total_sin_impuesto,
                    'descuento': descuento_producto,
                    'iva': iva_producto,
                    'total': total_producto
                })
            
            total_final = subtotal - descuento + iva_total
            
            # Generar número de factura con formato 001-001-000000015
            # Obtener el siguiente número secuencial
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(CAST(SUBSTRING_INDEX(numeroFactura, '-', -1) AS UNSIGNED)), 0) + 1 FROM facturas_venta WHERE numeroFactura LIKE '001-001-%'")
                siguiente_numero = cursor.fetchone()[0]
            
            numero_factura = f"001-001-{str(siguiente_numero).zfill(9)}"
            
            # --- 2. Insertar el encabezado de la factura (facturas_venta) ---
            with connection.cursor() as cursor:
                sql_factura = """
                    INSERT INTO facturas_venta 
                    (idCliente, idUsuario, idCierreCaja, numeroFactura, numeroAutorizacion, fechaEmision, 
                     subtotal, descuento, iva, total, estado, creadoPor, creadoDate, anulado)
                    VALUES
                    (%s, %s, %s, %s, %s, NOW(),
                     %s, %s, %s, %s, 'PAGADA', %s, NOW(), 0)
                """
                
                cursor.execute(sql_factura, [
                    data.get('cliente_id') or None,  # idCliente
                    request.user.id,                 # idUsuario
                    caja_abierta[0],                # idCierreCaja
                    numero_factura,                 # numeroFactura
                    '',                             # numeroAutorizacion (vacío por ahora)
                    float(subtotal),                # subtotal
                    float(descuento),               # descuento
                    float(iva_total),               # iva
                    float(total_final),             # total
                    request.user.id                 # creadoPor
                ])
                
                # Obtener ID de la factura insertada
                cursor.execute("SELECT LAST_INSERT_ID()")
                id_factura_venta = cursor.fetchone()[0]
            
            # --- 3. Insertar cada producto en el detalle (facturas_venta_detalle) ---
            for prod_data in productos_procesados:
                producto = prod_data['producto']
                
                with connection.cursor() as cursor:
                    sql_detalle = """
                        INSERT INTO facturas_venta_detalle
                        (idFacturaVenta, idProducto, cantidad, precioUnitario, descuentoValor, ivaValor, total, productoNombre)
                        VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(sql_detalle, [
                        id_factura_venta,                      # idFacturaVenta
                        producto.id,                           # idProducto
                        float(prod_data['cantidad']),         # cantidad
                        float(prod_data['precio_unitario']),  # precioUnitario
                        float(prod_data['descuento']),        # descuentoValor
                        float(prod_data['iva']),              # ivaValor
                        float(prod_data['total']),            # total
                        producto.nombre                        # productoNombre
                    ])
                
                # Obtener stock actual
                with connection.cursor() as cursor:
                    cursor.execute("SELECT stock FROM productos WHERE id = %s", [producto.id])
                    saldo_actual = Decimal(str(cursor.fetchone()[0]))
                
                nuevo_saldo = saldo_actual - prod_data['cantidad']
                
                # --- 4. INSERTAR EL MOVIMIENTO EN EL KARDEX ---
                with connection.cursor() as cursor:
                    sql_kardex = """
                        INSERT INTO kardex_movimientos 
                        (idProducto, tipoMovimiento, detalle, egreso, saldo)
                        VALUES 
                        (%s, 'VENTA', %s, %s, %s)
                    """
                    
                    cursor.execute(sql_kardex, [
                        producto.id,                           # idProducto
                        f"Factura Venta N° {numero_factura}",  # detalle
                        float(prod_data['cantidad']),         # egreso
                        float(nuevo_saldo)                     # saldo
                    ])
                
                # --- 5. ACTUALIZAR EL STOCK EN LA TABLA DE PRODUCTOS ---
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", [
                        float(nuevo_saldo),
                        producto.id
                    ])
            
            # Crear objeto venta para generar JSON (usar FacturaVenta)
            factura_venta = FacturaVenta.objects.get(idFactura=id_factura_venta)
            
            # Generar JSON para facturación electrónica
            json_facturacion = generar_json_facturacion_electronica_real(factura_venta)
            
            return JsonResponse({
                'success': True, 
                'numero_venta': numero_factura,
                'total': float(total_final),
                'json_facturacion': json_facturacion,
                'venta_id': id_factura_venta
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def ticket(request, numero_venta):
    """Generar ticket de venta"""
    venta = get_object_or_404(Venta, numero_factura=numero_venta)
    
    context = {
        'venta': venta,
        'titulo': f'Ticket {venta.numero_factura}'
    }
    return render(request, 'ventas/ticket.html', context)


@login_required
def ticket_termico(request, venta_id):
    """Generar ticket térmico para impresión"""
    try:
        factura_venta = get_object_or_404(FacturaVenta, idFactura=venta_id)
        
        # Debug: verificar el objeto
        print(f"DEBUG: FacturaVenta ID: {factura_venta.idFactura}")
        print(f"DEBUG: Cliente ID: {factura_venta.idCliente}")
        
        # Obtener configuración de la empresa desde la tabla empresas
        EMPRESA_CONFIG = obtener_configuracion_empresa()
        
        # Obtener detalles de la factura
        detalles = FacturaVentaDetalle.objects.filter(idFacturaVenta=factura_venta.idFactura)
        print(f"DEBUG: Detalles count: {detalles.count()}")
        
        context = {
            'venta': factura_venta,
            'empresa': EMPRESA_CONFIG,
            'secuencial': str(factura_venta.idFactura).zfill(9),
            'numero_factura': str(factura_venta.idFactura).zfill(6),
            'detalles': detalles,
            'debug_id': factura_venta.idFactura,  # Para debug en template
        }
        
        return render(request, 'ventas/ticket_termico.html', context)
    except Exception as e:
        print(f"ERROR en ticket_termico: {str(e)}")
        import traceback
        traceback.print_exc()
        return render(request, 'ventas/debug_ticket.html', {'error': str(e), 'debug_id': venta_id})


@login_required
def json_facturacion(request, venta_id):
    """Endpoint para obtener JSON de facturación electrónica"""
    factura_venta = get_object_or_404(FacturaVenta, idFactura=venta_id)
    json_facturacion = generar_json_facturacion_electronica_real(factura_venta)
    
    response = JsonResponse(json_facturacion, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="factura_{factura_venta.numeroFactura}.json"'
    return response


def buscar_producto(request):
    """Buscar productos para POS via AJAX - incluye información de ubicación"""
    print(f"=== BÚSQUEDA DE PRODUCTOS ===")
    print(f"Método: {request.method}")
    print(f"Es AJAX: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
    print(f"Usuario autenticado: {request.user.is_authenticated}")
    
    if request.method == 'GET':
        search = request.GET.get('search', '')
        print(f"Término de búsqueda: '{search}'")
        
        # Consulta SQL que incluye información de ubicación
        with connection.cursor() as cursor:
            if not search or search.strip() == '':
                print("Búsqueda vacía, devolviendo productos iniciales")
                sql = """
                    SELECT 
                        p.id, p.codigoPrincipal, p.nombre, p.precioVenta, p.stock,
                        c.nombre as categoria,
                        CASE WHEN u.id IS NOT NULL 
                             THEN CONCAT(s.nombre, ' - ', pr.nombre, ' (F', u.fila, 'C', u.columna, ')')
                             ELSE NULL 
                        END as ubicacion_completa,
                        CASE WHEN u.id IS NOT NULL 
                             THEN CONCAT(pr.nombre, '-F', u.fila, 'C', u.columna)
                             ELSE NULL 
                        END as codigo_ubicacion,
                        s.color as color_seccion
                    FROM productos p
                    LEFT JOIN categorias c ON p.idCategoria = c.id
                    LEFT JOIN productos_ubicacionproducto u ON p.id = u.producto_id AND u.activo = 1
                    LEFT JOIN productos_percha pr ON u.percha_id = pr.id AND pr.activo = 1
                    LEFT JOIN productos_seccion s ON pr.seccion_id = s.id AND s.activo = 1
                    WHERE p.activo = 1 AND p.anulado = 0 AND p.stock > 0
                    ORDER BY p.nombre
                    LIMIT 20
                """
                cursor.execute(sql)
            else:
                # Búsqueda con término específico
                sql = """
                    SELECT 
                        p.id, p.codigoPrincipal, p.nombre, p.precioVenta, p.stock,
                        c.nombre as categoria,
                        CASE WHEN u.id IS NOT NULL 
                             THEN CONCAT(s.nombre, ' - ', pr.nombre, ' (F', u.fila, 'C', u.columna, ')')
                             ELSE NULL 
                        END as ubicacion_completa,
                        CASE WHEN u.id IS NOT NULL 
                             THEN CONCAT(pr.nombre, '-F', u.fila, 'C', u.columna)
                             ELSE NULL 
                        END as codigo_ubicacion,
                        s.color as color_seccion
                    FROM productos p
                    LEFT JOIN categorias c ON p.idCategoria = c.id
                    LEFT JOIN productos_ubicacionproducto u ON p.id = u.producto_id AND u.activo = 1
                    LEFT JOIN productos_percha pr ON u.percha_id = pr.id AND pr.activo = 1
                    LEFT JOIN productos_seccion s ON pr.seccion_id = s.id AND s.activo = 1
                    WHERE p.activo = 1 AND p.anulado = 0 AND p.stock > 0
                      AND (p.nombre LIKE %s OR p.codigoPrincipal LIKE %s OR p.codigoAuxiliar LIKE %s)
                    ORDER BY p.nombre
                    LIMIT 10
                """
                search_param = f'%{search}%'
                cursor.execute(sql, [search_param, search_param, search_param])
            
            productos_raw = cursor.fetchall()
        
        print(f"Productos encontrados: {len(productos_raw)}")
        
        productos_data = []
        for producto in productos_raw:
            print(f"- {producto[1]}: {producto[2]} (Stock: {producto[4]}) - Ubicación: {producto[6] or 'Sin ubicar'}")
            
            # Determinar estado de ubicación
            tiene_ubicacion = producto[6] is not None
            
            productos_data.append({
                'id': producto[0],
                'codigo': producto[1],
                'codigo_principal': producto[1],  # Alias para compatibilidad
                'nombre': producto[2],
                'precio': float(producto[3]) if producto[3] else 0,
                'precio_venta': float(producto[3]) if producto[3] else 0,  # Alias para compatibilidad
                'stock': float(producto[4]) if producto[4] else 0,
                'categoria': producto[5] or '',
                'aplica_iva': True,  # Por defecto para el negocio
                'tiene_ubicacion': tiene_ubicacion,
                'ubicacion': producto[6] if tiene_ubicacion else 'Sin ubicar',  # Campo que usa el JavaScript
                'ubicacion_completa': producto[6] if tiene_ubicacion else None,
                'codigo_ubicacion': producto[7] if tiene_ubicacion else None,
                'color_seccion': producto[8] if tiene_ubicacion else None,
                'estado_ubicacion': 'ubicado' if tiene_ubicacion else 'sin_ubicar'
            })
        
        resultado = {'productos': productos_data}
        print(f"Resultado a enviar: {len(productos_data)} productos")
        return JsonResponse(resultado)
    
    return JsonResponse({'error': 'Método no permitido'})


@login_required
def agregar_producto(request):
    """Agregar producto al carrito via AJAX"""
    if request.method == 'POST':
        # Lógica para agregar producto al carrito
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Método no permitido'})


@login_required
def procesar_venta(request):
    """Procesar y finalizar venta"""
    if request.method == 'POST':
        # Lógica para procesar venta
        messages.success(request, 'Venta procesada exitosamente')
        return JsonResponse({'success': True, 'redirect_url': '/ventas/'})
    
    return JsonResponse({'error': 'Método no permitido'})


@login_required
def detalle_venta(request, pk):
    """Ver detalles de una venta"""
    from .models import FacturaVenta, FacturaVentaDetalle
    
    venta = get_object_or_404(FacturaVenta, pk=pk)
    detalles = FacturaVentaDetalle.objects.filter(idFacturaVenta=pk)
    
    context = {
        'venta': venta,
        'detalles': detalles,
        'titulo': f'Factura {venta.numeroFactura}'
    }
    return render(request, 'ventas/detalle.html', context)


@login_required
def anular_venta(request, pk):
    """Anular una venta"""
    venta = get_object_or_404(Venta, pk=pk)
    
    if request.method == 'POST':
        venta.estado = 'anulada'
        venta.save()
        messages.success(request, 'Venta anulada exitosamente')
        return redirect('ventas:lista')
    
    context = {
        'venta': venta,
        'titulo': 'Anular Venta'
    }
    return render(request, 'ventas/anular.html', context)


@login_required
def imprimir_factura(request, pk):
    """Imprimir factura de venta"""
    venta = get_object_or_404(Venta, pk=pk)
    
    context = {
        'venta': venta,
        'titulo': f'Factura {venta.numero_factura}'
    }
    return render(request, 'ventas/factura.html', context)


# Devoluciones
# Funciones de devoluciones comentadas temporalmente

# @login_required
# def lista_devoluciones(request):
#     """Lista todas las devoluciones con filtros"""
#     # Código comentado temporalmente
#     pass
    
    # Estadísticas
    total_devoluciones = devoluciones.count()
    total_monto_devuelto = devoluciones.aggregate(total=Sum('total_devolucion'))['total'] or 0
    
    # Paginación
    paginator = Paginator(devoluciones, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Motivos disponibles para el filtro
    # Motivos temporalmente hardcodeados
    motivos_disponibles = [
        ('defectuoso', 'Producto Defectuoso'),
        ('cambio', 'Cambio de Producto'),
        ('error', 'Error en Venta'),
        ('cliente', 'Solicitud del Cliente'),
    ]
    
    context = {
        'page_obj': page_obj,
        'titulo': 'Gestión de Devoluciones',
        'subtitulo': 'Lista y gestión de todas las devoluciones de productos',
        'total_devoluciones': total_devoluciones,
        'total_monto_devuelto': total_monto_devuelto,
        'filtros': {
            'numero_devolucion': numero_devolucion,
            'numero_factura': numero_factura,
            'cliente': cliente_nombre,
            'motivo': motivo,
            'usuario': usuario_devolucion,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
        },
        'motivos_disponibles': motivos_disponibles,
    }
    return render(request, 'ventas/devoluciones.html', context)


@login_required
def buscar_venta_devolucion(request):
    """Buscar factura para crear devolución"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        numero_factura = request.GET.get('numero_factura', '').strip()
        
        if not numero_factura:
            return JsonResponse({'success': False, 'error': 'Debe ingresar un número de factura'})
        
        try:
            # Buscar la factura usando el nuevo modelo
            from .models import FacturaVenta, FacturaVentaDetalle
            
            factura = FacturaVenta.objects.get(
                numeroFactura__iexact=numero_factura,
                estado__in=['PAGADA', 'completada', 'COMPLETADA']  # Acepta diferentes estados
            )
            
            # Obtener detalles de la factura
            detalles_factura = FacturaVentaDetalle.objects.filter(idFacturaVenta=factura.idFactura)
            
            # Verificar que la factura no esté completamente devuelta
            detalles_con_disponible = []
            for detalle in detalles_factura:
                # Por ahora, mostrar todos los productos como disponibles
                # TODO: Implementar lógica de devoluciones cuando las tablas estén listas
                cantidad_devuelta = 0
                cantidad_disponible = detalle.cantidad
                
                if cantidad_disponible > 0:
                    detalles_con_disponible.append({
                        'id': detalle.id,
                        'producto_id': detalle.idProducto,
                        'producto_codigo': detalle.idProducto,  # Usar ID como código
                        'producto_nombre': detalle.productoNombre or f'Producto {detalle.idProducto}',
                        'cantidad_original': detalle.cantidad,
                        'cantidad_devuelta': cantidad_devuelta,
                        'cantidad_disponible': cantidad_disponible,
                        'precio_unitario': float(detalle.precioUnitario),
                        'subtotal_disponible': float(cantidad_disponible * detalle.precioUnitario),
                    })
            
            # Debug: ver qué datos estamos devolviendo
            print(f"DEBUG: Factura encontrada ID={factura.idFactura}")
            print(f"DEBUG: Número de detalles encontrados: {len(detalles_factura)}")
            print(f"DEBUG: Detalles con disponibles: {len(detalles_con_disponible)}")
            
            # Obtener información del cliente usando la relación
            cliente = factura.cliente
            cliente_nombre = cliente.nombre_completo if cliente else 'Cliente Genérico'
            cliente_documento = cliente.cedula_ruc if cliente else ''
            print(f"DEBUG: Cliente encontrado: {cliente_nombre}")
            
            if not detalles_con_disponible:
                return JsonResponse({
                    'success': False, 
                    'error': 'Esta factura ya tiene todos sus productos devueltos'
                })
            
            response_data = {
                'success': True,
                'venta': {
                    'id': factura.idFactura,
                    'numero_factura': factura.numeroFactura,
                    'fecha': factura.fechaEmision.strftime('%d/%m/%Y %H:%M'),
                    'cliente': {
                        'id': factura.idCliente,
                        'nombre': cliente_nombre,
                        'documento': cliente_documento,
                    },
                    'total_original': float(factura.total),
                    'detalles': detalles_con_disponible
                }
            }
            
            print(f"DEBUG: Response data = {response_data}")
            return JsonResponse(response_data)
            
        except FacturaVenta.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': f'No se encontró una factura completada con el número: {numero_factura}'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al buscar factura: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def crear_devolucion(request):
    """Crear nueva devolución - MODO DEMO (no guarda datos)"""
    
    if request.method == 'POST':
        # En modo demo, no guardamos nada, solo mostramos un mensaje
        messages.info(request, '🔍 MODO DEMO: Esta devolución no se guardó en la base de datos. Funcionalidad completa disponible cuando se configuren las tablas.')
        messages.success(request, 'Devolución procesada exitosamente en modo demostración.')
        return redirect('ventas:crear_devolucion')
    
    # GET request - mostrar formulario básico
    context = {
        'titulo': 'Crear Nueva Devolución',
        'subtitulo': 'Busque la factura y seleccione los productos a devolver (MODO DEMO)',
        'modo_demo': True,  # Indicador para el template
        'motivos_devolucion': [
            ('defectuoso', 'Producto Defectuoso'),
            ('cambio', 'Cambio de Producto'),
            ('error', 'Error en Venta'),
            ('cliente', 'Solicitud del Cliente'),
        ]
    }
    return render(request, 'ventas/crear_devolucion.html', context)


@login_required  
def lista_devoluciones(request):
    """Lista de devoluciones - MODO DEMO"""
    messages.info(request, '🔍 MODO DEMO: Esta sección mostrará el historial de devoluciones cuando se configuren las tablas.')
    
    # Datos de ejemplo para mostrar cómo se vería
    devoluciones_ejemplo = [
        {
            'numero_devolucion': 'DEV-20251028-0001',
            'fecha': '28/10/2025 23:30',
            'factura_original': '001-001-000000015',
            'cliente_nombre': 'Cliente Ejemplo',
            'motivo': 'Producto Defectuoso',
            'total_devolucion': 15.50,
            'usuario': request.user.username,
        }
    ]
    
    context = {
        'titulo': 'Lista de Devoluciones',
        'subtitulo': 'Historial de devoluciones realizadas (MODO DEMO)',
        'devoluciones_ejemplo': devoluciones_ejemplo,
        'modo_demo': True,
    }
    return render(request, 'ventas/devoluciones.html', context)


@login_required
def detalle_devolucion(request, pk):
    """Ver detalles completos de una devolución - MODO DEMO"""
    messages.info(request, '🔍 MODO DEMO: Esta pantalla mostrará los detalles de devoluciones cuando se configuren las tablas.')
    
    # Datos de ejemplo para mostrar cómo se vería
    devolucion_ejemplo = {
        'numero_devolucion': f'DEV-20251028-{pk:04d}',
        'fecha': '28/10/2025 23:30',
        'factura_original': '001-001-000000015',
        'cliente_nombre': 'Cliente Ejemplo',
        'motivo': 'Producto Defectuoso',
        'total_devolucion': 15.50,
        'usuario': request.user.username,
        'observaciones': 'Producto llegó dañado de fábrica',
        'productos': [
            {
                'nombre': 'AGUA ALL NATURAL S-GASX1LT',
                'cantidad_devuelta': 2,
                'precio_unitario': 5.45,
                'subtotal': 10.90,
            }
        ]
    }
    
    context = {
        'titulo': f'Devolución DEV-20251028-{pk:04d}',
        'subtitulo': 'Detalles de devolución (MODO DEMO)',
        'devolucion_ejemplo': devolucion_ejemplo,
        'modo_demo': True,
    }
    return render(request, 'ventas/detalle_devolucion.html', context)


@login_required
def detalle_devolucion(request, pk):
    """Ver detalles completos de una devolución - TEMPORALMENTE DESHABILITADO"""
    messages.warning(request, 'La funcionalidad de devoluciones está temporalmente deshabilitada mientras se configuran las tablas.')
    return redirect('ventas:lista_ventas')


# Reportes
@login_required
def reportes_ventas(request):
    """Reportes de ventas"""
    context = {
        'titulo': 'Reportes de Ventas'
    }
    return render(request, 'ventas/reportes.html', context)


@login_required
def ventas_por_fecha(request):
    """Reporte de ventas por fecha"""
    context = {
        'titulo': 'Ventas por Fecha'
    }
    return render(request, 'ventas/ventas_por_fecha.html', context)


@login_required
def ventas_por_vendedor(request):
    """Reporte de ventas por vendedor"""
    context = {
        'titulo': 'Ventas por Vendedor'
    }
    return render(request, 'ventas/ventas_por_vendedor.html', context)


@login_required
def ventas_por_producto(request):
    """Reporte de ventas por producto"""
    context = {
        'titulo': 'Ventas por Producto'
    }
    return render(request, 'ventas/ventas_por_producto.html', context)


# Funciones de búsqueda para Ventas siguiendo patrón C#
@login_required
def debug_ventas(request):
    """Función temporal para debug - verificar datos en la tabla"""
    with connection.cursor() as cursor:
        # Verificar estructura de la tabla ventas_venta
        cursor.execute("SHOW TABLES LIKE 'ventas_venta'")
        tabla_ventas_existe = cursor.fetchone()
        
        # Verificar estructura de la tabla facturas_venta
        cursor.execute("SHOW TABLES LIKE 'facturas_venta'")
        tabla_facturas_existe = cursor.fetchone()
        
        resultado = {
            'tabla_ventas_existe': tabla_ventas_existe is not None,
            'tabla_facturas_existe': tabla_facturas_existe is not None
        }
        
        if tabla_ventas_existe:
            # Contar registros ventas
            cursor.execute("SELECT COUNT(*) FROM ventas_venta")
            count_ventas = cursor.fetchone()[0]
            resultado['ventas_count'] = count_ventas
            
            if count_ventas > 0:
                # Obtener algunos ejemplos de ventas
                cursor.execute("SELECT numero_factura, fecha, total, estado FROM ventas_venta LIMIT 5")
                ejemplos_ventas = cursor.fetchall()
                resultado['ejemplos_ventas'] = [{'numero': e[0], 'fecha': str(e[1]), 'total': str(e[2]), 'estado': e[3]} for e in ejemplos_ventas]
        
        if tabla_facturas_existe:
            # Contar registros facturas
            cursor.execute("SELECT COUNT(*) FROM facturas_venta")
            count_facturas = cursor.fetchone()[0]
            resultado['facturas_count'] = count_facturas
            
            if count_facturas > 0:
                # Obtener algunos ejemplos de facturas
                cursor.execute("SELECT numeroFactura, fechaEmision, total, estado FROM facturas_venta LIMIT 5")
                ejemplos_facturas = cursor.fetchall()
                resultado['ejemplos_facturas'] = [{'numero': e[0], 'fecha': str(e[1]), 'total': str(e[2]), 'estado': e[3]} for e in ejemplos_facturas]
                
                # Buscar específicamente la factura que buscas
                cursor.execute("SELECT numeroFactura, fechaEmision, total FROM facturas_venta WHERE numeroFactura LIKE %s", ['%FAC-20251031-5A355D%'])
                factura_buscada = cursor.fetchone()
                if factura_buscada:
                    resultado['factura_encontrada'] = {'numero': factura_buscada[0], 'fecha': str(factura_buscada[1]), 'total': str(factura_buscada[2])}
        
        return JsonResponse(resultado)

@login_required
def buscar_ventas_por_numero(request):
    """Buscar ventas por número completo o dígitos parciales"""
    termino = request.GET.get('termino', '').strip()
    
    if not termino:
        return JsonResponse({'ventas': []})
    
    with connection.cursor() as cursor:
        # Buscar por número completo o por dígitos parciales
        sql = """
            SELECT 
                v.id AS Id,
                v.numero_factura AS NumeroVenta,
                COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS Cliente,
                v.total AS Total,
                v.estado AS Estado,
                v.fecha AS FechaVenta,
                v.tipo_pago AS MetodoPago
            FROM ventas_venta v
            LEFT JOIN clientes c ON v.cliente_id = c.id
            WHERE v.numero_factura LIKE %s 
               OR v.numero_factura = %s
               OR REPLACE(v.numero_factura, '-', '') LIKE %s
            ORDER BY v.fecha DESC
            LIMIT 20
        """
        
        # Buscar tanto el término completo como variaciones
        busqueda_completa = f'%{termino}%'
        busqueda_sin_guiones = f'%{termino.replace("-", "")}%'
        
        cursor.execute(sql, [busqueda_completa, termino, busqueda_sin_guiones])
        ventas = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        ventas_list = []
        for venta in ventas:
            ventas_list.append({
                'Id': venta[0],
                'NumeroVenta': venta[1],
                'Cliente': venta[2] or 'Sin cliente',
                'Total': float(venta[3]) if venta[3] else 0,
                'Estado': venta[4],
                'FechaVenta': venta[5].strftime('%Y-%m-%d %H:%M:%S') if venta[5] else '',
                'MetodoPago': venta[6]
            })
    
    return JsonResponse({'ventas': ventas_list})


@login_required
def obtener_venta_detalle(request, venta_id):
    """Obtener detalle completo de una venta específica"""
    try:
        # Buscar en la tabla facturas_venta usando el modelo FacturaVenta
        from .models import FacturaVenta, FacturaVentaDetalle
        
        try:
            factura = FacturaVenta.objects.get(idFactura=venta_id)
        except FacturaVenta.DoesNotExist:
            return JsonResponse({'error': 'Venta no encontrada'}, status=404)
        
        # Obtener cliente
        cliente = factura.cliente
        cliente_nombre = cliente.nombre_completo if cliente else 'Cliente Genérico'
        cliente_documento = cliente.cedula_ruc if cliente else ''
        cliente_direccion = cliente.direccion if cliente else ''
        cliente_telefono = cliente.telefono if cliente else ''
        
        # Obtener detalles de la factura
        detalles_factura = FacturaVentaDetalle.objects.filter(idFacturaVenta=factura.idFactura)
        
        # Formatear datos del encabezado
        encabezado_dict = {
            'Id': factura.idFactura,
            'NumeroVenta': factura.numeroFactura,
            'FechaVenta': factura.fechaEmision.strftime('%Y-%m-%d %H:%M:%S') if factura.fechaEmision else '',
            'TotalVenta': float(factura.total) if factura.total else 0,
            'SubtotalVenta': float(factura.subtotal) if factura.subtotal else 0,
            'DescuentoVenta': float(factura.descuento) if factura.descuento else 0,
            'IvaVenta': float(factura.iva) if factura.iva else 0,
            'EstadoVenta': factura.estado or 'Sin estado',
            'MetodoPago': 'ELECTRONICO',  # Valor por defecto ya que no está en el modelo
            'RazonSocial': cliente_nombre,
            'Identificacion': cliente_documento,
            'Direccion': cliente_direccion,
            'Telefono': cliente_telefono,
            'Vendedor': 'Sistema POS'
        }
        
        # Formatear datos del detalle
        detalle_list = []
        for detalle in detalles_factura:
            # Obtener producto
            producto = detalle.producto
            detalle_list.append({
                'Codigo': producto.codigo_principal if producto else str(detalle.idProducto),
                'Descripcion': detalle.productoNombre or (producto.nombre if producto else 'Producto desconocido'),
                'Cantidad': float(detalle.cantidad) if detalle.cantidad else 0,
                'PrecioUnitario': float(detalle.precioUnitario) if detalle.precioUnitario else 0,
                'Descuento': float(detalle.descuentoValor) if detalle.descuentoValor else 0,
                'Subtotal': float(detalle.total) if detalle.total else 0,
                'Iva': float(detalle.ivaValor) if detalle.ivaValor else 0
            })
        
        return JsonResponse({
            'encabezado': encabezado_dict,
            'detalle': detalle_list
        })
            
        
    except Exception as e:
        print(f"Error en obtener_venta_detalle: {e}")
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)


@login_required
def obtener_venta_por_numero(request):
    """Obtener venta específica por su número"""
    numero_venta = request.GET.get('numero', '').strip()
    
    if not numero_venta:
        return JsonResponse({'error': 'Número de venta requerido'}, status=400)
    
    with connection.cursor() as cursor:
        sql = """
            SELECT 
                v.id AS Id,
                v.numero_factura AS NumeroVenta,
                COALESCE(NULLIF(c.razonSocial,''), TRIM(CONCAT(IFNULL(c.nombres,''),' ',IFNULL(c.apellidos,'')))) AS Cliente,
                v.total AS Total,
                v.estado AS Estado,
                v.fecha AS FechaVenta,
                v.tipo_pago AS MetodoPago
            FROM ventas_venta v
            LEFT JOIN clientes c ON v.cliente_id = c.id
            WHERE v.numero_factura = %s
        """
        
        cursor.execute(sql, [numero_venta])
        venta = cursor.fetchone()
        
        if not venta:
            return JsonResponse({'error': 'Venta no encontrada'}, status=404)
        
        venta_dict = {
            'Id': venta[0],
            'NumeroVenta': venta[1],
            'Cliente': venta[2] or 'Sin cliente',
            'Total': float(venta[3]) if venta[3] else 0,
            'Estado': venta[4],
            'FechaVenta': venta[5].strftime('%Y-%m-%d %H:%M:%S') if venta[5] else '',
            'MetodoPago': venta[6]
        }
        
        return JsonResponse({'venta': venta_dict})


@login_required
def obtener_historial_precios(request):
    """Obtener historial de precios de un producto por su código"""
    codigo = request.GET.get('codigo', '').strip()
    
    if not codigo:
        return JsonResponse({'success': False, 'error': 'Código requerido'})
    
    try:
        from productos.models import Producto
        from django.db import connection
        
        # Buscar producto por código o código alternativo
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, precioVenta, costoUnidad, esDivisible, cantidadFraccion
                FROM productos 
                WHERE codigoPrincipal = %s AND anulado = 0
                LIMIT 1
            """, [codigo])
            
            producto = cursor.fetchone()
            
            if not producto:
                # Buscar en códigos alternativos
                cursor.execute("""
                    SELECT p.id, p.nombre, p.precioVenta, p.costoUnidad, p.esDivisible, p.cantidadFraccion
                    FROM productos p
                    INNER JOIN codigos_alternativo ca ON p.id = ca.producto_id
                    WHERE ca.codigo = %s AND p.anulado = 0 AND ca.activo = 1
                    LIMIT 1
                """, [codigo])
                
                producto = cursor.fetchone()
            
            if producto:
                return JsonResponse({
                    'success': True,
                    'tiene_producto': True,
                    'producto': {
                        'id': producto[0],
                        'nombre': producto[1],
                        'precio_venta_actual': float(producto[2]) if producto[2] else 0,
                        'costo_actual': float(producto[3]) if producto[3] else 0,
                        'es_divisible': bool(producto[4]),
                        'cantidad_fraccion': int(producto[5]) if producto[5] else 1
                    }
                })
            else:
                return JsonResponse({
                    'success': True,
                    'tiene_producto': False,
                    'producto': None
                })
                
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def desvincular_codigo_alternativo(request):
    """Desvincular un código alternativo de un producto"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        import json
        from django.db import connection
        
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip()
        
        if not codigo:
            return JsonResponse({'success': False, 'error': 'Código requerido'})
        
        with connection.cursor() as cursor:
            # Buscar el código alternativo
            cursor.execute("""
                SELECT id, producto_id FROM codigos_alternativo 
                WHERE codigo = %s AND activo = 1
            """, [codigo])
            
            codigo_alt = cursor.fetchone()
            
            if not codigo_alt:
                return JsonResponse({'success': False, 'error': 'Código alternativo no encontrado'})
            
            # Desactivar el código alternativo (no eliminar, mantener histórico)
            cursor.execute("""
                UPDATE codigos_alternativo 
                SET activo = 0
                WHERE id = %s
            """, [codigo_alt[0]])
            
            return JsonResponse({
                'success': True,
                'mensaje': f'Código {codigo} desvinculado exitosamente'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Error en formato de datos'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def reporte_consolidado(request):
    """Reporte consolidado de ventas por rango de fechas"""
    from datetime import datetime, timedelta
    
    # Obtener parámetros de fecha
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Si no hay fechas, usar el mes actual
    if not fecha_inicio or not fecha_fin:
        hoy = datetime.now()
        fecha_inicio = hoy.replace(day=1).strftime('%Y-%m-%d')
        fecha_fin = hoy.strftime('%Y-%m-%d')
    
    # Calcular días del período
    from datetime import datetime as dt
    fecha_inicio_dt = dt.strptime(fecha_inicio, '%Y-%m-%d')
    fecha_fin_dt = dt.strptime(fecha_fin, '%Y-%m-%d')
    dias_periodo = (fecha_fin_dt - fecha_inicio_dt).days + 1
    
    # Inicializar variables
    estadisticas = {
        'total_ventas': 0,
        'total_facturas': 0,
        'total_monto': 0,
        'total_clientes': 0,
        'total_productos_vendidos': 0,
        'promedio_venta': 0,
        'promedio_diario': 0,
        'dias_periodo': dias_periodo,
    }
    
    ventas_por_dia = []
    productos_top = []
    clientes_top = []
    formas_pago = []
    
    try:
        with connection.cursor() as cursor:
            # Total de ventas y monto
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_ventas,
                    COALESCE(SUM(total), 0) as total_monto,
                    COUNT(DISTINCT idCliente) as total_clientes
                FROM facturas_venta
                WHERE DATE(fechaEmision) BETWEEN %s AND %s
                AND estado != 'ANULADA'
            """, [fecha_inicio, fecha_fin])
            
            row = cursor.fetchone()
            if row:
                estadisticas['total_ventas'] = row[0] or 0
                estadisticas['total_monto'] = float(row[1]) if row[1] else 0
                estadisticas['total_clientes'] = row[2] or 0
                estadisticas['promedio_venta'] = (
                    estadisticas['total_monto'] / estadisticas['total_ventas'] 
                    if estadisticas['total_ventas'] > 0 else 0
                )
                estadisticas['promedio_diario'] = (
                    estadisticas['total_ventas'] / dias_periodo
                    if dias_periodo > 0 else 0
                )
            
            # Total de productos vendidos
            cursor.execute("""
                SELECT COALESCE(SUM(fvd.cantidad), 0) as total_productos
                FROM facturas_venta_detalle fvd
                JOIN facturas_venta fv ON fvd.idFacturaVenta = fv.id
                WHERE DATE(fv.fechaEmision) BETWEEN %s AND %s
                AND fv.estado != 'ANULADA'
            """, [fecha_inicio, fecha_fin])
            
            row = cursor.fetchone()
            if row:
                estadisticas['total_productos_vendidos'] = float(row[0]) if row[0] else 0
            
            # Ventas por día para gráfico
            cursor.execute("""
                SELECT 
                    DATE(fechaEmision) as fecha,
                    COUNT(*) as cantidad,
                    COALESCE(SUM(total), 0) as monto
                FROM facturas_venta
                WHERE DATE(fechaEmision) BETWEEN %s AND %s
                AND estado != 'ANULADA'
                GROUP BY DATE(fechaEmision)
                ORDER BY fecha
            """, [fecha_inicio, fecha_fin])
            
            for row in cursor.fetchall():
                ventas_por_dia.append({
                    'fecha': row[0].strftime('%Y-%m-%d'),
                    'cantidad': row[1],
                    'monto': float(row[2]) if row[2] else 0
                })
            
            # Top 10 productos más vendidos
            cursor.execute("""
                SELECT 
                    p.nombre,
                    p.codigoPrincipal,
                    SUM(fvd.cantidad) as cantidad,
                    COALESCE(SUM(fvd.total), 0) as total
                FROM facturas_venta_detalle fvd
                JOIN facturas_venta fv ON fvd.idFacturaVenta = fv.id
                JOIN productos p ON fvd.idProducto = p.id
                WHERE DATE(fv.fechaEmision) BETWEEN %s AND %s
                AND fv.estado != 'ANULADA'
                GROUP BY p.id, p.nombre, p.codigoPrincipal
                ORDER BY cantidad DESC
                LIMIT 10
            """, [fecha_inicio, fecha_fin])
            
            for row in cursor.fetchall():
                productos_top.append({
                    'nombre': row[0],
                    'codigo': row[1],
                    'cantidad': float(row[2]) if row[2] else 0,
                    'total': float(row[3]) if row[3] else 0
                })
            
            # Top 10 clientes
            cursor.execute("""
                SELECT 
                    CONCAT(c.nombres, ' ', c.apellidos) as cliente,
                    c.identificacion,
                    COUNT(*) as num_compras,
                    COALESCE(SUM(fv.total), 0) as total_comprado
                FROM facturas_venta fv
                LEFT JOIN clientes c ON fv.idCliente = c.id
                WHERE DATE(fv.fechaEmision) BETWEEN %s AND %s
                AND fv.estado != 'ANULADA'
                GROUP BY c.id, cliente, c.identificacion
                ORDER BY total_comprado DESC
                LIMIT 10
            """, [fecha_inicio, fecha_fin])
            
            for row in cursor.fetchall():
                clientes_top.append({
                    'nombre': row[0] or 'Cliente General',
                    'identificacion': row[1] or 'N/A',
                    'num_compras': row[2],
                    'total': float(row[3]) if row[3] else 0
                })
            
            # Formas de pago
            cursor.execute("""
                SELECT 
                    formaPago,
                    COUNT(*) as cantidad,
                    COALESCE(SUM(total), 0) as total
                FROM facturas_venta
                WHERE DATE(fechaEmision) BETWEEN %s AND %s
                AND estado != 'ANULADA'
                GROUP BY formaPago
                ORDER BY total DESC
            """, [fecha_inicio, fecha_fin])
            
            for row in cursor.fetchall():
                formas_pago.append({
                    'forma_pago': row[0] or 'No especificado',
                    'cantidad': row[1],
                    'total': float(row[2]) if row[2] else 0
                })
    
    except Exception as e:
        messages.error(request, f'Error al generar el reporte: {str(e)}')
    
    # Serializar datos para JavaScript
    import json
    
    context = {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estadisticas': estadisticas,
        'ventas_por_dia': ventas_por_dia,
        'ventas_por_dia_json': json.dumps(ventas_por_dia),
        'productos_top': productos_top,
        'productos_top_json': json.dumps(productos_top),
        'clientes_top': clientes_top,
        'formas_pago': formas_pago,
        'formas_pago_json': json.dumps(formas_pago),
    }
    
    return render(request, 'ventas/reporte_consolidado.html', context)
