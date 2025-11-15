from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from decimal import Decimal
import json

from .models import Cotizacion, DetalleCotizacion
from .forms import CotizacionForm, DetalleCotizacionFormSet, BuscarCotizacionForm, ConvertirVentaForm
from productos.models import Producto
from clientes.models import Cliente
from ventas.models import Venta, DetalleVenta, PagoVenta


@login_required
def lista_cotizaciones(request):
    """Vista para listar todas las cotizaciones con filtros"""
    form = BuscarCotizacionForm(request.GET)
    cotizaciones = Cotizacion.objects.all()
    
    # Aplicar filtros
    if form.is_valid():
        busqueda = form.cleaned_data.get('busqueda')
        estado = form.cleaned_data.get('estado')
        cliente = form.cleaned_data.get('cliente')
        fecha_desde = form.cleaned_data.get('fecha_desde')
        fecha_hasta = form.cleaned_data.get('fecha_hasta')
        
        if busqueda:
            cotizaciones = cotizaciones.filter(
                Q(numero__icontains=busqueda) |
                Q(cliente__nombre__icontains=busqueda) |
                Q(cliente__email__icontains=busqueda)
            )
        
        if estado:
            cotizaciones = cotizaciones.filter(estado=estado)
        
        if cliente:
            cotizaciones = cotizaciones.filter(cliente=cliente)
        
        if fecha_desde:
            cotizaciones = cotizaciones.filter(fecha_creacion__date__gte=fecha_desde)
        
        if fecha_hasta:
            cotizaciones = cotizaciones.filter(fecha_creacion__date__lte=fecha_hasta)
    
    # Actualizar estados vencidos automáticamente
    cotizaciones_vencidas = cotizaciones.filter(
        fecha_vencimiento__lt=timezone.now().date(),
        estado__in=['borrador', 'enviada']
    )
    cotizaciones_vencidas.update(estado='vencida')
    
    # Paginación
    paginator = Paginator(cotizaciones.order_by('-fecha_creacion'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    estadisticas = {
        'total': cotizaciones.count(),
        'borradores': cotizaciones.filter(estado='borrador').count(),
        'enviadas': cotizaciones.filter(estado='enviada').count(),
        'aceptadas': cotizaciones.filter(estado='aceptada').count(),
        'convertidas': cotizaciones.filter(estado='convertida').count(),
    }
    
    # Obtener clientes para el filtro
    clientes = Cliente.objects.filter(estado=True, anulado=False).order_by('nombres')
    
    context = {
        'form': form,
        'cotizaciones': page_obj,  # Cambiar el nombre para que coincida con la plantilla
        'stats': estadisticas,  # Cambiar el nombre para que coincida con la plantilla
        'clientes': clientes,
    }
    
    return render(request, 'cotizaciones/lista.html', context)


@login_required
def crear_cotizacion(request):
    """Vista para crear una nueva cotización"""
    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        formset = DetalleCotizacionFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            cotizacion = form.save(commit=False)
            cotizacion.usuario_creacion = request.user
            cotizacion.save()
            
            # Guardar detalles
            formset.instance = cotizacion
            formset.save()
            
            # Recalcular totales
            cotizacion.calcular_totales()
            cotizacion.save()
            
            messages.success(request, f'Cotización {cotizacion.numero} creada exitosamente.')
            return redirect('cotizaciones:detalle', pk=cotizacion.pk)
    else:
        form = CotizacionForm()
        formset = DetalleCotizacionFormSet()
    
    # Obtener productos activos para el autocompletado
    productos = Producto.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'form': form,
        'formset': formset,
        'productos': productos,
        'titulo': 'Nueva Cotización',
        'accion': 'Crear'
    }
    
    return render(request, 'cotizaciones/crear_editar.html', context)


@login_required
def detalle_cotizacion(request, pk):
    """Vista para ver el detalle de una cotización"""
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    detalles = cotizacion.detallecotizacion_set.all()
    
    context = {
        'cotizacion': cotizacion,
        'detalles': detalles,
    }
    
    return render(request, 'cotizaciones/detalle.html', context)


@login_required
def editar_cotizacion(request, pk):
    """Vista para editar una cotización existente"""
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    
    # Solo permitir edición si está en borrador
    if cotizacion.estado not in ['borrador']:
        messages.error(request, 'Solo se pueden editar cotizaciones en estado borrador.')
        return redirect('cotizaciones:detalle', pk=pk)
    
    if request.method == 'POST':
        form = CotizacionForm(request.POST, instance=cotizacion)
        formset = DetalleCotizacionFormSet(request.POST, instance=cotizacion)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
            # Recalcular totales
            cotizacion.calcular_totales()
            cotizacion.save()
            
            messages.success(request, f'Cotización {cotizacion.numero} actualizada exitosamente.')
            return redirect('cotizaciones:detalle', pk=cotizacion.pk)
    else:
        form = CotizacionForm(instance=cotizacion)
        formset = DetalleCotizacionFormSet(instance=cotizacion)
    
    # Obtener productos activos para el autocompletado
    productos = Producto.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'form': form,
        'formset': formset,
        'cotizacion': cotizacion,
        'productos': productos,
        'titulo': f'Editar Cotización {cotizacion.numero}',
        'accion': 'Actualizar'
    }
    
    return render(request, 'cotizaciones/crear_editar.html', context)


@login_required
@require_http_methods(["POST"])
def cambiar_estado(request, pk):
    """Vista AJAX para cambiar el estado de una cotización"""
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    nuevo_estado = request.POST.get('estado')
    
    if nuevo_estado in ['borrador', 'enviada', 'aceptada', 'rechazada']:
        cotizacion.estado = nuevo_estado
        cotizacion.save()
        
        return JsonResponse({
            'success': True,
            'mensaje': f'Estado cambiado a {cotizacion.get_estado_display()}'
        })
    
    return JsonResponse({
        'success': False,
        'error': 'Estado no válido'
    })


@login_required
def convertir_a_venta(request, pk):
    """Vista para convertir una cotización en venta"""
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    
    if not cotizacion.puede_convertir_a_venta():
        messages.error(request, 'Esta cotización no se puede convertir a venta.')
        return redirect('cotizaciones:detalle', pk=pk)
    
    if request.method == 'POST':
        form = ConvertirVentaForm(request.POST)
        
        if form.is_valid():
            try:
                # Crear la venta
                venta = Venta.objects.create(
                    cliente=cotizacion.cliente,
                    usuario=request.user,
                    subtotal=cotizacion.subtotal,
                    impuesto=cotizacion.impuesto,
                    total=cotizacion.total,
                    observaciones=form.cleaned_data.get('observaciones_venta', '')
                )
                
                # Crear detalles de venta
                for detalle_cot in cotizacion.detallecotizacion_set.all():
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=detalle_cot.producto,
                        cantidad=detalle_cot.cantidad,
                        precio_unitario=detalle_cot.precio_unitario,
                        total=detalle_cot.total
                    )
                
                # Crear pago por el total (se puede ajustar después)
                PagoVenta.objects.create(
                    venta=venta,
                    forma_pago='por_definir',
                    monto=venta.total
                )
                
                # Actualizar la cotización
                cotizacion.estado = 'convertida'
                cotizacion.venta_relacionada = venta
                cotizacion.save()
                
                messages.success(request, f'Cotización convertida exitosamente a venta #{venta.numero}')
                return redirect('ventas:detalle', pk=venta.pk)
                
            except Exception as e:
                messages.error(request, f'Error al convertir la cotización: {str(e)}')
    else:
        form = ConvertirVentaForm()
    
    context = {
        'cotizacion': cotizacion,
        'form': form,
    }
    
    return render(request, 'cotizaciones/convertir_venta.html', context)


@login_required
def obtener_precio_producto(request):
    """Vista AJAX para obtener el precio de un producto"""
    producto_id = request.GET.get('producto_id')
    
    if producto_id:
        try:
            producto = Producto.objects.get(id=producto_id, activo=True)
            return JsonResponse({
                'success': True,
                'precio': float(producto.precio_venta),
                'stock': producto.stock_actual,
                'descripcion': producto.descripcion or producto.nombre
            })
        except Producto.DoesNotExist:
            pass
    
    return JsonResponse({
        'success': False,
        'error': 'Producto no encontrado'
    })


@login_required
def duplicar_cotizacion(request, pk):
    """Vista para duplicar una cotización existente"""
    cotizacion_original = get_object_or_404(Cotizacion, pk=pk)
    
    # Crear nueva cotización basada en la original
    nueva_cotizacion = Cotizacion.objects.create(
        cliente=cotizacion_original.cliente,
        fecha_vencimiento=timezone.now().date() + timezone.timedelta(days=15),
        validez_dias=cotizacion_original.validez_dias,
        descuento=cotizacion_original.descuento,
        observaciones=cotizacion_original.observaciones,
        condiciones=cotizacion_original.condiciones,
        usuario_creacion=request.user
    )
    
    # Duplicar detalles
    for detalle in cotizacion_original.detallecotizacion_set.all():
        DetalleCotizacion.objects.create(
            cotizacion=nueva_cotizacion,
            producto=detalle.producto,
            cantidad=detalle.cantidad,
            precio_unitario=detalle.precio_unitario,
            descuento_linea=detalle.descuento_linea,
            descripcion_producto=detalle.descripcion_producto
        )
    
    # Recalcular totales
    nueva_cotizacion.calcular_totales()
    nueva_cotizacion.save()
    
    messages.success(request, f'Cotización duplicada como {nueva_cotizacion.numero}')
    return redirect('cotizaciones:editar', pk=nueva_cotizacion.pk)